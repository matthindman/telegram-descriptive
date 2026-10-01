/* v7 member-anchored community names: invariants, association metrics, navigation and UI.
   Usage: NODE_PATH=<playwright node_modules> node scripts/verify_member_anchored_labels.cjs <atlas root>
   Writes visualization/member_labels_verification.json and member_*.png under <root>.
   Association metrics use the renderer's node diameter() and a brute-force scan of all
   displayed nodes, independent of the planner's spatial index and cost function. */
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
const root=path.resolve(process.argv[2]),out=path.join(root,'visualization');
const assert=(x,m)=>{if(!x)throw Error(m)};
const helpers=`
window.__planDigest=()=>JSON.stringify(communityLabelPlan.map(p=>[p.community,p.anchor,p.side,p.offsetY,p.minScale]));
// Independent geometry: renderer diameters, every displayed node, one label at one scale.
window.__labelGeometry=(p,scale)=>{const saved=camera.scale;camera.scale=scale;const b=communityLabelBox(p,scale,false),gap=p.gap;
 let ownNearest=Infinity,otherNearest=Infinity,otherCovered=0,ownCovered=0,ownArea=0,otherArea=0,anchorGap=NaN;
 for(let i=0;i<N;i++){if(!included(i)||!(nval(i,2)>0))continue;const r=diameter(i)/2,x=nval(i,0)*scale,y=nval(i,1)*scale,dx=x-Math.max(b[0],Math.min(x,b[0]+b[2])),dy=y-Math.max(b[1],Math.min(y,b[1]+b[3])),d=Math.max(0,Math.hypot(dx,dy)-r);
  if(i===p.anchor)anchorGap=Math.hypot(dx,dy)-r;
  if(r<.5||d>40)continue;const own=Math.round(nval(i,8))===p.community;
  if(own){ownNearest=Math.min(ownNearest,d);if(d<1&&i!==p.anchor)ownCovered++;ownArea+=r*r}else{otherNearest=Math.min(otherNearest,d);if(d<1)otherCovered++;otherArea+=r*r}}
 const anchorRadius=diameter(p.anchor)/2;camera.scale=saved;return {ownNearest,otherNearest,otherCovered,ownCovered,ownArea,otherArea,anchorGap,gap,anchorRadius,box:b}};
window.__restoreCamera=c=>{camera=c};
window.__drawnBoxes=()=>{const arr=[];draw();const keep=communityLabelBoxes;drawCommunityNames(arr);communityLabelBoxes=keep;return arr};
`;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',args:['--enable-unsafe-swiftshader']});
 const results=[];
 for(const spec of [{width:1500,height:1000,dpr:1},{width:1500,height:1000,dpr:2},{width:1200,height:800,dpr:1},{width:390,height:844,dpr:2}]){
  const context=await browser.newContext({viewport:{width:spec.width,height:spec.height},deviceScaleFactor:spec.dpr}),page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
  await page.goto(pathToFileURL(path.join(out,'crawled_channels_atlas.html')).href);await page.waitForFunction(()=>window.atlas?.metrics.ready,{},{timeout:120000});await page.evaluate(helpers);await page.evaluate(()=>draw());
  const tag=`${spec.width}_dpr${spec.dpr}`,R={viewport:spec};
  const initial=await page.evaluate(()=>({metrics:atlas.metrics,plan:__planDigest(),shown:communityLabelBoxes.map(p=>({rank:p.rank,community:p.community,box:p.box})),nodes:Array.from(nodes.filter((_,i)=>i%14<2)),overview:W<640?D.label_display.mobile_overview_count:D.label_display.overview_count,planMs:labelPlanMs}));
  assert(initial.metrics.N===72326&&initial.metrics.E===820041&&initial.metrics.glError===0,'Frozen graph/GPU regression');
  assert(initial.shown.map(p=>p.rank).join()===Array.from({length:initial.overview},(_,i)=>i+1).join(),'Overview must show the top-ranked names: '+initial.shown.map(p=>p.rank));
  R.planMs=initial.planMs;
  // 1. Plan invariants: anchors are displayed members; glyph model equals rendered sizes; fixed gap at every zoom.
  R.invariants=await page.evaluate(()=>{let bad=[],gapError=0,modelError=0,wrongSide=0,anchorTooSmall=0,checks=0;const saved=camera.scale;
   for(const p of communityLabelPlan){
    if(Math.round(nval(p.anchor,8))!==p.community||!included(p.anchor)||!(nval(p.anchor,2)>0))bad.push(p.rank);
    for(let k=0;k<240;k++){const s=p.minScale*Math.pow(baseScale*16384/p.minScale,k/239);camera.scale=s;const r=diameter(p.anchor)/2,b=communityLabelBox(p,s,false),ax=nval(p.anchor,0)*s,ay=nval(p.anchor,1)*s;
     const dx=ax-Math.max(b[0],Math.min(ax,b[0]+b[2])),dy=ay-Math.max(b[1],Math.min(ay,b[1]+b[3]));checks++;
     gapError=Math.max(gapError,Math.abs(Math.hypot(dx,dy)-r-p.gap));modelError=Math.max(modelError,Math.abs(labelWorldRadii[p.anchor]*labelGlyphScale(s)-r));
     if(p.side>0?b[0]<ax:b[0]+b[2]>ax)wrongSide++;if(k===0&&r<LABEL_ANCHOR_R-1e-9)anchorTooSmall++}}
   camera.scale=saved;return {planned:communityLabelPlan.length,unplaced:labelUnplaced.map(u=>u.rank+':'+u.text),notAccepted:communityLabelPlan.filter(p=>!p.accepted).map(p=>p.rank),badAnchors:bad,scaleChecks:checks,gapErrorPx:gapError,glyphModelErrorPx:modelError,wrongSide,anchorTooSmall}});
  assert(R.invariants.badAnchors.length===0&&R.invariants.gapErrorPx<1e-6&&R.invariants.glyphModelErrorPx<1e-9&&R.invariants.wrongSide===0&&R.invariants.anchorTooSmall===0,'Member-anchor invariant failed: '+JSON.stringify(R.invariants));
  // 2. Association across zoom (soft metrics, plus hard: the nearest visible own mark is the anchor gap away).
  R.association=await page.evaluate(()=>{const rows=[];let ownBeyondGap=0;
   for(const z of ['entry',1,2,4,8,16,64])for(const p of communityLabelPlan){const s=z==='entry'?p.minScale*1.1:baseScale*z;if(s<p.minScale)continue;const g=__labelGeometry(p,s);
    if(g.ownNearest>p.gap+1e-6)ownBeyondGap++;rows.push({z,rank:p.rank,accepted:p.accepted,otherCovered:g.otherCovered,ownCovered:g.ownCovered,otherDominates:g.otherArea>g.ownArea,otherCloser:g.otherNearest<g.ownNearest})}
   const by={};for(const r of rows){const k=String(r.z);by[k]||={labels:0,other_covered:0,own_covered:0,other_dominates:0,other_closer:0,max_other_covered_one_label:0};const b=by[k];b.labels++;b.other_covered+=r.otherCovered;b.own_covered+=r.ownCovered;b.other_dominates+=r.otherDominates;b.other_closer+=r.otherCloser;b.max_other_covered_one_label=Math.max(b.max_other_covered_one_label,r.otherCovered)}
   return {by_zoom:by,own_mark_beyond_gap:ownBeyondGap}});
  assert(R.association.own_mark_beyond_gap===0,'A drawn name is farther than its gap from every own mark');
  // 3. Label-label collisions under four sizing modes (re-anchored after each sizing change).
  R.collisions=await page.evaluate(()=>{const res={};const S=Array.from({length:3000},(_,i)=>baseScale*.25*Math.pow(65536,i/2999));
   for(const [name,ao,sm] of [['default',true,1],['protect_on_size3',true,3],['protect_off_size1',false,1],['protect_off_size3',false,3]]){avoidOverlap=ao;sizeMul=sm;prepareCommunityLabelPlan();let n=0;
    for(const s of S){const act=communityLabelPlan.filter(q=>q.minScale<=s),bx=act.map(q=>communityLabelBox(q,s,false));for(let i=0;i<act.length;i++)for(let j=0;j<i;j++){const a=bx[i],b=bx[j];if(a[0]<b[0]+b[2]-1e-6&&a[0]+a[2]>b[0]+1e-6&&a[1]<b[1]+b[3]-1e-6&&a[1]+a[3]>b[1]+1e-6)n++}}
    res[name]=n}avoidOverlap=true;sizeMul=1;prepareCommunityLabelPlan();return res});
  assert(Object.values(R.collisions).every(n=>n===0),'Label-label collision: '+JSON.stringify(R.collisions));
  assert(await page.evaluate(p=>__planDigest()===p,initial.plan),'Default plan not reproducible after sizing round trip');
  // 4. Drawn names are never truncated or under map controls (grid of camera positions and zooms).
  R.hud_clip=await page.evaluate(()=>{let drawn=0,violations=[];const c0={...camera};const hud=labelHudRects(0);
   for(const z of [1,1.5,2,3,4,8])for(const fx of [.1,.3,.5,.7,.9])for(const fy of [.1,.3,.5,.7,.9]){camera={x:labelGridX0+fx*labelGridW*labelGridCell,y:labelGridY0+fy*labelGridH*labelGridCell,scale:baseScale*z};
    for(const b of __drawnBoxes()){drawn++;if(b[0]<-.5||b[1]<-.5||b[0]+b[2]>W+.5||b[1]+b[3]>H+.5||hud.some(h=>rectsOverlap(b,h)))violations.push({z,fx,fy,b})}}
   camera=c0;draw();return {drawn,violations:violations.length}});
  assert(R.hud_clip.violations===0,'Truncated or control-covered name');
  // 5. Pointer pan and zoom: plan unchanged; names translate with the camera; gap stays fixed.
  const stage=await page.locator('#stage').boundingBox();await page.mouse.move(stage.x+stage.width*.55,stage.y+stage.height*.8);await page.mouse.down();await page.mouse.move(stage.x+stage.width*.55+31,stage.y+stage.height*.8-17,{steps:8});await page.mouse.up();await page.evaluate(()=>draw());
  const panned=await page.evaluate(()=>({plan:__planDigest(),shown:communityLabelBoxes.map(p=>({community:p.community,box:p.box}))}));
  assert(panned.plan===initial.plan,'Pan replanned names');let panError=0,panPairs=0;for(const a of initial.shown){const b=panned.shown.find(p=>p.community===a.community);if(!b)continue;panPairs++;panError=Math.max(panError,Math.abs(b.box[0]-a.box[0]-31),Math.abs(b.box[1]-a.box[1]+17))}
  assert(panPairs>0&&panError<1e-3,'Names moved independently of pan');R.panErrorPx=panError;
  await page.locator('#zoomIn').click();await page.evaluate(()=>draw());assert(await page.evaluate(p=>__planDigest()===p,initial.plan),'Zoom replanned names');
  // 6. Resize hysteresis (desktop): small resizes keep the plan; a viewport-class change re-plans.
  if(spec.width===1500&&spec.dpr===1){R.resize=[];for(const [w,h] of [[1490,995],[1400,1000],[1500,940],[1500,1000]]){await page.setViewportSize({width:w,height:h});await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));R.resize.push({viewport:[w,h],planUnchanged:await page.evaluate(p=>__planDigest()===p,initial.plan)})}
   assert(R.resize.every(x=>x.planUnchanged),'Small resize changed the name plan');}
  await page.evaluate(()=>{reset();draw()});
  // 7. Filters re-anchor to displayed channels after the change settles.
  R.filters=[];for(const [label,fn] of [['subscribers>=100k',()=>setSubscribers(100000)],['10-core',()=>setCore(10)],['subscribers>=10k',()=>setSubscribers(10000)]]){
   await page.evaluate(fn);await page.evaluate(()=>draw());await page.waitForTimeout(400);
   R.filters.push(await page.evaluate(label=>{draw();let bad=0,beyond=0;for(const p of communityLabelPlan){if(!included(p.anchor))bad++;const s=Math.max(p.minScale*1.1,baseScale*2),g=__labelGeometry(p,s);if(g.ownNearest>p.gap+1e-6)beyond++}
    return {filter:label,keyCurrent:currentLabelFilterKey()===labelPlanKey,planned:communityLabelPlan.length,anchorsNotDisplayed:bad,ownMarkBeyondGap:beyond}},label));
   await page.evaluate(()=>{reset();draw()});}
  assert(R.filters.every(f=>f.keyCurrent&&f.anchorsNotDisplayed===0&&f.ownMarkBeyondGap===0),'Filter re-anchoring failed: '+JSON.stringify(R.filters));
  await page.waitForTimeout(250);await page.evaluate(()=>draw());assert(await page.evaluate(p=>__planDigest()===p,initial.plan),'Reset did not restore the default plan');
  // 7b. Regression (v8): temporary selected-neighbour focus must never restrict the name plan.
  //     Real UI: search a channel, enable neighbour focus, make a material resize, Clear, Reset.
  {const big=spec.width>=640,alt=big?{width:1200,height:800}:{width:700,height:844};
   const handle=await page.evaluate(()=>labels[100]);await page.locator('#search').fill(handle);await page.locator('#searchForm button').click();
   await page.locator('#advancedControls').evaluate(e=>e.open=true);await page.locator('#focusOnly').check();
   await page.setViewportSize(alt);await page.waitForTimeout(350);
   const focused=await page.evaluate(()=>({planned:communityLabelPlan.length,visible:visibleCount}));
   await page.locator('#clear').click();await page.waitForTimeout(350);
   const cleared=await page.evaluate(()=>{draw();const planned=communityLabelPlan.length,digest=__planDigest();prepareCommunityLabelPlan();return {planned,stale:digest!==__planDigest(),checked:$('showCommunityLabels').checked}});
   await page.locator('#reset').click();await page.waitForTimeout(350);
   const afterReset=await page.evaluate(()=>{draw();const planned=communityLabelPlan.length,shown=communityLabelBoxes.length,digest=__planDigest();prepareCommunityLabelPlan();return {planned,shown,stale:digest!==__planDigest(),overview:W<640?D.label_display.mobile_overview_count:D.label_display.overview_count}});
   await page.setViewportSize({width:spec.width,height:spec.height});await page.waitForTimeout(350);await page.evaluate(()=>{reset();draw()});
   const restored=await page.evaluate(p=>__planDigest()===p,initial.plan);
   R.focus_resize_regression={handle,resizedTo:[alt.width,alt.height],focusedVisibleNodes:focused.visible,planDuringFocus:focused.planned,afterClear:cleared,afterReset,restoredOriginalPlan:restored};
   // The plan in force after Clear and after Reset must equal a freshly prepared one (never a focus-restricted plan).
   assert(!cleared.stale&&cleared.planned>=60&&!afterReset.stale&&afterReset.planned>=60&&(big?afterReset.shown===afterReset.overview:afterReset.shown>0)&&restored,'Focus/resize/clear/reset lost community names: '+JSON.stringify(R.focus_resize_regression));
   await page.locator('#focusOnly').uncheck();await page.evaluate(()=>{reset();draw()});}
  // 8. Locate through the actual controls: the community's own name must end up inside the
  //    map AND inside the browser viewport (stacked mobile layouts scroll the page).
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.locator('#communitySection').evaluate(e=>e.open=true);
  const pageVisibleName=()=>page.evaluate(()=>{const cid=chosenCommunity,q=communityLabelPlan.find(x=>x.community===cid);if(!q)return {placed:false};
   const drawn=__drawnBoxes(),b=communityLabelBox(q),shown=drawn.some(x=>Math.abs(x[0]-b[0])<1e-6&&Math.abs(x[1]-b[1])<1e-6),sr=stage.getBoundingClientRect(),hud=labelHudRects(0);
   const pg=[sr.left+b[0],sr.top+b[1],b[2],b[3]],inViewport=pg[0]>=-.5&&pg[1]>=-.5&&pg[0]+pg[2]<=innerWidth+.5&&pg[1]+pg[3]<=innerHeight+.5;
   return {placed:true,shown,inViewport,underControls:hud.some(h=>rectsOverlap(b,h)),pageRect:pg,scrollY}});
  R.locate={located:0,name_visible_in_page:0,exceptions:[]};
  for(const item of await page.evaluate(()=>rankedCommunities().map(x=>({community:x.community,rank:x.rank_subscribers})))){
   await page.selectOption('#communitySelect',String(item.community));await page.locator('#locateCommunity').click();R.locate.located++;
   const v=await pageVisibleName();
   if(v.placed&&v.shown&&v.inViewport&&!v.underControls)R.locate.name_visible_in_page++;else R.locate.exceptions.push(item.rank+':'+(v.placed?JSON.stringify(v):'unplaced'));
  }
  const unplacedRanks=await page.evaluate(()=>labelUnplaced.map(u=>u.rank+':unplaced'));
  assert(R.locate.name_visible_in_page===R.locate.located-unplacedRanks.length&&JSON.stringify(R.locate.exceptions.sort())===JSON.stringify(unplacedRanks.sort()),'Locate did not show the name in the page viewport: '+JSON.stringify(R.locate.exceptions));
  // One default-motion (smooth scroll) case from the first ranked group on stacked layouts.
  await page.emulateMedia({reducedMotion:'no-preference'});await page.evaluate(()=>{reset();window.scrollTo(0,0);draw()});
  await page.locator('#communityRanking button').nth(0).click();await page.locator('#locateCommunity').click();
  await page.waitForFunction(()=>{const q=communityLabelPlan.find(x=>x.community===chosenCommunity),b=communityLabelBox(q),sr=stage.getBoundingClientRect();return sr.top+b[1]>=0&&sr.top+b[1]+b[3]<=innerHeight},{},{timeout:5000});
  R.locate.smooth_scroll_first_rank=await pageVisibleName();assert(R.locate.smooth_scroll_first_rank.inViewport&&R.locate.smooth_scroll_first_rank.shown,'Smooth-scroll Locate');
  await page.evaluate(()=>{reset();window.scrollTo(0,0);draw()});
  // 9. Colours: names match their nodes; ranking colours match; adjacency beats modulo assignment.
  R.colors=await page.evaluate(()=>{let mismatch=0;for(const p of communityLabelPlan){const c=colorRGB(communityColor(p.community)),n=color(p.anchor);if(c.some((v,i)=>Math.abs(v-n[i])>1e-9))mismatch++}
   const rank=[...$('communityRanking').querySelectorAll('[data-community]')].filter(b=>b.querySelector('.rankName').style.color!==(()=>{const e=document.createElement('span');e.style.color=communityColor(+b.dataset.community);return e.style.color})()).length;
   return {labelNodeMismatch:mismatch,rankingMismatch:rank}});
  assert(R.colors.labelNodeMismatch===0&&R.colors.rankingMismatch===0,'Colour mismatch');
  // 10. Highlight: colours only, exact membership, no camera or filter change; keyboard; saved view.
  await page.evaluate(()=>{reset();draw()});const before=await page.evaluate(()=>({camera:JSON.stringify(camera),counts:[visibleCount,visibleEdges]}));
  await page.locator('#communityRanking button').nth(1).focus();await page.keyboard.press('Enter');await page.evaluate(()=>draw());
  R.highlight=await page.evaluate(()=>{let members=0,wrong=0,moved=0;for(let j=0;j<N;j++){const id=drawOrder[j],base=color(id),inGroup=Math.round(nval(id,8))===chosenCommunity,exp=inGroup?base:mix(colorRGB(D.style.background),base,.16);if(inGroup)members++;for(let k=0;k<3;k++)if(Math.abs(nodeData[j*10+3+k]-exp[k])>1e-6)wrong++;if(nodeData[j*10]!==nval(id,0)||nodeData[j*10+2]!==nval(id,2))moved++}return {chosen:chosenCommunity,members,expected:semanticMembers.get(chosenCommunity).length,wrong,moved,camera:JSON.stringify(camera),counts:[visibleCount,visibleEdges],saved:state()}});
  assert(R.highlight.members===R.highlight.expected&&R.highlight.wrong===0&&R.highlight.moved===0,'Highlight membership/colour/size');assert(R.highlight.camera===before.camera&&String(R.highlight.counts)===String(before.counts),'Highlight changed view or filtering');
  assert(await page.locator('#communityRanking button').nth(1).getAttribute('aria-pressed')==='true','Missing accessible selection state');
  await page.screenshot({path:path.join(out,`member_highlight_${tag}.png`),fullPage:spec.width<640});
  await page.evaluate(v=>{reset();loadState(v);draw()},R.highlight.saved);assert(await page.evaluate(c=>chosenCommunity===c,R.highlight.chosen),'Highlight not restored');delete R.highlight.saved;
  // 11. Suppression is explained; faded names are not hit targets; alternative partitions carry no names.
  R.suppression=await page.evaluate(()=>{const out={};reset();setSelection(100);draw();out.selection=[communityLabelBoxes.length,$('communityNameStatus').hidden,$('communityNameStatus').textContent];setSelection(-1);
   $('colorMode').value='core';updateColor();draw();out.core=[communityLabelBoxes.length,$('communityNameStatus').hidden];reset();
   $('resolution').value='2';updateColor();draw();out.resolution2=[communityLabelBoxes.length,$('communityNameStatus').hidden];reset();
   const q=communityLabelPlan.find(p=>p.minScale>baseScale*1.2);camera.scale=q.minScale*1.001;draw();out.fadedHittable=communityLabelBoxes.some(p=>p.community===q.community);reset();draw();return out});
  assert(R.suppression.selection[0]===0&&R.suppression.selection[1]===false&&R.suppression.core[0]===0&&R.suppression.core[1]===false&&R.suppression.resolution2[0]===0&&R.suppression.resolution2[1]===false&&R.suppression.fadedHittable===false,'Suppression hints or faded hit targets');
  // Screenshots at the default view and centred zooms.
  await page.evaluate(()=>{reset();draw()});await page.screenshot({path:path.join(out,`member_labels_${tag}.png`),fullPage:spec.width<640});
  for(const z of [2,4]){await page.evaluate(z=>{reset();camera.scale=baseScale*z;draw()},z);await page.screenshot({path:path.join(out,`member_zoom${z}_${tag}.png`),fullPage:spec.width<640})}
  await page.evaluate(()=>{reset();draw()});
  assert(await page.evaluate(xy=>JSON.stringify(Array.from(nodes.filter((_,i)=>i%14<2)))===JSON.stringify(xy),initial.nodes),'Graph coordinates changed');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth)===spec.width,'Horizontal overflow');
  R.activation=await page.evaluate(()=>Object.fromEntries([1,1.65,2,2.8,4.2,8,16,64].map(z=>[z,communityLabelPlan.filter(q=>q.minScale<=baseScale*z).length])));
  assert(errors.length===0,'Browser errors: '+errors.join('; '));R.errors=errors;results.push(R);await context.close();
  console.log(tag,'ok',JSON.stringify({planned:R.invariants.planned,unplaced:R.invariants.unplaced.length,locate_in_page:R.locate.name_visible_in_page+'/'+R.locate.located,focus_regression:R.focus_resize_regression.afterReset,activation:R.activation}));
 }
 await browser.close();fs.writeFileSync(path.join(out,'member_labels_verification.json'),JSON.stringify(results,null,2)+'\n');
 console.log('Member anchors, fixed gaps, association metrics, collisions, controls/clipping, pan/zoom/resize stability, filters, focus/resize/reset regression, page-visible Locate via real controls, colours, highlight and suppression checks passed.');
})().catch(e=>{console.error(e);process.exit(1)});
