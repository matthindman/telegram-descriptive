"""Independent identity/edge/weight/core checks plus clean/cached/portable rebuilds."""
from pathlib import Path
import argparse,json,hashlib,shutil,subprocess,sys,tempfile
import numpy as np
import pandas as pd
from scipy import sparse
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root.resolve();repo=Path(__file__).resolve().parents[1];result={}
cohort=pd.read_parquet(root/'graph/crawled_nodes.parquet');globalnodes=pd.read_parquet(root.parent/'channel_graph_2026-09-30/graph/nodes_indexed.parquet')
identity={r.handle:('chat:'+str(int(r.chat_id)) if pd.notna(r.chat_id) else 'handle:'+r.handle) for r in globalnodes.itertuples()}
identity.update({r.handle:('chat:'+str(int(r.chat_id)) if pd.notna(r.chat_id) else 'handle:'+r.handle) for r in cohort.itertuples()})
cohort_ids={identity[h] for h in cohort.handle};nodes=pd.read_parquet(root/'graph/nodes.parquet');edges=pd.read_parquet(root/'graph/undirected_edges.parquet');directed=pd.read_parquet(root/'graph/directed_edges.parquet')
assert set(nodes.entity_id)==cohort_ids and nodes.entity_id.is_unique
ix=dict(zip(nodes.entity_id,nodes.node_id));validnodes=pd.read_parquet(root.parent/'channel_graph_filtered_2026-09-30/graph/nodes_indexed.parquet',columns=['handle']);allowed=set(validnodes.handle)|set(cohort.handle)
rawedges=pd.read_parquet(root.parent/'channel_graph_2026-09-30/graph/edges.parquet',columns=['source_handle','target_handle'])
dv={e:set() for e in cohort_ids};da={e:set() for e in cohort_ids};inside=set()
for sh,th in rawedges.itertuples(index=False,name=None):
    se=identity[sh]
    if sh not in allowed or se not in cohort_ids:continue
    te=identity[th]
    if se==te:continue
    da[se].add(te)
    if th not in allowed:continue
    dv[se].add(te)
    if te in cohort_ids:inside.add((ix[se],ix[te]))
assert inside==set(zip(directed.source,directed.target))
assert np.array_equal(nodes.global_valid_outdegree,[len(dv[e]) for e in nodes.entity_id])
assert np.array_equal(nodes.global_all_outdegree,[len(da[e]) for e in nodes.entity_id])
u={tuple(sorted(pair)) for pair in inside};assert u==set(zip(edges.source,edges.target))
for r in edges.itertuples():
    w=wa=0.
    for s,t in [(r.source,r.target),(r.target,r.source)]:
        if (s,t) in inside:
            entity=nodes.entity_id.iloc[s];w+=1/len(dv[entity]);wa+=1/len(da[entity])
    assert abs(w-r.weight)<1e-14 and abs(wa-r.weight_all_targets)<1e-14
result['independent_raw_export_reconstruction']={'entities':len(cohort_ids),'directed':len(inside),'undirected':len(u),'valid_and_all_target_weights_exact':True}
# Independently implemented Batagelj-Zaversnik bucket peeling, all nodes.
n=len(nodes);s=edges.source.to_numpy();t=edges.target.to_numpy();A=sparse.csr_matrix((np.ones(2*len(edges)),(np.r_[s,t],np.r_[t,s])),shape=(n,n));d=np.diff(A.indptr).copy();bins=np.bincount(d);starts=np.r_[0,np.cumsum(bins)[:-1]];vert=np.argsort(d,kind='stable');pos=np.empty(n,dtype=int);pos[vert]=np.arange(n)
for i in range(n):
    v=vert[i]
    for j in A.indices[A.indptr[v]:A.indptr[v+1]]:
        if d[j]>d[v]:
            dj=d[j];pj=pos[j];pw=starts[dj];w=vert[pw]
            if j!=w:pos[j],pos[w]=pw,pj;vert[pj],vert[pw]=w,j
            starts[dj]+=1;d[j]-=1
layout=pd.read_parquet(root/'layout/nodes_layout.parquet');assert np.array_equal(d,layout.core)
result['core_independent_peeling_all_nodes']=True
scratch=Path(tempfile.mkdtemp(prefix='telegram-revision-verify-',dir='/private/tmp'));result['scratch_directory']=str(scratch)
shutil.copytree(root/'graph',scratch/'graph');shutil.copy2(root/'graph_manifest.json',scratch/'graph_manifest.json');(scratch/'visualization').mkdir();shutil.copy2(root/'visualization/style.json',scratch/'visualization/style.json')
with (root/'revision/reproduction.log').open('w') as log:
    def run(script,*args):subprocess.run([sys.executable,str(repo/'scripts'/script),str(scratch),*args],check=True,stdout=log,stderr=log)
    run('layout_crawled_graph.py','--fresh')
    for file in ['positions.npy','quotient_positions.npy']:
        assert np.array_equal(np.load(scratch/'layout'/file),np.load(root/'layout'/file)),file
    result['fresh_positions_exact']=True
    fresh=np.load(scratch/'layout/positions.npy').copy();run('layout_crawled_graph.py');assert np.array_equal(fresh,np.load(scratch/'layout/positions.npy'))
    assert json.loads((scratch/'layout/layout_manifest.json').read_text())['cache_used'];result['cached_positions_exact']=True
    # A stale fingerprint must invalidate caches rather than silently reusing them.
    fp=scratch/'layout/cache_fingerprint.json';z=json.loads(fp.read_text());z['inputs']['graph/nodes.parquet']='stale-test';fp.write_text(json.dumps(z));run('layout_crawled_graph.py')
    assert not json.loads((scratch/'layout/layout_manifest.json').read_text())['cache_used'];assert np.array_equal(fresh,np.load(scratch/'layout/positions.npy'));result['stale_cache_invalidated']=True
    run('render_crawled_graph.py');result['copied_directory_render']=True
    def payload():
        import re,base64,gzip
        html=(scratch/'visualization/crawled_channels_atlas.html').read_text();x=re.search(r'type="application/octet-stream">([^<]+)</script>',html).group(1);return json.loads(gzip.decompress(base64.b64decode(x)))
    before=payload();style=scratch/'visualization/style.json';st=json.loads(style.read_text());st['edge_density_exponent']=2.;st['reference_diameter_css_px']=6.;style.write_text(json.dumps(st));run('render_crawled_graph.py');after=payload()
    assert before['nodes']==after['nodes'] and before['edges']==after['edges'];assert after['style']['edge_density_exponent']==2.
    result['style_only_data_unchanged']=True
    fp=json.loads((scratch/'layout/cache_fingerprint.json').read_text());fp['inputs']['graph/nodes.parquet']='stale-test';(scratch/'layout/cache_fingerprint.json').write_text(json.dumps(fp))
    bad=subprocess.run([sys.executable,str(repo/'scripts/render_crawled_graph.py'),str(scratch)],stdout=log,stderr=log);assert bad.returncode!=0;result['renderer_refuses_stale_layout']=True
(root/'revision/verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
