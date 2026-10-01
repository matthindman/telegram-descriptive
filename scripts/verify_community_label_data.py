"""Independent coverage and immutability checks for descriptive community labels."""
from pathlib import Path
import hashlib, json
import pandas as pd

old=Path('outputs/crawled_channel_graph_v3_2026-09-30');new=Path('outputs/crawled_channel_graph_v4_2026-09-30');r=Path('outputs/community_labels_2026-09-30')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
identical=[]
for folder in ['graph','layout']:
    for source in (old/folder).iterdir():
        if not source.is_file():continue
        dest=new/folder/source.name;assert dest.exists() and sha(source)==sha(dest),f'Analytical/geometry change: {source}'
        identical.append(str(source.relative_to(old)))
n=pd.read_parquet(old/'layout/nodes_layout.parquet');s=pd.read_csv(r/'samples.csv');manifest=json.loads((r/'sampling_manifest.json').read_text())
assert sha(r/'samples.csv')==manifest['sample_sha256']
assert sha(old/'layout/nodes_layout.parquet')==manifest['source_sha256']
counts=n.groupby('community').node_id.count().sort_index();subs=n.groupby('community').subscribers.sum().sort_index()
expected=set(counts.sort_values(ascending=False,kind='stable').head(50).index)|set(subs.sort_values(ascending=False,kind='stable').head(50).index)
published=json.loads((new/'labels/community_labels.json').read_text());labels=published['communities'];assert published['status']=='complete for requested selection'
assert {x['community'] for x in labels}==expected and len(labels)==len(expected)==66
audience=[x['subscribers'] for x in labels];assert all(a>=b for a,b in zip(audience,audience[1:]))
for c in expected:
    members=n[n.community==c].sort_values(['subscribers','entity_id'],ascending=[False,True]);draw=s[s.community==c]
    assert draw.node_id.is_unique and set(draw.node_id)<=set(members.node_id)
    top=set(members.node_id.head(10));assert set(draw.loc[draw.stratum=='top','node_id'])==top
    eligible=members[~members.node_id.isin(top)].set_index('entity_id').node_id.to_dict()
    ordered=sorted(eligible,key=lambda entity:hashlib.sha256(f'{manifest["seed"]}|{c}|{entity}'.encode()).digest())
    assert set(draw.loc[draw.stratum=='random','node_id'])=={eligible[x] for x in ordered[:20]}
    assert len(draw)==min(30,len(members))
selected=s[s.community.isin(expected)];assert len(selected)==1847
evidence=[json.loads((r/'evidence'/f'{x.handle}.json').read_text()) for x in selected.itertuples()]
assert all(x['observed_at_utc'] and x['requested_url'].startswith('https://t.me/s/') for x in evidence)
for x in evidence:assert sha(Path(x['html_file']))==x['page_sha256']
annotations=[a for c in labels for a in c['channel_annotations']];assert {a['node_id'] for a in annotations}==set(selected.node_id) and len(annotations)==1847
summary={'communities':len(labels),'sampled_channels':len(selected),'represented_nodes':int(counts.loc[list(expected)].sum()),'represented_node_fraction':float(counts.loc[list(expected)].sum()/len(n)),'summed_subscribers':int(subs.loc[list(expected)].sum()),'subscriber_sum_fraction':float(subs.loc[list(expected)].sum()/subs.sum()),'counts_not_unique_people':True,'usable_channel_evidence':sum(x['usable'] for x in annotations),'usable_by_stratum':{k:sum(x['usable'] and x['stratum']==k for x in annotations) for k in ['top','random']},'sample_by_stratum':{k:sum(x['stratum']==k for x in annotations) for k in ['top','random']},'full_review_communities':sum(x.get('review_mode')!='staged_metadata_then_posts' for x in labels),'staged_review_communities':sum(x.get('review_mode')=='staged_metadata_then_posts' for x in labels),'staged_channel_depth':{k:sum(a.get('review_depth')==k for c in labels if c.get('review_mode')=='staged_metadata_then_posts' for a in c['channel_annotations']) for k in ['metadata','posts']},'confidence_counts':{k:sum(x['confidence']==k for x in labels) for k in ['high','moderate','low','unresolved']},'current_public_channel_previews':sum(x['public_channel_evidence'] for x in evidence),'fetch_statuses':pd.Series([x['evidence_status'] for x in evidence]).value_counts().to_dict(),'evidence_first_utc':min(x['observed_at_utc'] for x in evidence),'evidence_last_utc':max(x['observed_at_utc'] for x in evidence),'unchanged_files':identical,'source_checks':'Independent fixed hash sample of 12 channels in six communities plus targeted anomaly checks; not semantic accuracy estimation.'}
(r/'data_verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
