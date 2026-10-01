"""Freeze subscriber-top-10 plus hash-random-20 entity samples by community."""
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

p=argparse.ArgumentParser(); p.add_argument('--minimum-size',type=int,default=30); p.add_argument('--top-union',type=int); a=p.parse_args()
root=Path('outputs/community_labels_2026-09-30'); root.mkdir(exist_ok=True)
source=Path('outputs/crawled_channel_graph_v3_2026-09-30/layout/nodes_layout.parquet')
d=pd.read_parquet(source).sort_values('node_id'); seed='telegram-community-labels-20260930-v1'
partition_hash=hashlib.sha256(d[['entity_id','community']].to_csv(index=False).encode()).hexdigest()
stats=d.groupby('community').agg(nodes=('node_id','size'),subscribers=('subscribers','sum')).reset_index()
rank_nodes={int(c):i+1 for i,c in enumerate(stats.sort_values(['nodes','community'],ascending=[False,True]).community)}
rank_subs={int(c):i+1 for i,c in enumerate(stats.sort_values(['subscribers','community'],ascending=[False,True]).community)}
selected_ids=set(stats.loc[stats.nodes>=a.minimum_size,'community']) if not a.top_union else {c for c in rank_nodes if rank_nodes[c]<=a.top_union or rank_subs[c]<=a.top_union}
samples=[]; inventory=[]
for c,g in d.groupby('community',sort=True):
    c=int(c); top=g.sort_values(['subscribers','entity_id'],ascending=[False,True]).head(10)
    rest=g[~g.node_id.isin(top.node_id)].copy()
    rest['random_key']=[hashlib.sha256(f'{seed}|{c}|{e}'.encode()).hexdigest() for e in rest.entity_id]
    rand=rest.sort_values(['random_key','entity_id']).head(20)
    inventory.append({'community':c,'display_id':c+1,'nodes':len(g),'subscribers':int(g.subscribers.sum()),'rank_nodes':rank_nodes[c],'rank_subscribers':rank_subs[c],'selected':c in selected_ids,'sample_n':min(len(g),30),'membership_sha256':hashlib.sha256('\n'.join(sorted(g.entity_id)).encode()).hexdigest()})
    for stratum,gg in [('top',top),('random',rand)]:
        for rank,(_,x) in enumerate(gg.iterrows(),1):
            samples.append({'community':c,'display_id':c+1,'node_id':int(x.node_id),'entity_id':x.entity_id,'handle':x.handle,'subscribers':int(x.subscribers),'subscriber_conflict':bool(x.subscriber_conflict),'stratum':stratum,'rank':rank,'selected':c in selected_ids,'random_key':x.get('random_key',None)})
pd.DataFrame(samples).to_csv(root/'samples.csv',index=False)
(root/'communities.json').write_text(json.dumps(inventory,indent=2)+'\n')
manifest={'protocol_version':1,'seed':seed,'algorithm':'Top 10 descending stored subscribers, entity_id tie-break; remaining 20 by ascending SHA256(seed|zero-based-community|entity_id), equivalent to reproducible uniform hash sampling without replacement. Census when fewer than 30. No substitutions for inaccessible evidence.','source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'partition_sha256':partition_hash,'minimum_size':a.minimum_size,'all_communities':len(inventory),'selected_communities':sum(x['selected'] for x in inventory),'selected_channels':sum(x['nodes'] for x in inventory if x['selected']),'selected_sample':sum(x['selected'] for x in samples),'sample_sha256':hashlib.sha256((root/'samples.csv').read_bytes()).hexdigest()}
(root/'sampling_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n'); print(json.dumps(manifest,indent=2))
manifest['selection_rule']=f'Union of top {a.top_union} by nodes and top {a.top_union} by summed subscribers; ascending community ID breaks ties' if a.top_union else f'At least {a.minimum_size} nodes'
manifest['top_union']=a.top_union
(root/'sampling_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
