/* Hull port, near-edge attachment, multiscale geometry and UI checks. */
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
const root=path.resolve(process.argv[2]),out=path.join(root,'visualization');
const assert=(x,m)=>{if(!x)throw Error(m)};
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',args:['--enable-unsafe-swiftshader']});
 const results=[];
 for(const spec of [{width:1500,height:1000,dpr:1},{width:1500,height:1000,dpr:2},{width:1200,height:800,dpr:1},{width:390,height:844,dpr:2}]){
  const context=await browser.newContext({viewport:{width:spec.width,height:spec.height},deviceScaleFactor:spec.dpr}),page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));await page.goto(pathToFileURL(path.join(out,'crawled_channels_atlas.html')).href);await page.waitForFunction(()=>window.atlas?.metrics.ready);await page.evaluate(()=>draw());
  const initial=await page.evaluate(()=>({metrics:atlas.metrics,plan:JSON.stringify(communityLabelPlan),camera:{...camera},shown:communityLabelBoxes,dimensions:[W,H],nodes:Array.from(nodes.filter((_,i)=>i%14<2))}));
  assert(initial.metrics.N===72326&&initial.metrics.E===820041&&initial.metrics.glError===0,'Frozen graph/GPU regression');
  const expected=spec.width<640?3:8;assert(initial.shown.length===expected,'Wrong overview label count');assert(initial.shown.every((p,i)=>p.rank===i+1),'Overview omits a more important community');
  const structure=await page.evaluate(()=>({planCount:communityLabelPlan.length,allRanked:communityLabelPlan.every((p,i)=>!i||p.rank>communityLabelPlan[i-1].rank&&p.minScale>=communityLabelPlan[i-1].minScale),font:D.label_display.font_css_px,allOneLine:communityLabelPlan.every(p=>p.height===16&&!p.text.includes('\n')),rankList:[...$('communityRanking').querySelectorAll('[data-community]')].map(b=>semanticById.get(+b.dataset.community).rank_subscribers),nodeHits:communityLabelBoxes.filter(p=>labelCollisionIndex()(p.box,-1)).length}));
  assert(structure.planCount===66&&structure.allRanked&&structure.font===11&&structure.allOneLine,'Label plan hierarchy or typography');assert(structure.rankList.join(',')==='1,2,3,4,5,6,7,8','Persistent ranking');

  const hullChecks=await page.evaluate(()=>{
   let portError=0,maxGapError=0,maxBorderGap=0,wrongSide=0,hullIntrusions=0,labelCollisions=0;
   const scales=Array.from({length:181},(_,i)=>baseScale*.25*Math.pow(65536,i/180));
   scales.push(...communityLabelPlan.flatMap(p=>[p.minScale*(1-1e-7),p.minScale,p.minScale*(1+1e-7)]));
   for(const p of communityLabelPlan){
    const [a,b]=p.edge,t=p.fraction;
    portError=Math.max(portError,Math.hypot(p.x-(nval(a,0)*(1-t)+nval(b,0)*t),p.y-(nval(a,1)*(1-t)+nval(b,1)*t)));
    if(a!==b){const dx=nval(b,0)-nval(a,0),dy=nval(b,1)-nval(a,1);if(Math.sign(dy)!==p.side)wrongSide++;const normal=[dy/Math.hypot(dx,dy),-dx/Math.hypot(dx,dy)];for(const id of semanticMembers.get(p.community))if(normal[0]*(nval(id,0)-p.x)+normal[1]*(nval(id,1)-p.y)>1e-5)wrongSide++;}
   }
   for(const scale of scales){
    const active=communityLabelPlan.filter(p=>p.minScale<=scale),boxes=active.map(p=>communityLabelBox(p,scale,false));
    for(let i=0;i<active.length;i++){
     const p=active[i],b=boxes[i],ax=p.x*scale,ay=p.y*scale,r=p.radius_node===null?0:labelWorldRadii[p.radius_node]*labelGlyphScale(scale);
     const dx=ax-Math.max(b[0],Math.min(ax,b[0]+b[2])),dy=ay-Math.max(b[1],Math.min(ay,b[1]+b[3])),gap=Math.hypot(dx,dy)-r;
     maxGapError=Math.max(maxGapError,Math.abs(gap-p.gap));maxBorderGap=Math.max(maxBorderGap,gap);
     const near=p.side>0?b[0]:b[0]+b[2],far=p.side>0?b[0]+b[2]:b[0];if(Math.abs(near-ax)>Math.abs(far-ax)+1e-6)wrongSide++;
     if(p.edge[0]!==p.edge[1]){const nx=p.side/Math.sqrt(1+p.slope*p.slope),ny=-p.slope*nx;for(const [x,y] of [[b[0],b[1]],[b[0]+b[2],b[1]],[b[0],b[1]+b[3]],[b[0]+b[2],b[1]+b[3]]])if(nx*(x-ax)+ny*(y-ay)<-1e-6)hullIntrusions++;}
     for(let j=0;j<i;j++){const c=boxes[j];if(b[0]<c[0]+c[2]-1e-6&&b[0]+b[2]>c[0]+1e-6&&b[1]<c[1]+c[3]-1e-6&&b[1]+b[3]>c[1]+1e-6)labelCollisions++;}
    }
   }
   const overviewOutside=communityLabelBoxes.filter(p=>p.box[0]<0||p.box[1]<0||p.box[0]+p.box[2]>W||p.box[1]+p.box[3]>H).length;
   const start=performance.now();prepareCommunityLabelPlan();const preparationMs=performance.now()-start;
   return {portError,maxGapError,maxBorderGap,wrongSide,hullIntrusions,labelCollisions,overviewOutside,scaleChecks:scales.length,preparationMs,left:communityLabelPlan.filter(p=>p.side<0).length,right:communityLabelPlan.filter(p=>p.side>0).length};
  });
  assert(hullChecks.portError<1e-6&&hullChecks.wrongSide===0&&hullChecks.hullIntrusions===0,'Port or left/right attachment does not match the full community hull');
  assert(hullChecks.maxGapError<1e-5&&hullChecks.maxBorderGap<=8.00001,'Label gap grows with zoom');
  assert(hullChecks.labelCollisions===0&&hullChecks.overviewOutside===0,'Scale collision or clipped overview name');
  await page.screenshot({path:path.join(out,`hull_labels_${spec.width}_dpr${spec.dpr}.png`),fullPage:spec.width<640});
  // Actual pointer pan: labels must translate by the exact same amount as nodes.
  const stage=await page.locator('#stage').boundingBox();await page.mouse.move(stage.x+stage.width*.48,stage.y+stage.height*.85);await page.mouse.down();await page.mouse.move(stage.x+stage.width*.48+31,stage.y+stage.height*.85-17,{steps:8});await page.mouse.up();await page.evaluate(()=>draw());
  const panned=await page.evaluate(()=>({plan:JSON.stringify(communityLabelPlan),camera:{...camera},shown:communityLabelBoxes}));
  assert(panned.plan===initial.plan,'Pan replanned labels');let panError=0,panPairs=0;
  for(const a of initial.shown){const b=panned.shown.find(p=>p.community===a.community);if(!b)continue;panPairs++;panError=Math.max(panError,Math.abs(b.box[0]-a.box[0]-31),Math.abs(b.box[1]-a.box[1]+17));}assert(panPairs===expected&&panError<1e-6,'Labels moved independently of pan');
  await page.locator('#zoomIn').click();await page.evaluate(()=>draw());assert(await page.locator('#tooltip').isHidden(),'Tooltip obscures navigation control');const zoomed=await page.evaluate(()=>({plan:JSON.stringify(communityLabelPlan),camera:{...camera},shown:communityLabelBoxes}));assert(zoomed.plan===initial.plan,'Zoom replanned labels');let zoomError=0;
  for(const a of panned.shown){const b=zoomed.shown.find(p=>p.community===a.community);if(!b)continue;const oldOffset=a.side>0?a.gap:-a.gap-a.width;const oldPort=a.box[0]-oldOffset;const expectedX=(oldPort-initial.dimensions[0]/2)*1.5+initial.dimensions[0]/2+oldOffset;zoomError=Math.max(zoomError,Math.abs(b.box[0]-expectedX));assert(b.width===a.width&&b.height===a.height,'Zoom inflated typography')}assert(zoomError<1e-6,'Zoom anchor drift');
  // Exhaust activation levels and compare all fixed boxes, including offscreen ones.
  const levels=await page.evaluate(()=>{const results=[];let previous=[];for(const z of [.5,.88,1,1.4,1.65,2,2.8,3,4.2,5,8,16]){camera.scale=baseScale*z;draw();const active=communityLabelPlan.filter(p=>p.minScale<=camera.scale),ids=active.map(p=>p.community);let collisions=0;for(let i=0;i<active.length;i++)for(let j=0;j<i;j++){const a=active[i],b=active[j];const aa=communityLabelBox(a,camera.scale,false),bb=communityLabelBox(b,camera.scale,false);if(aa[0]<bb[0]+bb[2]&&aa[0]+aa[2]>bb[0]&&aa[1]<bb[1]+bb[3]&&aa[1]+aa[3]>bb[1])collisions++}results.push({zoom:z,active:active.length,collisions,monotonic:previous.every(id=>ids.includes(id)),nodeHits:communityLabelBoxes.filter(p=>labelCollisionIndex()(p.box,-1)).length});previous=ids}return results});
  assert(levels.every(x=>x.collisions===0&&x.monotonic),'Collisions or names disappear while zooming in');assert(levels.at(-1).active===66,'Names deferred past useful zoom levels');
  await page.evaluate(()=>{reset();camera.scale=baseScale*2;draw()});await page.screenshot({path:path.join(out,`hull_zoom2_${spec.width}_dpr${spec.dpr}.png`)});await page.evaluate(()=>{reset();draw()});
  const beforeSelect=await page.evaluate(()=>({camera:JSON.stringify(camera),counts:[visibleCount,visibleEdges]}));
  await page.locator('#communityRanking button').nth(1).focus();await page.keyboard.press('Enter');await page.evaluate(()=>draw());
  const highlight=await page.evaluate(()=>{let highlighted=0,dimmed=0,wrong=0;for(let j=0;j<N;j++){const id=drawOrder[j],base=color(id),inGroup=Math.round(nval(id,8))===chosenCommunity,expected=inGroup?base:mix(colorRGB(D.style.background),base,.16);if(inGroup)highlighted++;else dimmed++;for(let k=0;k<3;k++)if(Math.abs(nodeData[j*10+3+k]-expected[k])>1e-6)wrong++}return {chosenCommunity,highlighted,dimmed,wrong,camera:JSON.stringify(camera),counts:[visibleCount,visibleEdges],saved:state()}});
  assert(highlight.chosenCommunity===13&&highlight.highlighted===semanticCount(13)&&highlight.wrong===0,'Community highlight incorrect');assert(highlight.camera===beforeSelect.camera&&String(highlight.counts)===String(beforeSelect.counts),'Highlight changed view or filtering');
  assert(await page.locator('#communityRanking button').nth(1).getAttribute('aria-pressed')==='true','Missing accessible selection state');
  await page.screenshot({path:path.join(out,`hull_highlight_${spec.width}_dpr${spec.dpr}.png`),fullPage:spec.width<640});
  await page.evaluate(v=>{reset();loadState(v);draw()},highlight.saved);assert(await page.evaluate(()=>chosenCommunity)===13,'Highlight not restored');
  const atomic=await page.evaluate(()=>{const before=JSON.stringify(state());let error=false;try{loadState({...state(),chosenCommunity:999999})}catch{error=true}return error&&JSON.stringify(state())===before});assert(atomic,'Invalid community view not atomic');
  await page.locator('#locateCommunity').click();assert(await page.evaluate(()=>visibleCount)===72326,'Locate changed filters');
  await page.locator('#communitySection').evaluate(e=>e.open=true);await page.selectOption('#communitySelect','1');assert((await page.locator('#communityReport').innerText()).includes('Russian news'),'Full description unavailable');await page.locator('#communityReport details').evaluate(e=>e.open=true);assert(await page.locator('#communityReport [data-sample]').count()===30,'Evidence samples unavailable');await page.locator('#communityReport [data-sample]').first().click();assert((await page.locator('#details').innerText()).includes('Russian news'),'Node report link regression');
  await page.locator('#advancedControls').evaluate(e=>e.open=true);await page.selectOption('#resolution','2');await page.evaluate(()=>draw());assert(await page.evaluate(()=>communityLabelBoxes.length)===0&&await page.locator('#communitySelect').isDisabled(),'Alternative partition has stale descriptions');await page.selectOption('#resolution','1');await page.selectOption('#weightMode','all');await page.evaluate(()=>draw());assert(await page.evaluate(()=>communityLabelBoxes.length)===0,'All-target stale labels');
  await page.evaluate(()=>{reset();setSubscribers(10000);draw()});assert(await page.evaluate(()=>visibleCount===8788&&visibleEdges===66409),'Subscriber filter regression');assert(await page.evaluate(p=>JSON.stringify(communityLabelPlan)===p,initial.plan),'Filter moved label anchors');
  await page.evaluate(()=>setCore(10));assert(await page.evaluate(()=>subscribersMin===10000&&coreMin===10),'Combined filters');await page.evaluate(()=>{reset();draw()});
  assert(await page.evaluate(xy=>JSON.stringify(Array.from(nodes.filter((_,i)=>i%14<2)))===JSON.stringify(xy),initial.nodes),'Graph coordinates changed');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth)===spec.width,'Horizontal overflow');
  await page.locator('#showCommunityLabels').uncheck();assert(await page.evaluate(()=>state().showCommunityLabels===false),'Toggle persistence');await page.evaluate(()=>draw());assert(await page.evaluate(()=>communityLabelBoxes.length)===0,'Toggle ineffective');
  if(spec.width>=640){await page.locator('#showCommunityLabels').check();await page.setViewportSize({width:390,height:844});await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));await page.evaluate(()=>{fit();draw()});assert(await page.evaluate(()=>communityLabelBoxes.length)===3,'Responsive plan not rebuilt for mobile');}
  await page.goto(pathToFileURL(path.join(out,'community_reports.html')).href);assert(await page.locator('article').count()===66,'Report index missing');await page.locator('#search').fill('username');assert(await page.locator('article:visible').count()>0,'Report search');
  assert(errors.length===0,'Browser errors: '+errors.join('; '));results.push({viewport:spec,structure,hullChecks,panErrorCssPx:panError,zoomErrorCssPx:zoomError,levels,highlight:{members:highlight.highlighted,dimmed:highlight.dimmed,wrongColors:highlight.wrong},errors});await context.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'hull_labels_verification.json'),JSON.stringify(results,null,2)+'\n');console.log('Hull boundary attachment, screen-space gaps, zoom sweeps, navigation and UI checks passed at desktop DPR 1/2 and mobile DPR 2.');
 function semanticCount(cid){return JSON.parse(fs.readFileSync(path.join(root,'labels/community_labels.json'))).communities.find(x=>x.community===cid).nodes}
})().catch(e=>{console.error(e);process.exit(1)});
