"""Independent circle overlap, filter counts and GTree repeatability checks."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,tempfile,shutil
import numpy as np
import pandas as pd
from numba import njit

@njit(cache=True)
def sweep_count(xy,r):
    order=np.argsort(xy[:,0]-r);count=0;involved=np.zeros(len(r),np.uint8)
    for z in range(len(order)):
        i=order[z];right=xy[i,0]+r[i]
        for zz in range(z+1,len(order)):
            j=order[zz]
            if xy[j,0]-r[j]>=right:break
            dx=xy[i,0]-xy[j,0];dy=xy[i,1]-xy[j,1];want=r[i]+r[j]
            if dx*dx+dy*dy<(want-1e-7)**2:count+=1;involved[i]=1;involved[j]=1
    return count,int(involved.sum())

@njit(cache=True)
def sampled_overlap(xy,r,ids):
    affected=0;directed=0
    for i in ids:
        hit=False
        for j in range(len(r)):
            if i==j:continue
            dx=xy[i,0]-xy[j,0];dy=xy[i,1]-xy[j,1];want=r[i]+r[j]
            if dx*dx+dy*dy<want*want:directed+=1;hit=True
        affected+=int(hit)
    return affected,directed

p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();root=a.root.resolve()
n=pd.read_parquet(root/'layout/nodes_layout.parquet');xy=n[['x','y']].to_numpy();before=np.load(root/'layout/positions_graph_reference.npy');sub=n.subscribers.to_numpy();r=np.where(sub>0,4*np.sqrt(sub/100000),1.)
count,affected=sweep_count(xy,r+.25);assert count==0
# Verify actual embedded float32 coordinates, not just double-precision layout.
count32,affected32=sweep_count(xy.astype('float32').astype('float64'),r);assert count32==0
rng=np.random.default_rng(20260930);sample=rng.choice(len(n),4000,replace=False);sample_before=sampled_overlap(before,r,sample);sample_after=sampled_overlap(xy,r,sample)
e=pd.read_parquet(root/'graph/undirected_edges.parquet');s=e.source.to_numpy();t=e.target.to_numpy();thresholds=[]
for minimum in [0,1,100,1000,10000,100000,1000000,int(sub.max())]:
    for k in [0,10]:
        keep=(sub>=minimum)&(n.core.to_numpy()>=k)
        thresholds.append({'minimum_subscribers':minimum,'minimum_core':k,'nodes':int(keep.sum()),'edges':int((keep[s]&keep[t]).sum())})
# Hashes of graph and attributes show overlap removal cannot change topology/sizes.
old=root.parent/'crawled_channel_graph_v2_2026-09-30'
oldn=pd.read_parquet(old/'layout/nodes_layout.parquet')
assert n.drop(columns=['x','y']).equals(oldn.drop(columns=['x','y']))
for name in ['nodes.parquet','directed_edges.parquet','undirected_edges.parquet']:
    assert (root/'graph'/name).read_bytes()==(old/'graph'/name).read_bytes()
result={'circle_overlaps_with_padding':count,'circle_overlaps_float32_positions':count32,
        'sample_size':len(sample),'before_sample_nodes_overlapping':sample_before[0],'before_sample_incident_overlaps':sample_before[1],
        'after_sample_nodes_overlapping':sample_after[0],'graph_and_all_noncoordinate_attributes_unchanged':True,'threshold_counts':thresholds}
# Repeat the postprocessing from the saved reference, in a scratch copy.
scratch=Path(tempfile.mkdtemp(prefix='telegram-overlap-replay-',dir='/private/tmp'));shutil.copytree(root/'layout',scratch/'layout');shutil.copytree(root/'graph',scratch/'graph')
with (root/'revision/overlap_replay.log').open('w') as log:
    subprocess.run([sys.executable,str(Path(__file__).with_name('remove_crawled_node_overlaps.py')),str(scratch)],stdout=log,stderr=log,check=True)
assert np.array_equal(np.load(root/'layout/positions.npy'),np.load(scratch/'layout/positions.npy'))
result['repeat_positions_exact']=True;result['scratch']=str(scratch)
(root/'revision/overlap_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
