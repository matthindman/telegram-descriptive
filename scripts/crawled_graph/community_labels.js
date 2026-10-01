// Descriptive labels belong only to the frozen reference partition.
let semanticById=new Map(), semanticMembers=new Map(), showCommunityLabels=true, chosenCommunity=null, chosenPartner=null;
let communityLabelBoxes=[],communityLabelPlan=[],communityVisible=new Map();
const shortCommunityName=item=>D.label_display.map_names[String(item.display_id)]||item.label;
const compactAudience=n=>new Intl.NumberFormat('en',{notation:'compact',maximumFractionDigits:1}).format(n);
const rankedCommunities=()=>[...semanticById.values()].sort((a,b)=>a.rank_subscribers-b.rank_subscribers);
// Reference-partition colour of a reviewed community (same palette entry as its nodes).
const communityColor=cid=>PALETTE[colorIndex.reference[(semanticMembers.get(cid)||[0])[0]]];
function updateCommunityVisibility(){communityVisible=new Map();for(const [cid,ids] of semanticMembers)communityVisible.set(cid,ids.some(id=>eligible(id)&&(showZeros||nval(id,2)>0)))}
const referencePartition=()=>weightMode==='valid'&&resolution==='1';
function communityDescription(id){return referencePartition()?semanticById.get(Math.round(nval(id,8))):null}
function semanticDetails(id){const item=communityDescription(id);return item?`<p class="communityTitle">C${item.display_id} · ${escapeHTML(item.label)}</p><p class="hint">${escapeHTML(item.confidence)} confidence · sample-based description</p><button type="button" id="inspectCommunity">Read community report</button>`:referencePartition()?'<p class="hint">This community has not been reviewed.</p>':'<p class="hint">Descriptive labels apply to the reference partition only.</p>'}
function initializeCommunities(){
 const items=D.semantic_labels?.communities||[];
 semanticById=new Map(items.map(x=>[x.community,x]));
 for(const item of items)semanticMembers.set(item.community,[]);
 for(let i=0;i<N;i++)semanticMembers.get(Math.round(nval(i,8)))?.push(i);
 $('communitySelect').innerHTML='<option value="">Choose a reviewed community…</option>'+rankedCommunities().map(x=>`<option value="${x.community}">C${x.display_id} · ${escapeHTML(x.label)} (${fmt(x.nodes)})</option>`).join('');
 $('communityRanking').innerHTML=rankedCommunities().slice(0,8).map(item=>`<button type="button" data-community="${item.community}" aria-pressed="false" title="C${item.display_id} · ${escapeHTML(item.label)} · ${fmt(item.subscribers)} summed subscribers"><span class="rankNumber">${item.rank_subscribers}</span><span class="rankName" style="color:${communityColor(item.community)}">${escapeHTML(shortCommunityName(item))}</span><span class="rankAudience">${compactAudience(item.subscribers)}</span></button>`).join('');
 $('communityRanking').querySelectorAll('[data-community]').forEach(b=>b.onclick=()=>chooseCommunity(Number(b.dataset.community)===chosenCommunity?null:Number(b.dataset.community)));
 $('clearCommunity').onclick=()=>chooseCommunity(null);
 $('communitySearch').oninput=()=>{const q=$('communitySearch').value.toLowerCase();for(const o of $('communitySelect').options)o.hidden=!!o.value&&!o.textContent.toLowerCase().includes(q)};
 $('communitySelect').onchange=()=>chooseCommunity($('communitySelect').value===''?null:Number($('communitySelect').value));
 $('showCommunityLabels').onchange=()=>{showCommunityLabels=$('showCommunityLabels').checked;requestDraw()};
 $('locateCommunity').onclick=()=>locateCommunity(chosenCommunity);
 updateCommunityPanel();
}
function chooseCommunity(cid){chosenCommunity=cid;chosenPartner=null;refreshPartners();$('communitySelect').value=cid===null?'':String(cid);$('communityLocationNote').textContent='';if(selected>=0)setSelection(-1);updateCommunityPanel();updateNodes();requestDraw()}
// ---------------------------------------------------------------------------
// Linked communities of a chosen reference community, from every observed tie (not
// filtered by display controls). weight = sum of fractional tie weights between the
// two groups; out/in split the pair's weight by direction: q(u,v)=1/eligible
// outdegree(u) for each recorded u->v link. affinity = observed / expected among
// EXTERNAL links: expected = X_A*X_B/(2X), where X_c is community c's total
// between-community weight and 2X the sum over all communities (internal ties excluded,
// so cohesive groups are not all scored below 1).
let partnerEndpoints=new Set(),partnerCache=new Map(),partnerSort='weight',partnerExpanded=false,communitySizeCache=null,communityStrengthCache=null;
function communitySizes(){if(!communitySizeCache){communitySizeCache=[];for(let i=0;i<N;i++){const c=Math.round(nval(i,8));communitySizeCache[c]=(communitySizeCache[c]||0)+1}}return communitySizeCache}
function communityStrengths(){if(!communityStrengthCache){const n=communitySizes().length,s=new Float64Array(n),x=new Float64Array(n);let external2=0;for(let j=0;j<E;j++){const w=weightsValid[j],a=Math.round(nval(edges[j*4],8)),b=Math.round(nval(edges[j*4+1],8));s[a]+=w;s[b]+=w;if(a!==b){x[a]+=w;x[b]+=w;external2+=2*w}}communityStrengthCache={s,x,external2}}return communityStrengthCache}
function communityPartners(cid){
 if(partnerCache.has(cid))return partnerCache.get(cid);
 const rows=new Map(),{s,x,external2}=communityStrengths();let external=0;
 for(let j=0;j<E;j++){const u=edges[j*4],v=edges[j*4+1],cu=Math.round(nval(u,8)),cv=Math.round(nval(v,8));if((cu===cid)===(cv===cid))continue;
   const insideIsU=cu===cid,inside=insideIsU?u:v,outside=insideIsU?v:u,other=insideIsU?cv:cu,bits=edges[j*4+3],w=weightsValid[j];
   const out=(insideIsU?bits&1:bits&2)?1/nval(inside,6):0,inn=(insideIsU?bits&2:bits&1)?1/nval(outside,6):0;
   let r=rows.get(other);if(!r){r={community:other,weight:0,out:0,in:0,ties:0};rows.set(other,r)}r.weight+=w;r.out+=out;r.in+=inn;r.ties++;external+=w}
 for(const r of rows.values())r.affinity=r.weight*external2/(x[cid]*x[r.community]);
 const result={rows:[...rows.values()],external,strength:s[cid]};partnerCache.set(cid,result);return result;
}
function refreshPartners(){
 partnerEndpoints=new Set();if(chosenCommunity===null||!referencePartition())return;
 for(let j=0;j<E;j++){const u=edges[j*4],v=edges[j*4+1],cu=Math.round(nval(u,8)),cv=Math.round(nval(v,8));if((cu===chosenCommunity)===(cv===chosenCommunity))continue;
   const outside=cu===chosenCommunity?v:u,other=cu===chosenCommunity?cv:cu;if(chosenPartner===null||other===chosenPartner)partnerEndpoints.add(outside)}
}
function setPartner(cid){chosenPartner=cid===chosenPartner?null:cid;refreshPartners();updateCommunityPanel();updateNodes();requestDraw()}
function partnerName(cid){const item=semanticById.get(cid);return item?`C${item.display_id} · ${shortCommunityName(item)}`:`Group ${cid+1}`}
function partnerHTML(cid){
 // Affinity is unstable for tiny satellite groups whose few outside links all go to this
 // group (they all reach the same maximum), so the affinity ranking uses real groups only.
 const {rows,external,strength}=communityPartners(cid),minTies=10,minSize=20,sizes=communitySizes();
 const list=(partnerSort==='affinity'?rows.filter(r=>r.ties>=minTies&&sizes[r.community]>=minSize).sort((a,b)=>b.affinity-a.affinity||b.weight-a.weight):rows.slice().sort((a,b)=>b.weight-a.weight)).slice(0,partnerExpanded?40:10);
 const pct=x=>(100*x).toFixed(x<.01?1:0)+'%',fmtW=x=>x<.01?x.toExponential(1):x.toFixed(x<1?3:2);
 return `<div class="partners"><div class="partnersHead"><b>Linked communities</b><span class="sortGroup" role="group" aria-label="Sort linked communities"><button type="button" data-psort="weight" aria-pressed="${partnerSort==='weight'}">Weight</button><button type="button" data-psort="affinity" aria-pressed="${partnerSort==='affinity'}">Affinity</button></span></div>
 <p class="hint">${fmt(rows.length)} linked groups · external weight ${fmtW(external)} (${pct(external/strength)} of this group's link weight). Out / in: share of each pair's weight from links this group's channels make, or receive. Affinity = observed ÷ expected from both groups' external (between-group) link weight; above 1 means more than expected${partnerSort==='affinity'?`; ranked among partners with at least ${minSize} channels and ${minTies} ties`:''}. All channels, independent of filters. Click a row to show only that pair's ties.</p>
 <ol class="partnerList">${list.map(r=>`<li><button type="button" data-partner="${r.community}" aria-pressed="${chosenPartner===r.community}" title="${escapeHTML(partnerName(r.community))}"><span class="pRow1"><i style="background:${PALETTE[colorIndex.reference[(semanticMembers.get(r.community)||[firstMember(r.community)])[0]]]}"></i><span class="pName">${escapeHTML(partnerName(r.community))}</span><span class="pNum">${fmtW(r.weight)}</span></span><span class="pRow2">${pct(r.weight/external)} of external · out ${pct(r.out/(r.weight||1))} / in ${pct(r.in/(r.weight||1))} · ×${r.affinity.toFixed(r.affinity<10?1:0)} affinity · ${fmt(r.ties)} ties · ${fmt(sizes[r.community])} ch.</span></button></li>`).join('')}</ol>
 <div class="partnerFoot">${rows.length>10?`<button type="button" id="partnerMore">${partnerExpanded?'Show fewer':'Show more'}</button>`:''}${chosenPartner!==null?`<button type="button" id="partnerAll">Show all linked groups</button>`:''}</div>
 </div>`;
}
let firstMemberCache=null;function firstMember(cid){if(!firstMemberCache){firstMemberCache=new Map();for(let i=0;i<N;i++){const c=Math.round(nval(i,8));if(!firstMemberCache.has(c))firstMemberCache.set(c,i)}}return firstMemberCache.get(cid)??0}
function updateCommunityPanel(){
 $('communitySelect').value=chosenCommunity===null?'':String(chosenCommunity);
 const available=referencePartition();$('communityRanking').querySelectorAll('[data-community]').forEach(b=>{b.disabled=!available;b.setAttribute('aria-pressed',String(available&&Number(b.dataset.community)===chosenCommunity))});$('clearCommunity').hidden=chosenCommunity===null;$('communitySelect').disabled=!available;$('communitySearch').disabled=!available;$('locateCommunity').disabled=!available||chosenCommunity===null;
 $('communityLabelNote').textContent=available?'66 sample-based descriptions. Ranked by full-community subscriber sum, which can count the same people more than once. Each map name sits beside one of its own displayed channels; click a name to highlight every member.':'Descriptions apply to eligible-target weights at γ 1. Return to that partition to use these names.';
 const item=semanticById.get(chosenCommunity);if(!available||!item){$('communityReport').innerHTML='';return}
 const cv=item.evidence_coverage;
 const rows=item.channel_annotations||[];
 $('communityReport').innerHTML=`<h2>C${item.display_id} · ${escapeHTML(item.label)}</h2><p class="hint">${escapeHTML(item.confidence)} confidence · ${fmt(item.nodes)} channels · ${fmt(item.subscribers)} summed subscribers</p><p>${escapeHTML(item.description)}</p>${partnerHTML(item.community)}<p class="hint">Usable evidence: largest ${cv.top.usable}/${cv.top.sampled}; random others ${cv.random.usable}/${cv.random.sampled}. ${cv.random.sampled===0?'Small-group census; no remaining channels.':''}</p><details><summary>Evidence and qualifications</summary><p><b>Largest channels:</b> ${escapeHTML(item.top_summary)}</p><p><b>Random others:</b> ${escapeHTML(item.random_summary)}</p><p><b>Exceptions:</b> ${item.counterexamples.map(escapeHTML).join('; ')||'None identified in the inspected sample.'}</p><p>${item.limitations.map(escapeHTML).join(' ')}</p><p>Current public previews; historical identity and crawl-window content remain unverified.</p><div class="communitySamples">${rows.map(x=>`<p><button type="button" data-sample="${x.node_id}">@${escapeHTML(x.handle)}</button> <span>${escapeHTML(x.stratum)} · ${escapeHTML(x.language)} · ${escapeHTML(x.subject_function)}</span><br>${escapeHTML(x.evidence_summary)} <a href="${escapeHTML(x.source_url||'https://t.me/'+x.handle)}" target="_blank" rel="noreferrer">Public source ↗</a></p>`).join('')}</div></details>`;
 $('communityReport').querySelectorAll('[data-sample]').forEach(b=>b.onclick=()=>setSelection(Number(b.dataset.sample),true));
 $('communityReport').querySelectorAll('[data-partner]').forEach(b=>b.onclick=()=>setPartner(Number(b.dataset.partner)));
 $('communityReport').querySelectorAll('[data-psort]').forEach(b=>b.onclick=()=>{partnerSort=b.dataset.psort;updateCommunityPanel()});
 if($('partnerMore'))$('partnerMore').onclick=()=>{partnerExpanded=!partnerExpanded;updateCommunityPanel()};
 if($('partnerAll'))$('partnerAll').onclick=()=>setPartner(chosenPartner);
}
// Map controls that sit over the canvas; names never draw beneath them.
function labelHudRects(pad=4){const sr=stage.getBoundingClientRect();return [...stage.querySelectorAll('.toolbar,.legend,#viewStatus')].filter(el=>el.offsetParent!==null&&getComputedStyle(el).visibility!=='hidden').map(el=>{const b=el.getBoundingClientRect();return [b.left-sr.left-pad,b.top-sr.top-pad,b.width+2*pad,b.height+2*pad]})}
const rectsOverlap=(a,b)=>a[0]<b[0]+b[2]&&a[0]+a[2]>b[0]&&a[1]<b[1]+b[3]&&a[1]+a[3]>b[1];
// Free map areas for camera fitting: right of the control column, and below it.
function labelFreeRects(){
 const hud=labelHudRects(8),m=12,status=hud.find(h=>h[1]>H/2),top=hud.filter(h=>h[1]<=H/2);
 const bottom=(status?status[1]:H)-m,right=Math.max(m,...top.map(h=>h[0]+h[2]))+4,below=Math.max(m,...top.map(h=>h[1]+h[3]))+4;
 return [[right,m,W-m-right,bottom-m],[m,below,W-2*m,bottom-below]].filter(r=>r[2]>40&&r[3]>40);
}
function locateCommunity(cid){
 if(cid===null||!referencePartition())return;
 const ids=(semanticMembers.get(cid)||[]).filter(i=>eligible(i)&&nval(i,2)>0);
 if(!ids.length){$('communityLocationNote').textContent='No members pass the current filters. Lower the subscriber or core threshold to locate this community.';return}
 if(labelPlanTimer||currentLabelFilterKey()!==labelPlanKey)prepareCommunityLabelPlan();
 let minx=Infinity,miny=Infinity,maxx=-Infinity,maxy=-Infinity;
 for(const i of ids){minx=Math.min(minx,nval(i,0));maxx=Math.max(maxx,nval(i,0));miny=Math.min(miny,nval(i,1));maxy=Math.max(maxy,nval(i,1))}
 const p=communityLabelPlan.find(q=>q.community===cid&&eligible(q.anchor));
 // Content = members plus this community's name box, in unprojected pixels at scale s.
 const content=s=>{const pad=Math.max(6,labelMaxWorldRadius*labelGlyphScale(s)*.5);let b=[minx*s-pad,miny*s-pad,maxx*s+pad,maxy*s+pad];if(p){const q=communityLabelBox(p,s,false);b=[Math.min(b[0],q[0]),Math.min(b[1],q[1]),Math.max(b[2],q[0]+q[2]),Math.max(b[3],q[1]+q[3])]}return b};
 const clampScale=s=>Math.max(baseScale*.25,Math.min(baseScale*16384,s));
 let best=null;
 for(const r of labelFreeRects()){
   let s=clampScale(Math.min(r[2]/Math.max(maxx-minx,30),r[3]/Math.max(maxy-miny,30)));
   for(let k=0;k<30;k++){const b=content(s),fit=Math.min(r[2]/(b[2]-b[0]),r[3]/(b[3]-b[1]));if(fit>=1-1e-6)break;s=clampScale(s*Math.max(.5,fit*.995))}
   // Prefer a scale at which the name is already active, if the content still fits.
   if(p&&s<p.minScale*1.08){const t=clampScale(p.minScale*1.08),b=content(t);if(b[2]-b[0]<=r[2]&&b[3]-b[1]<=r[3])s=t}
   const b=content(s),ok=b[2]-b[0]<=r[2]+1e-6&&b[3]-b[1]<=r[3]+1e-6,score=(ok?0:1e9)+(p&&s>=p.minScale?0:1e6)-s;
   if(!best||score<best.score)best={score,s,r,b};
 }
 if(!best){fit();return}
 let {s,r,b}=best,partial=false;
 // If every member fits only below the name's activation scale, show the name at its
 // activation scale instead, centred on the name and its anchor; say that members extend beyond.
 if(p&&s<p.minScale){const rects=labelFreeRects().sort((u,v)=>v[2]*v[3]-u[2]*u[3]);const t=clampScale(p.minScale*1.08),q=communityLabelBox(p,t,false),ax=nval(p.anchor,0)*t,ay=nval(p.anchor,1)*t;
   const nb=[Math.min(q[0],ax),Math.min(q[1],ay),Math.max(q[0]+q[2],ax),Math.max(q[1]+q[3],ay)];const rr=rects.find(x=>nb[2]-nb[0]<=x[2]&&nb[3]-nb[1]<=x[3]);
   if(rr){s=t;r=rr;b=nb;partial=true}}
 camera.scale=s;camera.x=((b[0]+b[2])/2-(r[0]+r[2]/2-W/2))/s;camera.y=((b[1]+b[3])/2-(r[1]+r[3]/2-H/2))/s;
 $('communityLocationNote').textContent=partial?`Showing the name beside one of ${fmt(ids.length)} displayed members; some members extend beyond the view. Zoom out to see all of them.`:`Located ${fmt(ids.length)} displayed members${p&&s<p.minScale?'; zoom in slightly to reveal the name':''}. Other communities remain visible.`;
 setSelection(-1);draw();revealMapInPage(p);
}
// On stacked (narrow) layouts the map can sit above the page viewport while the user
// operates controls below it. Explicit Locate scrolls the map, or at least the name
// when the map is taller than the viewport, into the visible page. Highlighting alone
// never scrolls.
function revealMapInPage(p){
 const sr=stage.getBoundingClientRect(),vh=window.innerHeight;let top=sr.top,bottom=sr.bottom;
 if(sr.height>vh&&p&&camera.scale>=p.minScale){const b=communityLabelBox(p);top=sr.top+b[1]-24;bottom=sr.top+b[1]+b[3]+24}
 const delta=top<0?top:bottom>vh?Math.min(bottom-vh,top):0;
 if(Math.abs(delta)>.5)window.scrollBy({top:delta,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
}
// ---------------------------------------------------------------------------
// Member-anchored community names.
// A name attaches to one real member glyph of its community: text to the right is
// left-aligned, text to the left is right-aligned, and the near edge stays a fixed
// CSS-pixel gap beyond that glyph's rendered edge at every zoom. Candidate anchors
// are visible members that are boundary-PREFERRED, not guaranteed: convex-hull
// vertices and left/right extremes of label-height bands of members visible at entry
// (these can lie inside the full-membership hull). Each candidate is scored over its
// whole active zoom range for (1) other communities' marks under or near the text,
// (2) own marks under the text, (3) whether its own community dominates the
// surrounding marks, (4) closeness to the visible hull border, and (5) collisions
// with higher-priority names, which may delay activation. Plans are frozen during
// pan/zoom; filters and node-size changes re-anchor after the change settles.
const LABEL_H=16,LABEL_ANCHOR_R=1.25,LABEL_VISIBLE_R=.5,LABEL_RING=24,LABEL_SCALES=[1,1.3,1.8,2.5,4,8,16,64];
let labelWorldRadii,labelGrid,labelGridCell=64,labelGridX0=0,labelGridY0=0,labelGridW=1,labelGridH=1,labelMaxWorldRadius=0,labelOverviewCenter=[0,0];
let labelRefCommunity,labelActive,labelUnplaced=[],labelPlanKey='',labelPlanView=null,labelPlanTimer=0,labelPlanMs=0;
function labelGlyphScale(scale){
 const ref=2*D.layout.overlap_removal.radius_reference*Math.sqrt(D.style.subscriber_reference/D.layout.overlap_removal.radius_reference_count);
 const desired=D.style.reference_diameter_css_px*sizeMul*Math.sqrt(scale/baseScale);
 return (avoidOverlap?Math.min(desired,ref*scale):desired)/ref;
}
const labelAnchorRadius=(p,scale)=>labelWorldRadii[p.anchor]*labelGlyphScale(scale);
function communityLabelBox(p,scale=camera.scale,project=true){
 const near=nval(p.anchor,0)*scale+p.side*(labelAnchorRadius(p,scale)+p.gap);
 const box=[p.side<0?near-p.width:near,nval(p.anchor,1)*scale+p.offsetY,p.width,p.height];
 if(project){box[0]+=W/2-camera.x*scale;box[1]+=H/2-camera.y*scale}
 return box;
}
// Scale interval on which two labels overlap (plus clearance), starting at `start`.
// Box x-extents depend on the anchor's glyph radius r(s)=R·g(s). g(s)/s never
// increases with s (sqrt growth, optionally capped by overlap protection), so for
// s>=start r(s)<=R·c·s with c=g(start)/start; a 10% margin covers small resizes.
// The envelope is linear in s, so four linear inequalities bound the overlap.
function labelCollisionScaleEnd(a,b,start){
 let lo=start,hi=Infinity;const c=1.1*labelGlyphScale(start)/start;
 const bounds=p=>{const r=labelWorldRadii[p.anchor]*c,x=nval(p.anchor,0);return [x-(p.side<0?r:0),x+(p.side>0?r:0),p.side>0?p.gap:-p.gap-p.width]};
 const [al,ar,ao]=bounds(a),[bl,br,bo]=bounds(b),ay=nval(a.anchor,1),by=nval(b.anchor,1),clearance=4;
 for(const [A,B] of [[al-br,bo+b.width+clearance-ao],[bl-ar,ao+a.width+clearance-bo],[ay-by,b.offsetY+b.height+clearance-a.offsetY],[by-ay,a.offsetY+a.height+clearance-b.offsetY]]){
   if(Math.abs(A)<1e-12){if(B<=0)return start;continue}
   if(A>0)hi=Math.min(hi,B/A);else lo=Math.max(lo,B/A);
 }
 return hi>lo+1e-10?hi:start;
}
function buildLabelSpatialIndex(){
 labelWorldRadii=new Float64Array(N);labelMaxWorldRadius=0;labelRefCommunity=new Int32Array(N);let minx=Infinity,miny=Infinity,maxx=-Infinity,maxy=-Infinity;
 for(let id=0;id<N;id++){
   minx=Math.min(minx,nval(id,0));miny=Math.min(miny,nval(id,1));maxx=Math.max(maxx,nval(id,0));maxy=Math.max(maxy,nval(id,1));
   const r=D.layout.overlap_removal.radius_reference*Math.sqrt(nval(id,2)/D.layout.overlap_removal.radius_reference_count);labelWorldRadii[id]=r;labelMaxWorldRadius=Math.max(labelMaxWorldRadius,r);labelRefCommunity[id]=Math.round(nval(id,8));
 }
 labelOverviewCenter=[(minx+maxx)/2,(miny+maxy)/2];labelGridX0=minx;labelGridY0=miny;
 labelGridW=Math.floor((maxx-minx)/labelGridCell)+1;labelGridH=Math.floor((maxy-miny)/labelGridCell)+1;
 const lists=Array.from({length:labelGridW*labelGridH},()=>[]);
 for(let id=0;id<N;id++)if(labelWorldRadii[id]>0)lists[Math.floor((nval(id,1)-miny)/labelGridCell)*labelGridW+Math.floor((nval(id,0)-minx)/labelGridCell)].push(id);
 // Largest glyphs first: a scan can stop once glyphs fall below visibility.
 labelGrid=lists.map(l=>Int32Array.from(l.sort((a,b)=>labelWorldRadii[b]-labelWorldRadii[a]||a-b)));
}
// Visible marks (radius >= LABEL_VISIBLE_R px) of displayed channels near a box.
function labelNeighborhood(p,scale){
 const b=communityLabelBox(p,scale,false),g=labelGlyphScale(scale),ring=LABEL_RING,rmax=labelMaxWorldRadius*g,minR=LABEL_VISIBLE_R/g;
 const gx0=Math.max(0,Math.floor(((b[0]-ring-rmax)/scale-labelGridX0)/labelGridCell)),gx1=Math.min(labelGridW-1,Math.floor(((b[0]+b[2]+ring+rmax)/scale-labelGridX0)/labelGridCell));
 const gy0=Math.max(0,Math.floor(((b[1]-ring-rmax)/scale-labelGridY0)/labelGridCell)),gy1=Math.min(labelGridH-1,Math.floor(((b[1]+b[3]+ring+rmax)/scale-labelGridY0)/labelGridCell));
 const m={ownCover:0,otherCover:0,ownMass:0,otherMass:0,nearestOther:Infinity,otherCommunity:-1};
 for(let gy=gy0;gy<=gy1;gy++)for(let gx=gx0;gx<=gx1;gx++){const list=labelGrid[gy*labelGridW+gx];
   for(let k=0;k<list.length;k++){const id=list[k],rw=labelWorldRadii[id];if(rw<minR)break;if(!labelActive[id])continue;
     const r=rw*g,x=nval(id,0)*scale,y=nval(id,1)*scale,dx=x-Math.max(b[0],Math.min(x,b[0]+b[2])),dy=y-Math.max(b[1],Math.min(y,b[1]+b[3])),d=Math.max(0,Math.hypot(dx,dy)-r);
     if(d>ring)continue;const w=(1-d/ring)*r*r;
     if(labelRefCommunity[id]===p.community){m.ownMass+=w;if(d<1&&id!==p.anchor)m.ownCover++}
     else{m.otherMass+=w;if(d<1)m.otherCover++;if(d<m.nearestOther){m.nearestOther=d;m.otherCommunity=labelRefCommunity[id]}}
   }}
 return m;
}
function labelScaleCost(p,scale){
 const m=labelNeighborhood(p,scale),share=m.otherMass/(m.ownMass+m.otherMass+1e-9);
 // The nearest foreign mark should be clearly farther than the attachment gap.
 const crowd=m.nearestOther<p.gap+4?1-m.nearestOther/(p.gap+4):0;
 return {cost:50*m.otherCover+18*m.ownCover+70*share+35*crowd,m};
}
function convexHullIds(ids){
 const pts=ids.slice().sort((a,b)=>nval(a,0)-nval(b,0)||nval(a,1)-nval(b,1)||a-b);if(pts.length<3)return pts;
 const cross=(o,a,b)=>(nval(a,0)-nval(o,0))*(nval(b,1)-nval(o,1))-(nval(a,1)-nval(o,1))*(nval(b,0)-nval(o,0));
 const lower=[],upper=[];for(const p of pts){while(lower.length>=2&&cross(lower.at(-2),lower.at(-1),p)<=0)lower.pop();lower.push(p)}
 for(let i=pts.length-1;i>=0;i--){const p=pts[i];while(upper.length>=2&&cross(upper.at(-2),upper.at(-1),p)<=0)upper.pop();upper.push(p)}
 return lower.slice(0,-1).concat(upper.slice(0,-1));
}
function pointInHull(hull,x,y){if(hull.length<3)return false;let sign=0;for(let i=0;i<hull.length;i++){const a=hull[i],b=hull[(i+1)%hull.length],c=(nval(b,0)-nval(a,0))*(y-nval(a,1))-(nval(b,1)-nval(a,1))*(x-nval(a,0));if(Math.abs(c)<1e-9)continue;const s=Math.sign(c);if(!sign)sign=s;else if(s!==sign)return false}return true}
function distanceToHull(hull,x,y){if(hull.length<2)return hull.length?Math.hypot(x-nval(hull[0],0),y-nval(hull[0],1)):Infinity;let best=Infinity;for(let i=0;i<hull.length;i++){const a=hull[i],b=hull[(i+1)%hull.length],ax=nval(a,0),ay=nval(a,1),dx=nval(b,0)-ax,dy=nval(b,1)-ay,t=Math.max(0,Math.min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy||1)));best=Math.min(best,Math.hypot(x-ax-t*dx,y-ay-t*dy))}return best}
// Smallest scale >= start at which some displayed member reaches the anchor radius.
function anchorVisibleScale(ids,start){
 let rw=0;for(const id of ids)rw=Math.max(rw,labelWorldRadii[id]);if(rw<=0)return Infinity;
 if(rw*labelGlyphScale(start)>=LABEL_ANCHOR_R)return start;
 let lo=start,hi=baseScale*16384;if(rw*labelGlyphScale(hi)<LABEL_ANCHOR_R)return Infinity;
 for(let k=0;k<60;k++){const mid=Math.sqrt(lo*hi);if(rw*labelGlyphScale(mid)>=LABEL_ANCHOR_R)hi=mid;else lo=mid}
 return hi;
}
function labelCandidates(item,ids,scale,width){
 const g=labelGlyphScale(scale),vis=ids.filter(id=>labelWorldRadii[id]*g>=LABEL_ANCHOR_R);if(!vis.length)return {list:[],hull:[]};
 const hull=convexHullIds(vis),band=LABEL_H/scale,byBand=new Map();
 for(const id of vis){const k=Math.floor(nval(id,1)/band),e=byBand.get(k);if(!e)byBand.set(k,[id,id]);else{if(nval(id,0)<nval(e[0],0))e[0]=id;if(nval(id,0)>nval(e[1],0))e[1]=id}}
 const pick=side=>{const set=new Set(hull);for(const e of byBand.values())set.add(side<0?e[0]:e[1]);let arr=[...set].sort((a,b)=>nval(a,1)-nval(b,1)||a-b);if(arr.length>48){const keep=new Set(hull);arr=arr.filter((id,i)=>keep.has(id)||i%Math.ceil(arr.length/48)===0)}return arr};
 const list=[];
 for(const side of [-1,1])for(const anchor of pick(side))for(const offsetY of [-LABEL_H/2,-LABEL_H+2,-2])
   list.push({community:item.community,anchor,side,offsetY,width,height:LABEL_H,gap:D.label_display.hull_gap_css_px});
 return {list,hull};
}
function labelHullIntrusion(p,hull,scale){
 // Fraction of nine sample points of the text box inside the community's visible-member hull.
 const b=communityLabelBox(p,scale,false);let inside=0;
 for(const fx of [0,.5,1])for(const fy of [0,.5,1])if(pointInHull(hull,(b[0]+fx*b[2])/scale,(b[1]+fy*b[3])/scale))inside++;
 return inside/9;
}
// Every input to eligible() and to glyph sizes; the viewport is tracked by labelPlanView.
// Keep this in step with eligible(): a missing dependency leaves a stale plan current.
function currentLabelFilterKey(){return JSON.stringify([subscribersMin,coreMin,scope,sizeMul,avoidOverlap])}
function prepareCommunityLabelPlan(){
 const t0=performance.now();clearTimeout(labelPlanTimer);labelPlanTimer=0;
 if(!labelGrid)buildLabelSpatialIndex();
 labelActive=new Uint8Array(N);for(let i=0;i<N;i++)labelActive[i]=eligible(i)&&nval(i,2)>0?1:0;
 const cfg=D.label_display,mobile=W<640,overview=mobile?cfg.mobile_overview_count:cfg.overview_count,hud=labelHudRects(6);
 ctx.font=`500 ${cfg.font_css_px}px system-ui`;communityLabelPlan=[];labelUnplaced=[];
 for(const item of rankedCommunities()){
   const ids=(semanticMembers.get(item.community)||[]).filter(id=>labelActive[id]);if(!ids.length)continue;
   const rank=item.rank_subscribers,text=shortCommunityName(item),width=ctx.measureText(text).width+4;
   const level=rank<=overview?.88:rank<=20?1.65:rank<=50?2.8:4.2;
   const initialScale=anchorVisibleScale(ids,baseScale*level);if(!Number.isFinite(initialScale)||initialScale>baseScale*16384)continue;
   const {list}=labelCandidates(item,ids,initialScale,width);if(!list.length)continue;
   // Border closeness is measured against every displayed member, not only the marks visible at entry.
   const hull=convexHullIds(ids);
   const center=[nval(item.anchor_node,0),nval(item.anchor_node,1)];
   // Stage 1: the entry scale, where a text box covers the largest map area.
   const staged=list.map(p=>{
     let fixed=20*labelHullIntrusion(p,hull,initialScale)+.6*distanceToHull(hull,nval(p.anchor,0),nval(p.anchor,1))*initialScale+(p.offsetY===-LABEL_H/2?0:2)+.004*Math.hypot(nval(p.anchor,0)-center[0],nval(p.anchor,1)-center[1])*baseScale;
     if(rank<=overview){const b=communityLabelBox(p,baseScale,false);b[0]+=W/2-labelOverviewCenter[0]*baseScale;b[1]+=H/2-labelOverviewCenter[1]*baseScale;
       const out=Math.max(0,8-b[0])+Math.max(0,b[0]+b[2]-W+8)+Math.max(0,8-b[1])+Math.max(0,b[1]+b[3]-H+8);if(out>0)fixed+=400+20*out;
       for(const h of hud)if(rectsOverlap(b,h))fixed+=400;}
     // Account for collisions with already planned (higher-ranked) names here too,
     // so the shortlist is not filled with candidates that would all be delayed.
     let entry=initialScale;for(const other of communityLabelPlan){const probe={...p,minScale:entry},end=labelCollisionScaleEnd(probe,other,Math.max(entry,other.minScale));if(end>Math.max(entry,other.minScale))entry=end*(1+1e-6)}
     const late=Number.isFinite(entry)?1000*Math.log(entry/initialScale)+(rank<=overview&&entry*1.08>baseScale?800:0):1e9;
     return {p,fixed,entry,first:fixed+late+labelScaleCost(p,Number.isFinite(entry)?entry:initialScale).cost};
   }).sort((a,b)=>a.first-b.first);
   // Overview-tier names must be fully visible in the default view: when any candidate
   // allows that, only such candidates are considered (best association among them).
   const onTime=rank<=overview?staged.filter(x=>x.entry*1.08<=baseScale):[];
   const shortlist=(onTime.length?onTime:staged).slice(0,16);
   // Stage 2: the full active range. Try the earliest activation first; accept a
   // placement only if its worst sampled scale keeps foreign marks essentially
   // clear (cost <= label_display.accept_cost). Later delays trade entry scale for clearer
   // association. Overview names always take their best placement; other names
   // without an acceptable placement stay off the map (the ranked list and search
   // still reach them) rather than sit on another community.
   let best=null,fallback=null;
   for(const delay of rank<=overview?[1]:[1,1.4,2,3,4.5,7,11,16,24]){
     for(const {p:base,fixed} of shortlist){
       const p={...base,rank,text,minScale:initialScale*delay};
       for(const other of communityLabelPlan){const end=labelCollisionScaleEnd(p,other,Math.max(p.minScale,other.minScale));if(end>Math.max(p.minScale,other.minScale))p.minScale=end*(1+1e-6)}
       if(!Number.isFinite(p.minScale)||p.minScale>baseScale*16384)continue;
       const samples=LABEL_SCALES.map(z=>labelScaleCost(p,p.minScale*z));
       const costs=samples.map(x=>x.cost),worst=Math.max(...costs),mean=costs.reduce((a,b)=>a+b,0)/costs.length;
       // Overview names must be fully faded in at the default view (fade spans 8% of scale).
       const overviewLate=rank<=overview&&p.minScale*1.08>baseScale?(onTime.length?1e9:800):0;
       const score=fixed+overviewLate+1000*Math.log(p.minScale/initialScale)+.6*worst+mean;
       const plan={...p,score,worstCost:worst,sampleCosts:costs,sampleMetrics:samples.map(x=>x.m),hullDistancePx:distanceToHull(hull,nval(p.anchor,0),nval(p.anchor,1))*initialScale,entryScale:initialScale};
       if(!fallback||score<fallback.score)fallback=plan;
       if(worst<=D.label_display.accept_cost&&(!best||score<best.score))best=plan;
     }
     if(best)break;
   }
   const chosen=best||(rank<=overview?fallback:null);
   if(chosen)communityLabelPlan.push({...chosen,accepted:!!best});else labelUnplaced.push({community:item.community,rank,text,bestWorstCost:fallback?fallback.worstCost:null});
 }
 labelPlanKey=currentLabelFilterKey();labelPlanView={W,H,base:baseScale,mobile};labelPlanMs=performance.now()-t0;
}
// Resizing keeps the plan unless the viewport class or overview scale changes materially.
function labelPlanNeedsViewportReplan(){if(!labelPlanView)return true;const v=labelPlanView;return v.mobile!==(W<640)||Math.abs(Math.log(baseScale/v.base))>Math.log(1.12)||Math.abs(W/v.W-1)>.12||Math.abs(H/v.H-1)>.12}
function scheduleLabelPlan(){clearTimeout(labelPlanTimer);labelPlanTimer=setTimeout(()=>{prepareCommunityLabelPlan();requestDraw()},160)}
function communityNameSuppression(){
 if(!showCommunityLabels)return '';
 if(!referencePartition())return 'Names are hidden for alternative partitions; they describe the reference partition (eligible targets, γ 1).';
 if(colorMode!=='community')return 'Names appear only with Structural community node colors.';
 if(selected>=0)return 'Names are hidden while a channel is selected. Clear the selection to show them.';
 return '';
}
function communityLabelHit(x,y){return communityLabelBoxes.find(p=>x>=p.box[0]&&x<=p.box[0]+p.box[2]&&y>=p.box[1]&&y<=p.box[1]+p.box[3])}
function drawCommunityNames(boxes){
 communityLabelBoxes=[];
 const reason=communityNameSuppression(),status=$('communityNameStatus');if(status){status.textContent=reason;status.hidden=!reason}
 if(!showCommunityLabels||reason)return;
 if(currentLabelFilterKey()!==labelPlanKey&&!labelPlanTimer)scheduleLabelPlan();
 ctx.font=`500 ${D.label_display.font_css_px}px system-ui`;ctx.textBaseline='middle';ctx.lineJoin='round';
 const hud=labelHudRects(2);
 for(const p of communityLabelPlan){
   // Anchor must still be a displayed channel (filters may change before re-anchoring settles).
   if(camera.scale<p.minScale||!eligible(p.anchor)||!(nval(p.anchor,2)>0)||!communityVisible.get(p.community))continue;
   const box=communityLabelBox(p);
   // Never draw truncated names or names beneath map controls.
   if(box[0]<-.5||box[1]<-.5||box[0]+box[2]>W+.5||box[1]+box[3]>H+.5||hud.some(h=>rectsOverlap(box,h)))continue;
   const x=p.side>0?box[0]+2:box[0]+box[2]-2,y=box[1]+box[3]/2,fade=Math.min(1,(camera.scale/p.minScale-1)/.08);
   ctx.textAlign=p.side>0?'left':'right';
   ctx.globalAlpha=(chosenCommunity!==null&&chosenCommunity!==p.community?.27:1)*fade;
   ctx.strokeStyle=D.style.background;ctx.lineWidth=3;ctx.strokeText(p.text,x,y);
   ctx.fillStyle=communityColor(p.community);ctx.fillText(p.text,x,y);
   boxes.push(box);if(fade>=.5)communityLabelBoxes.push({...p,box});
 }
 ctx.globalAlpha=1;ctx.textAlign='left';ctx.textBaseline='alphabetic';ctx.font='11px system-ui';
}
