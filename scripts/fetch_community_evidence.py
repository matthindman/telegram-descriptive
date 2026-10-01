"""Cache public Telegram text evidence; preserve failures, IDs, timestamps and HTML."""
import argparse, concurrent.futures, datetime, hashlib, json, re, subprocess, time
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup

ROOT=Path('outputs/community_labels_2026-09-30')
def fetch(row):
    handle=row['handle']; assert re.fullmatch(r'[a-zA-Z0-9_]+',handle)
    dest=ROOT/'evidence'/f'{handle}.json'
    if dest.exists(): return json.loads(dest.read_text())
    url='https://t.me/s/'+handle; html=ROOT/'pages'/f'{handle}.html'
    stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    r=subprocess.run(['/usr/bin/curl','--location','--proto','=https','--proto-redir','=https','--connect-timeout','10','--max-time','25','--silent','--show-error','--output',str(html),'--write-out','%{http_code}\n%{url_effective}',url],capture_output=True,text=True)
    status=r.stdout.splitlines(); soup=BeautifulSoup(html.read_text(errors='replace') if html.exists() else '', 'html.parser')
    def text(sel):
        e=soup.select_one(sel); return e.get_text(' ',strip=True) if e else ''
    title=text('.tgme_channel_info_header_title') or text('.tgme_page_title')
    description=text('.tgme_channel_info_description') or text('.tgme_page_description')
    extra=text('.tgme_channel_info_counter') or text('.tgme_page_extra')
    msgs=[]
    for m in soup.select('.tgme_widget_message'):
        body=m.select_one('.tgme_widget_message_text'); date=m.select_one('time'); link=m.select_one('.tgme_widget_message_date')
        body=body.get_text(' ',strip=True) if body else ''
        if body: msgs.append({'text':body,'datetime':date.get('datetime') if date else None,'url':link.get('href') if link else None})
    ok=r.returncode==0 and status and status[0]=='200'
    channel=bool(soup.select_one('.tgme_channel_info') or re.search(r'\bsubscribers?\b',extra,re.I))
    result={'handle':handle,'requested_url':url,'effective_url':status[1] if len(status)>1 else None,'http_status':status[0] if status else None,'curl_exit':r.returncode,'error':r.stderr.strip(),'observed_at_utc':stamp,'title':title,'description':description,'public_count_text':extra,'public_channel_evidence':bool(ok and channel),'evidence_status':'public_channel' if ok and channel else 'public_landing' if ok and title else 'unavailable_or_generic','preview_text_posts':len(msgs),'recent_posts':msgs[-5:],'page_sha256':hashlib.sha256(html.read_bytes()).hexdigest() if html.exists() else None,'html_file':str(html),'identity_warning':'Current handle preview is not verified against the historical chat_id; it is current descriptive evidence, not crawl-window content.'}
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result

def packet(c,g):
    items=[]
    for row in g.to_dict('records'):
        path=ROOT/'evidence'/f"{row['handle']}.json"
        if not path.exists(): return
        ev=json.loads(path.read_text()); ev.pop('html_file'); ev['description']=ev['description'][:1200]
        # Keep complete evidence on disk; bounded excerpts keep reviewer packets readable.
        for post in ev['recent_posts']: post['text']=post['text'][:900]
        items.append({**row,'evidence_file':str(path),**ev})
    meta=next(x for x in json.loads((ROOT/'communities.json').read_text()) if x['community']==c)
    (ROOT/'packets'/f'community_{c+1:04d}.json').write_text(json.dumps({'community':int(c),'display_id':int(c)+1,'metadata':meta,'channels':items},ensure_ascii=False,indent=2)+'\n')
    if (ROOT/'staged_review_amendment.json').exists():
        qa=[]
        for stratum,count in [('top',1),('random',2)]:
            ordered=sorted([x for x in items if x['stratum']==stratum],key=lambda x:hashlib.sha256(('description-audit-v1|'+x['entity_id']).encode()).hexdigest())
            qa.extend(x['node_id'] for x in ordered[:count])
        for x in items:
            x['post_audit_required']=x['node_id'] in qa;x.pop('recent_posts',None);x.pop('page_sha256',None);x.pop('random_key',None)
        (ROOT/'metadata_packets').mkdir(exist_ok=True)
        (ROOT/'metadata_packets'/f'community_{c+1:04d}.json').write_text(json.dumps({'community':int(c),'display_id':int(c)+1,'metadata':meta,'channels':items},ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--start',type=int,default=1);p.add_argument('--end',type=int,default=142);p.add_argument('--workers',type=int,default=6);a=p.parse_args()
    for folder in ['evidence','pages','packets']: (ROOT/folder).mkdir(exist_ok=True)
    s=pd.read_csv(ROOT/'samples.csv').where(lambda x:pd.notna(x),None)
    s=s[(s.display_id>=a.start)&(s.display_id<=a.end)&s.selected]
    completed=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        for c,g in s.groupby('community',sort=True):
            rows=list(pool.map(fetch,g.to_dict('records')));packet(int(c),g);completed+=len(g)
            print(json.dumps({'community':int(c)+1,'sample':len(g),'channel_evidence':sum(x['public_channel_evidence'] for x in rows),'posts':sum(bool(x['recent_posts']) for x in rows),'completed':completed}),flush=True)
    print('DONE',flush=True)
