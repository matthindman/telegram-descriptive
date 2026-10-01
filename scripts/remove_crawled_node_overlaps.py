"""Circle adaptation of GTree (Nachmanson et al., 2016), with complete collision checks.

Keep the graph-derived source layout. Only the display coordinates change.
Growth uses a Delaunay proximity tree; node radii encode sqrt(subscribers).
"""
from pathlib import Path
import argparse, hashlib, json, time
import numpy as np
import pandas as pd
from scipy.spatial import Delaunay, cKDTree, procrustes
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import minimum_spanning_tree, breadth_first_order
from scipy.stats import spearmanr
from numba import njit


@njit(cache=True)
def grow(xy, order, parent, radii, cap):
    new=xy.copy()
    for z in range(1,len(order)):
        child=order[z]; par=parent[child]
        dx=xy[child,0]-xy[par,0];dy=xy[child,1]-xy[par,1]
        dist=np.sqrt(dx*dx+dy*dy)
        scale=min(cap,max(1.,(radii[child]+radii[par]+1e-5)/max(dist,1e-12)))
        new[child,0]=new[par,0]+dx*scale
        new[child,1]=new[par,1]+dy*scale
    return new


def triangulation_pairs(xy):
    tri=Delaunay(xy,qhull_options="QJ Qbb Qc Q12").simplices
    return np.unique(np.sort(np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[0,2]]]),axis=1),axis=0)


def collision_pairs(xy, radius, tolerance=1e-7):
    """Complete circle test via radius-binned spatial indexes; no all-pairs matrix."""
    bins=np.floor(np.log2(np.maximum(radius,1e-12))).astype(int)
    groups=[np.flatnonzero(bins==b) for b in np.unique(bins)]
    trees=[cKDTree(xy[ids]) for ids in groups];pairs=[]
    for i,aa in enumerate(groups):
        for j in range(i,len(groups)):
            bb=groups[j]; rmax=radius[bb].max()
            for start in range(0,len(aa),2048):
                ids=aa[start:start+2048]
                matches=trees[j].query_ball_point(xy[ids],radius[ids]+rmax)
                for a, neighbors in zip(ids,matches):
                    b=bb[neighbors]
                    if i==j:b=b[b>a]
                    if len(b):
                        dist=np.linalg.norm(xy[b]-xy[a],axis=1)
                        b=b[dist<radius[a]+radius[b]-tolerance]
                        if len(b):pairs.append(np.column_stack([np.full(len(b),a),b]))
    return np.concatenate(pairs).astype(np.int32) if pairs else np.empty((0,2),dtype=np.int32)


def remove(xy, radius, label, log):
    xy=xy.copy(); mean=xy.mean(axis=0); n=len(xy); start=time.monotonic()
    # Repeatable tiny shifts only for exact coincident centers.
    _, inv, counts=np.unique(xy,axis=0,return_inverse=True,return_counts=True)
    duplicate=np.flatnonzero(counts[inv]>1)
    if len(duplicate):xy[duplicate]+=np.random.default_rng(20260930).normal(0,1e-6,(len(duplicate),2))
    for iteration in range(160):
        pairs=triangulation_pairs(xy)
        dist=np.linalg.norm(xy[pairs[:,0]]-xy[pairs[:,1]],axis=1)
        cost=dist-radius[pairs[:,0]]-radius[pairs[:,1]]
        overlaps=int((cost < -1e-7).sum())
        complete=False
        if overlaps==0:
            extra=collision_pairs(xy,radius);complete=True;overlaps=len(extra)
            if overlaps:
                pairs=np.unique(np.sort(np.concatenate([pairs,extra]),axis=1),axis=0)
                dist=np.linalg.norm(xy[pairs[:,0]]-xy[pairs[:,1]],axis=1)
                cost=dist-radius[pairs[:,0]]-radius[pairs[:,1]]
        row={'region':label,'iteration':iteration,'overlaps_proximity_or_complete':overlaps,'complete_check':complete,'seconds':time.monotonic()-start}
        log.append(row)
        if iteration%5==0 or complete:print(json.dumps(row),flush=True)
        if not overlaps:return xy-xy.mean(axis=0)+mean
        # Add a common positive offset to costs: every spanning tree has n-1 edges,
        # so MST order is unchanged; zero weights cannot disappear in scipy sparse.
        adjusted=cost-cost.min()+1.
        graph=coo_matrix((adjusted,(pairs[:,0],pairs[:,1])),shape=(n,n)).tocsr()
        tree=minimum_spanning_tree(graph);order,parent=breadth_first_order(tree,0,directed=False,return_predecessors=True)
        assert len(order)==n
        xy=grow(xy,order,parent,radius,1.5)
        xy-=xy.mean(axis=0)-mean
    raise RuntimeError(f'Overlap removal did not converge for {label}; no incomplete layout published')


