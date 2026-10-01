"""Validate complete sample reviews, apply explicit root decisions, publish sidecars."""
from pathlib import Path
import argparse, datetime, hashlib, html, json, re, shutil
import pandas as pd

p=argparse.ArgumentParser();p.add_argument('--partial',action='store_true',help='Development only; output is explicitly marked incomplete');a=p.parse_args()
root=Path('outputs/community_labels_2026-09-30');out=Path('outputs/crawled_channel_graph_v4_2026-09-30/labels');out.mkdir(exist_ok=True)
manifest=json.loads((root/'sampling_manifest.json').read_text());inventory=json.loads((root/'communities.json').read_text());chosen=sorted([x for x in inventory if x['selected']],key=lambda x:x['rank_subscribers'])
sample=pd.read_csv(root/'samples.csv');decisions=json.loads((root/'root_decisions.json').read_text())
reviewed=[];validation=[]
for item in chosen:
    display=item['display_id'];path=root/'reports'/f'community_{display:04d}.json'
    if a.partial and (not path.exists() or str(display) not in decisions):continue
    assert path.exists(),f'Missing report {display}'
    r=json.loads(path.read_text());assert r['display_id']==display
    assert r['model']=='gpt-6.1-sol' and r['reasoning_effort']=='low'
    expected=sample[sample.display_id==display].set_index('node_id');ann=r['channel_annotations']
    assert len(ann)==len(expected) and {x['node_id'] for x in ann}==set(expected.index),f'Sample mismatch {display}'
    for x in ann:
        row=expected.loc[x['node_id']]
        assert x['handle']==row.handle and x['stratum']==row.stratum
        assert isinstance(x['usable'],bool) and x['fit'] in ['yes','partial','no','unknown']
        assert Path(x['evidence_file']).resolve()==(root/'evidence'/f"{x['handle']}.json").resolve()
        ev=json.loads(Path(x['evidence_file']).read_text())
        assert ev['handle']==x['handle']
        assert re.fullmatch(r'https://t\.me/(?:s/)?[A-Za-z0-9_]+(?:/\d+)?(?:\?[^\s<>]*)?',x['source_url']),f'Unexpected source URL {display}: {x["source_url"]}'
    counts={k:{'sampled':sum(x['stratum']==k for x in ann),'usable':sum(x['stratum']==k and x['usable'] for x in ann)} for k in ['top','random']}
    assert counts==r['evidence_coverage'],f'Coverage mismatch {display}: {counts} != {r["evidence_coverage"]}'
    if r.get('review_mode')=='staged_metadata_then_posts':
        metadata=json.loads((root/'metadata_packets'/f'community_{display:04d}.json').read_text())
        required={x['node_id'] for x in metadata['channels'] if x['post_audit_required']}
        assert all(x.get('review_depth') in ['metadata','posts'] for x in ann),f'Missing depth {display}'
        assert all(x['review_depth']=='posts' for x in ann if x['node_id'] in required),f'Missing post audit {display}'
    decision=decisions[str(display)];assert decision['confidence'] in ['high','moderate','low','unresolved']
    assert all(decision.get(k) for k in ['label','description','rationale'])
    reviewed.append({**item,**r,**decision,'report_file':str(path),'report_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'model_proposal':r['proposed_label']})
    validation.append({'display_id':display,'sample_n':len(expected),'coverage':counts,'report_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
assert a.partial or len(reviewed)==len(chosen)
result={'version':1,'status':'INCOMPLETE DEVELOPMENT PREVIEW' if a.partial else 'complete for requested selection','date':'2026-09-30','partition_sha256':manifest['partition_sha256'],'selection_rule':manifest['selection_rule'],'fit_reference':'Per-channel fit refers to the reviewer proposed_label, not an adjudicated classification under the final root label.','sample_seed':manifest['seed'],'sample_sha256':manifest['sample_sha256'],'review_model':'gpt-6.1-sol','review_reasoning_effort':'low','synthesis':'Root assistant reviewed reports and chose labels; model-assisted, not human-validated. Qualitative confidence is not a calibrated probability.','evidence_period':'Current public previews fetched during this review, not the historical crawl window.','communities':reviewed}
(out/'community_labels.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
flat=[{k:x[k] for k in ['display_id','nodes','subscribers','rank_nodes','rank_subscribers','label','confidence','description','rationale','model_proposal']}|{'top_usable':x['evidence_coverage']['top']['usable'],'top_sample':x['evidence_coverage']['top']['sampled'],'random_usable':x['evidence_coverage']['random']['usable'],'random_sample':x['evidence_coverage']['random']['sampled']} for x in reviewed]
pd.DataFrame(flat).to_csv(out/'community_labels.csv',index=False)
(root/'validation.json').write_text(json.dumps({'complete':not a.partial,'communities':len(reviewed),'channels':sum(x['sample_n'] for x in reviewed),'checks':validation},indent=2)+'\n')
for name in ['protocol.txt','sampling_manifest.json','root_decisions.json']:shutil.copy2(root/name,out/name)
esc=html.escape
blocks=[]
for x in reviewed:
    count=x['evidence_coverage'];rows=''.join(f'<tr><td>{esc(y["stratum"])}</td><td><a href="{esc(y["source_url"])}" target="_blank" rel="noreferrer">@{esc(y["handle"])}</a></td><td>{esc(y["language"])}</td><td>{esc(y["subject_function"])}</td><td>{esc(y["evidence_summary"])}</td><td>{esc(y["fit"])}</td></tr>' for y in x['channel_annotations'])
    blocks.append(f'<article id="c{x["display_id"]}" data-search="{esc((str(x["display_id"])+" "+x["label"]+" "+x["description"]).lower())}"><details><summary><b>C{x["display_id"]} · {esc(x["label"])}</b><span>{x["nodes"]:,} channels · {x["subscribers"]:,} summed subscribers · {esc(x["confidence"])} confidence</span></summary><p>{esc(x["description"])}</p><p>Ranks: #{x["rank_nodes"]} by channels; #{x["rank_subscribers"]} by subscribers. Usable evidence: largest {count["top"]["usable"]}/{count["top"]["sampled"]}; random {count["random"]["usable"]}/{count["random"]["sampled"]}.</p><p><b>Largest:</b> {esc(x["top_summary"])}</p><p><b>Random others:</b> {esc(x["random_summary"])}</p><p><b>Exceptions:</b> {esc("; ".join(x["counterexamples"]))}</p><p><b>Qualifications:</b> {esc(" ".join(x["limitations"]))}</p><p><b>Reviewer proposal:</b> {esc(x["model_proposal"])}</p><p><b>Root synthesis:</b> {esc(x["rationale"])}</p><div class="table"><table><thead><tr><th>Sample</th><th>Channel / source</th><th>Language</th><th>Subject or function</th><th>Evidence</th><th>Fit to reviewer proposal</th></tr></thead><tbody>{rows}</tbody></table></div></details></article>')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Telegram community evidence reports</title><style>body{font:15px/1.55 system-ui;background:#0a121d;color:#e6edf4;max-width:1150px;margin:auto;padding:28px}a{color:#7cddcd}h1{font-size:28px}p{max-width:95ch}.note{color:#abbdd0}input{font:inherit;padding:10px;background:#111d2b;color:inherit;border:1px solid #48617b;width:min(90%,600px)}article{background:#111d2b;border:1px solid #26384a;margin:12px 0;padding:14px}summary{cursor:pointer}summary span{display:block;color:#abbdd0;font-size:13px}.table{overflow-x:auto}table{border-collapse:collapse;font-size:12px;width:100%}td,th{border:1px solid #26384a;padding:8px;text-align:left;vertical-align:top}th{color:#7cddcd}button{font:inherit;padding:7px}</style><h1>Community labels and evidence</h1>'''
page+=f'<p>{len(reviewed)} reviewed communities · {sum(x["sample_n"] for x in reviewed):,} sampled channels. {esc(result["selection_rule"])}.</p><p class="note">Provisional model-assisted descriptions of structural groups. Each review uses ten largest channels and twenty random others, or a census for groups smaller than thirty. Current public text can differ from historical identities and crawl-period posts. Confidence is qualitative; this is not human validation. Subscriber sums are not unique audiences.</p><p><a href="crawled_channels_atlas.html">Open network atlas</a> · <a href="community_labels.csv">Download label table</a> · <a href="labeling_protocol.txt">Read protocol and research sources</a></p><input id="search" type="search" aria-label="Search community labels" placeholder="Search by community ID, language or topic">'+''.join(blocks)+'''<script>document.getElementById('search').oninput=e=>{const q=e.target.value.toLowerCase();document.querySelectorAll('article').forEach(x=>x.hidden=!x.dataset.search.includes(q))};const c=location.hash&&document.querySelector(location.hash);if(c)c.querySelector('details').open=true;</script></html>'''
vis=out.parent/'visualization';(vis/'community_reports.html').write_text(page);shutil.copy2(out/'community_labels.csv',vis/'community_labels.csv');shutil.copy2(root/'protocol.txt',vis/'labeling_protocol.txt')
print(json.dumps({'communities':len(reviewed),'channels':sum(x['sample_n'] for x in reviewed),'status':result['status']}))
