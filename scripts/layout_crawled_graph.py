"""Reproducible weighted hierarchical layout with measured spatial fidelity."""
from pathlib import Path
import argparse, hashlib, json, random, time
import igraph as ig
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.spatial import cKDTree, procrustes
from scipy.stats import spearmanr
from sklearn.metrics import normalized_mutual_info_score

SEED = 20260930


def fingerprint(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [root/'graph/nodes.parquet', root/'graph/undirected_edges.parquet']}


def rng_seed(key):
    return int.from_bytes(hashlib.sha256(f'{SEED}:{key}'.encode()).digest()[:4], 'big')


def force(g, key, iterations=200):
    """Each stochastic call has its own stream, independent of cache hits/order."""
    n = g.vcount()
    if n == 1: return np.zeros((1, 2))
    if n == 2: return np.array([[-1., 0.], [1., 0.]])
    seed = rng_seed(key); rng = np.random.default_rng(seed)
    initial = rng.normal(size=(n, 2)) * np.sqrt(n)
    w = np.asarray(g.es['weight']); w = w / np.median(w)
    ig.set_random_number_generator(random.Random(seed))
    xy = np.asarray(g.layout_fruchterman_reingold(weights=w, seed=initial, niter=iterations,
                                                 grid='grid' if n > 1000 else 'nogrid'))
    return xy - xy.mean(axis=0)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path)
    p.add_argument('--fresh', action='store_true', help='Recompute validated caches too')
    a=p.parse_args(); out=a.root/'layout'; out.mkdir(exist_ok=True); start=time.monotonic()
    nodes=pd.read_parquet(a.root/'graph/nodes.parquet'); edges=pd.read_parquet(a.root/'graph/undirected_edges.parquet')
    fp={'inputs':fingerprint(a.root),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'igraph':ig.__version__, 'seed':SEED}
    cache=out/'cache_fingerprint.json'
    cache_ok=not a.fresh and cache.exists() and json.loads(cache.read_text()) == fp
    n=len(nodes); pairs=edges[['source','target']].to_numpy(); weights=edges.weight.to_numpy()
    g=ig.Graph(n=n,edges=pairs,directed=False); g.es['weight']=weights.tolist()
    core=np.asarray(g.coreness(),dtype=np.int32); nodes['core']=core
    memberships=[]; sensitivity=[]; noniso=nodes.degree.to_numpy()>0
    giant=int(nodes.loc[nodes.component_size.idxmax(),'component']); gids=np.flatnonzero(nodes.component.to_numpy()==giant)
    configs=[('primary',1.,SEED,'weight'),('seed2',1.,SEED+1,'weight'),('seed3',1.,SEED+2,'weight'),
             ('coarse',.5,SEED,'weight'),('fine',2.,SEED,'weight'),('all_targets',1.,SEED,'weight_all_targets')]
    if cache_ok and (out/'partitions.npz').exists():
        z=np.load(out/'partitions.npz'); memberships=[z[key] for key,_,_,_ in configs]
        sensitivity=json.loads((out/'partition_sensitivity.json').read_text())
    else:
        for key,res,seed,wcol in configs:
            ig.set_random_number_generator(random.Random(seed))
            part=g.community_leiden(objective_function='modularity',weights=edges[wcol].to_numpy(),resolution=res,n_iterations=4)
            ids=np.array(part.membership,dtype=np.int32); cs=np.bincount(ids)
            order=np.lexsort((np.arange(len(cs)),-cs)); rank=np.empty_like(order);rank[order]=np.arange(len(cs));ids=rank[ids].astype('int32')
            memberships.append(ids); giant_sizes=np.unique(ids[gids],return_counts=True)[1]
            row={'variant':key,'resolution':res,'seed':seed,'weight_column':wcol,'communities':len(cs),
                 'nonisolated_communities':int(len(np.unique(ids[noniso]))),'giant_communities':len(giant_sizes),
                 'giant_largest_sizes':sorted(giant_sizes.tolist(),reverse=True)[:20],
                 'giant_communities_le3':int((giant_sizes<=3).sum()),
                 'weighted_modularity':g.modularity(ids,weights=edges[wcol].to_numpy(),resolution=res),
                 'nmi_to_primary_nonisolates':float(normalized_mutual_info_score(memberships[0][noniso],ids[noniso]))}
            sensitivity.append(row);print(json.dumps({'stage':'partition',**row}),flush=True)
        np.savez_compressed(out/'partitions.npz',**dict(zip([c[0] for c in configs],memberships)))
        (out/'partition_sensitivity.json').write_text(json.dumps(sensitivity,indent=2)+'\n')
    mainpart=memberships[0]; nodes['community']=mainpart;nodes['community_coarse']=memberships[3];nodes['community_fine']=memberships[4];nodes['community_all_targets']=memberships[5]
    # Compare memberships label-invariantly via the best overlap of each primary group.
    cross=pd.crosstab(mainpart[noniso],memberships[5][noniso]); stability=cross.max(axis=1)/cross.sum(axis=1)
    nodes['all_target_community_retention']=nodes.community.map(stability).fillna(1.)
    cross.stack().loc[lambda x:x>0].rename('nodes').reset_index().to_parquet(out/'denominator_community_overlap.parquet',index=False)
    coords=np.full((n,2),np.nan); unique,inverse=np.unique(mainpart[gids],return_inverse=True); k=len(unique)
    sg=g.induced_subgraph(gids); gi=np.asarray(sg.get_edgelist()); sw=np.asarray(sg.es['weight'])
    cu=inverse[gi[:,0]];cv=inverse[gi[:,1]];m=cu!=cv
    qa=sparse.coo_matrix((sw[m],(np.minimum(cu[m],cv[m]),np.maximum(cu[m],cv[m]))),shape=(k,k)).tocsr();qe=qa.tocoo()
    qg=ig.Graph(n=k,edges=np.column_stack([qe.row,qe.col]),directed=False);qg.es['weight']=np.log1p(qe.data/np.median(qe.data)).tolist()
    qpath=out/'quotient_positions.npy'
    qxy=np.load(qpath) if cache_ok and qpath.exists() else force(qg,'quotient',350)
    np.save(qpath,qxy)
    qxy=qxy-qxy.mean(axis=0);qxy=qxy/max(np.ptp(qxy,axis=0).max(),1e-9)*1000
    # Keep every quotient center exactly fixed: NO repacking/separation pass.
    # Available-space scaling of local layouts is presentational, explicitly saved.
    nearest=cKDTree(qxy).query(qxy,k=2)[0][:,1]
    local_rows=[]
    for j,cid in enumerate(unique):
        orig=gids[np.flatnonzero(inverse==j)];sub=g.induced_subgraph(orig);sz=len(orig)
        local=force(sub,f'community:{cid}',250 if sz>1000 else 200)
        rms=max(np.sqrt(np.mean(np.sum(local*local,axis=1))),1e-9)
        radius=min(24.,max(.15,nearest[j]*.3)); local=local/rms*radius
        coords[orig]=qxy[j]+local
        if sz>=100:
            el=np.asarray(sub.get_edgelist()); lw=np.asarray(sub.es['weight'])
            rng=np.random.default_rng(rng_seed(f'diagnostic:{cid}')); rp=rng.integers(0,sz,size=(10000,2))
            lens=np.linalg.norm(local[el[:,0]]-local[el[:,1]],axis=1);randomlens=np.linalg.norm(local[rp[:,0]]-local[rp[:,1]],axis=1)
            theta=np.arange(sz)*2.399963229728653; r=np.sqrt(np.arange(sz)+1);alphabetic=np.column_stack([r*np.cos(theta),r*np.sin(theta)])
            local_rows.append({'community':int(cid),'nodes':sz,'weight_median':float(np.median(lw)),
                               'edge_length_over_random':float(np.median(lens)/np.median(randomlens)),
                               'disparity_vs_alphabetical_spiral':float(procrustes(alphabetic,local)[2]),'local_rms':radius})
        if j%250==0:print(json.dumps({'stage':'local_layout','completed':j+1,'total':k,'seconds':time.monotonic()-start}),flush=True)
    # Only a common translation, rotation and scale; community centroids cannot drift.
    xy=coords[gids].copy()
    if np.ptp(xy[:,1])>np.ptp(xy[:,0]):xy=xy[:,[1,0]]
    xy-=xy.min(axis=0);xy*=1000/max(np.ptp(xy,axis=0).max(),1e-9);coords[gids]=xy
    centers=np.array([coords[gids[inverse==j]].mean(axis=0) for j in range(k)])
    rawdist=np.linalg.norm(qxy[qe.row]-qxy[qe.col],axis=1);finaldist=np.linalg.norm(centers[qe.row]-centers[qe.col],axis=1)
    fidelity={'quotient_pairs':len(qe.data),'raw_weight_distance_spearman':float(spearmanr(qe.data,rawdist).statistic),
              'final_weight_distance_spearman':float(spearmanr(qe.data,finaldist).statistic),
              'raw_vs_final_distance_spearman':float(spearmanr(rawdist,finaldist).statistic),
              'quotient_attraction':'log1p(quotient weight / median quotient weight); strictly monotone display transform', 'no_separation_pass':True,'local_layouts':local_rows}
    (out/'layout_fidelity.json').write_text(json.dumps(fidelity,indent=2)+'\n')
    x=y=rowh=0.; width=290.;comp=nodes.component.to_numpy()
    small=nodes.loc[(nodes.component!=giant)&(nodes.degree>0)].groupby('component').size().sort_values(ascending=False)
    for cid,sz in small.items():
        ids=np.flatnonzero(comp==cid);local=force(g.induced_subgraph(ids),f'component:{cid}',100)
        local-=local.min(axis=0);local/=max(np.ptp(local,axis=0).max(),1e-9);cell=max(7.,np.sqrt(sz)*4)
        if x+cell>width:x=0.;y+=rowh+5;rowh=0.
        coords[ids]=local*(cell-2)+[1080+x,20+y];x+=cell+5;rowh=max(rowh,cell)
    smallheight=y+rowh+20;iso=np.flatnonzero(nodes.degree.to_numpy()==0);cols=85;step=290/cols
    coords[iso]=np.column_stack([np.arange(len(iso))%cols*step+1080,np.arange(len(iso))//cols*step+smallheight+70])
    assert np.isfinite(coords).all()
    # Exact coreness independently checked by iterative threshold pruning (maximality).
    adjacency=sparse.csr_matrix((np.ones(len(pairs)*2,dtype=np.int32),(np.r_[pairs[:,0],pairs[:,1]],np.r_[pairs[:,1],pairs[:,0]])),shape=(n,n))
    checks=[]
    for threshold in sorted(set([1,2,5,10,int(core.max())])):
        keep=np.ones(n,dtype=bool)
        while True:
            nxt=keep & (np.asarray(adjacency @ keep.astype(np.int32)).ravel()>=threshold)
            if np.array_equal(nxt,keep):break
            keep=nxt
        assert np.array_equal(keep,core>=threshold)
        checks.append({'k':threshold,'nodes':int(keep.sum()),'edges':int((keep[pairs[:,0]]&keep[pairs[:,1]]).sum()),'maximal_by_independent_pruning':True})
    block=core==core.max();internal=block[pairs[:,0]]&block[pairs[:,1]];remove=block[pairs[:,0]]|block[pairs[:,1]]
    without=g.induced_subgraph(np.flatnonzero(~block));wc=np.array(without.coreness()); wp=np.array(without.get_edgelist())
    block_summary={'criterion':'maximum unweighted core','k':int(core.max()),'nodes':int(block.sum()),'internal_edges':int(internal.sum()),
                   'edge_share':float(internal.mean()),'density':float(internal.sum()/(block.sum()*(block.sum()-1)/2)),
                   'median_subscribers':float(nodes.loc[block,'subscribers'].median()),'weight_share':float(weights[internal].sum()/weights.sum()),
                   'excluding_block_nodes':int((~block).sum()),'excluding_block_edges':int((~remove).sum()),
                   'recomputed_10core_without_block_nodes':int((wc>=10).sum()),'recomputed_10core_without_block_edges':int(((wc[wp[:,0]]>=10)&(wc[wp[:,1]]>=10)).sum()),
                   'nature':'unestablished; structural density is not proof of coordination or authenticity'}
    nodes['dense_block']=block;nodes['x']=coords[:,0];nodes['y']=coords[:,1]
    nodes.to_parquet(out/'nodes_layout.parquet',index=False);np.save(out/'positions.npy',coords)
    communities=nodes.groupby('community').agg(nodes=('handle','size'),subscribers=('subscribers','sum'),x=('x','mean'),y=('y','mean'),
                                             all_target_retention=('all_target_community_retention','first')).reset_index()
    communities.to_parquet(out/'communities.parquet',index=False)
    summary={'seed':SEED,'nodes':n,'edges':len(edges),'layout_algorithm':'Log-compressed weighted quotient centers unchanged; independently seeded median-normalized local weighted FR, scaled to local center spacing. No node-level global refinement.',
             'local_geometry_note':'Community-local magnification is presentational; compare centers, not blob size/gaps. Local RMS=min(24,max(.15,.3*nearest center distance)).',
             'global_node_force_refinement':False,'giant_component':giant,'giant_nodes':len(gids),'max_core':int(core.max()),
             'core_values':np.unique(core).tolist(),'community_count':len(communities),'nonisolated_communities':sensitivity[0]['nonisolated_communities'],
             'small_component_shelf':[1080,20,1370,smallheight], 'isolate_shelf':[1080,smallheight+70,1370,float(coords[iso,1].max())] if len(iso) else None,
             'giant_bounds':[0.,0.,float(xy[:,0].max()),float(xy[:,1].max())],'coreness_checks':checks,'dense_block':block_summary,
             'denominator_sensitivity':sensitivity[-1], 'finite_coordinates':bool(np.isfinite(coords).all()),'subscriber_size_used_for_layout':False,
             'igraph_version':ig.__version__,'cache_used':cache_ok,'elapsed_seconds':time.monotonic()-start}
    (out/'layout_manifest.json').write_text(json.dumps(summary,indent=2)+'\n');cache.write_text(json.dumps(fp,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