def fidelity(before,after,nodes,edges,giant):
    gmask=nodes.component.to_numpy()==giant;ids=np.flatnonzero(gmask);n=len(nodes)
    s=edges.source.to_numpy();t=edges.target.to_numpy();comm=nodes.community.to_numpy()
    m=gmask[s]&(comm[s]!=comm[t]);q=pd.DataFrame({'a':np.minimum(comm[s[m]],comm[t[m]]),'b':np.maximum(comm[s[m]],comm[t[m]]),'w':edges.weight.to_numpy()[m]}).groupby(['a','b']).w.sum().reset_index()
    def centers(xy):return pd.DataFrame({'c':comm[ids],'x':xy[ids,0],'y':xy[ids,1]}).groupby('c')[['x','y']].mean()
    c0=centers(before);c1=centers(after)
    d0=np.linalg.norm(c0.loc[q.a].to_numpy()-c0.loc[q.b].to_numpy(),axis=1);d1=np.linalg.norm(c1.loc[q.a].to_numpy()-c1.loc[q.b].to_numpy(),axis=1)
    rng=np.random.default_rng(20260930);sample=rng.choice(ids,min(4000,len(ids)),replace=False)
    nb0=cKDTree(before[ids]).query(before[sample],k=11)[1][:,1:];nb1=cKDTree(after[ids]).query(after[sample],k=11)[1][:,1:]
    retained=np.array([len(set(a)&set(b))/10 for a,b in zip(nb0,nb1)])
    return {'cross_community_weight_distance_before':float(spearmanr(q.w,d0).statistic),
            'cross_community_weight_distance_after':float(spearmanr(q.w,d1).statistic),
            'community_distance_rank_retention':float(spearmanr(d0,d1).statistic),
            'procrustes_disparity_giant':float(procrustes(before[ids],after[ids])[2]),
            'mean_10_nearest_neighbors_retained':float(retained.mean()),'nearest_neighbor_sample':len(sample)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);a=p.parse_args();root=a.root;out=root/'layout'
    nodes=pd.read_parquet(out/'nodes_layout.parquet');edges=pd.read_parquet(root/'graph/undirected_edges.parquet');lm=json.loads((out/'layout_manifest.json').read_text())
    original=out/'positions_graph_reference.npy'
    graph_hash=hashlib.sha256((root/'graph/nodes.parquet').read_bytes()).hexdigest()
    previous=out/'overlap_removal.json'
    if previous.exists():
        prev=json.loads(previous.read_text())
        assert prev.get('graph_nodes_sha256',graph_hash)==graph_hash, 'The saved reference belongs to another graph; use a new revision directory.'
    if not original.exists():np.save(original,nodes[['x','y']].to_numpy())
    before=np.load(original);xy=before.copy();subs=nodes.subscribers.to_numpy();radii=np.where(subs>0,4*np.sqrt(subs/100000),1.)
    # Reserve .25 units around every circle, including optional zero markers.
    inflated=radii+.25; giant=lm['giant_component'];comp=nodes.component.to_numpy();deg=nodes.degree.to_numpy();log=[]
    groups=[np.flatnonzero(comp==giant),np.flatnonzero((comp!=giant)&(deg>0)),np.flatnonzero(deg==0)]
    labels=['main component','small-component shelf','isolate shelf'];bounds=[]
    for ids,label in zip(groups,labels):
        xy[ids]=remove(before[ids],inflated[ids],label,log)
        lo=np.min(xy[ids]-inflated[ids,None],axis=0);hi=np.max(xy[ids]+inflated[ids,None],axis=0)
        bounds.append((lo,hi))
    # Keep disconnected components on clearly labelled separate shelves.
    lo,hi=bounds[0];xy[groups[0]]-=lo; mainwidth,mainheight=hi-lo
    shelfx=mainwidth+60
    for j,y in [(1,0.),(2,bounds[1][1][1]-bounds[1][0][1]+65)]:
        xy[groups[j]]+=np.array([shelfx,y])-bounds[j][0]
    assert np.isfinite(xy).all()
    remaining=collision_pairs(xy,inflated);assert len(remaining)==0
    # No subsequent downscaling: renderer sizes use the same world-unit radii.
    nodes['x']=xy[:,0];nodes['y']=xy[:,1];nodes.to_parquet(out/'nodes_layout.parquet',index=False);np.save(out/'positions.npy',xy)
    lm['giant_bounds']=[0.,0.,float(mainwidth),float(mainheight)]
    for j,key in [(1,'small_component_shelf'),(2,'isolate_shelf')]:
        ids=groups[j];lo=(xy[ids]-inflated[ids,None]).min(axis=0);hi=(xy[ids]+inflated[ids,None]).max(axis=0);lm[key]=[*lo.tolist(),*hi.tolist()]
    summary={'algorithm':'GTree circle adaptation, capped growth 1.5; Delaunay MST plus complete radius-binned collision checks',
             'padding_per_node_world':.25,'radius_reference_count':100000,'radius_reference':4.,'zero_radius':1.,
             'graph_nodes_sha256':graph_hash,'output_positions_sha256':hashlib.sha256((out/'positions.npy').read_bytes()).hexdigest(),'world_radius':'4*sqrt(subscribers/100000), zero marker radius 1',
             'remaining_overlaps_including_padding':len(remaining),'nodes':len(nodes),'fidelity':fidelity(before,xy,nodes,edges,giant),'iterations':log,
             'source_positions_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
             'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'render_guard':'Default node radii capped by one common world-space scale factor; preserves sqrt subscriber ratios. Ordinary filters preserve positions.'}
    lm['overlap_removal']= {k:v for k,v in summary.items() if k!='iterations'}
    if not lm['layout_algorithm'].endswith('; circle-aware GTree display postprocessing'):lm['layout_algorithm']+='; circle-aware GTree display postprocessing'
    lm['subscriber_size_used_for_layout']=True
    lm['subscriber_size_used_for_clustering']=False
    (out/'layout_manifest.json').write_text(json.dumps(lm,indent=2)+'\n');(out/'overlap_removal.json').write_text(json.dumps(summary,indent=2)+'\n')
    communities=nodes.groupby('community').agg(nodes=('handle','size'),subscribers=('subscribers','sum'),x=('x','mean'),y=('y','mean'),all_target_retention=('all_target_community_retention','first')).reset_index();communities.to_parquet(out/'communities.parquet',index=False)
    print(json.dumps({k:v for k,v in summary.items() if k!='iterations'},indent=2),flush=True)


if __name__=='__main__':main()
