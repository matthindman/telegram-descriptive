/* Focused browser checks for the semantic-label layer; geometry/rendering unchanged. */
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
const root=path.resolve(process.argv[2]),out=path.join(root,'visualization');
const semantic=JSON.parse(fs.readFileSync(path.join(root,'labels/community_labels.json')));
const assert=(x,m)=>{if(!x)throw Error(m)};
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',args:['--enable-unsafe-swiftshader']});
 const results=[];
 for(const dpr of [1,2]){
  const ctx=await browser.newContext({viewport:{width:1500,height:1000},deviceScaleFactor:dpr}),page=await ctx.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.join(out,'crawled_channels_atlas.html')).href);await page.waitForFunction(()=>window.atlas?.metrics.ready);
  await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  const before=await page.evaluate(()=>({metrics:atlas.metrics,xy:Array.from(nodes.filter((_,i)=>i%14<2)),groups:semanticById.size,order:[...semanticById.values()].map(x=>x.rank_subscribers)}));
  assert(before.groups===semantic.communities.length,'Missing community labels');
  assert(before.order.every((x,i)=>i===0||x>before.order[i-1]),'Community menu is not subscriber-ranked');
  assert(before.metrics.N===72326&&before.metrics.E===820041&&before.metrics.glError===0,'Graph changed or GPU error');
  const collisions=await page.evaluate(()=>{
   const check=labelCollisionIndex();let overlaps=0,nodeHits=0;
   for(let i=0;i<communityLabelBoxes.length;i++){const a=communityLabelBoxes[i].box;if(check(a,-1))nodeHits++;for(let j=0;j<i;j++){const b=communityLabelBoxes[j].box;if(a[0]<b[0]+b[2]&&a[0]+a[2]>b[0]&&a[1]<b[1]+b[3]&&a[1]+a[3]>b[1])overlaps++}}
   return {overlaps,nodeHits,labels:communityLabelBoxes.length,ids:communityLabelBoxes.map(x=>x.community+1)};
  });assert(collisions.labels>0&&collisions.overlaps===0&&collisions.nodeHits===0,'Label collisions');
  await page.screenshot({path:path.join(out,`atlas_labels_dpr${dpr}.png`)});
  const first=semantic.communities[0];await page.selectOption('#communitySelect',String(first.community));
  assert((await page.locator('#communityReport').innerText()).includes(first.label),'Community report text');
  await page.locator('#communityReport details').evaluate(e=>e.open=true);
  assert(await page.locator('#communityReport [data-sample]').count()===first.channel_annotations.length,'Missing sampled channel links');
  await page.locator('#locateCommunity').click();
  assert((await page.evaluate(()=>atlas.metrics.visibleCount))===72326,'Locate unexpectedly filtered graph');
  await page.screenshot({path:path.join(out,`atlas_community_detail_dpr${dpr}.png`)});
  await page.locator('#communityReport [data-sample]').first().click();
  assert((await page.locator('#details').innerText()).includes(first.label),'Node details missing community description');
  await page.locator('#resolution').selectOption('2');await page.evaluate(()=>draw());
  assert(await page.locator('#communitySelect').isDisabled(),'Alternative partition permits mismatched report');
  assert((await page.evaluate(()=>communityLabelBoxes.length))===0,'Labels transferred to alternative partition');
  assert(!(await page.locator('#details').innerText()).includes(first.label),'Node detail uses wrong partition label');
  await page.locator('#resolution').selectOption('1');await page.locator('#weightMode').selectOption('all');await page.evaluate(()=>draw());
  assert((await page.evaluate(()=>communityLabelBoxes.length))===0&&await page.locator('#communitySelect').isDisabled(),'All-target labels mismatch');
  await page.locator('#reset').click();await page.locator('#subs10k').click();
  assert((await page.evaluate(()=>atlas.metrics.visibleCount))===8788&&(await page.evaluate(()=>atlas.metrics.visibleEdges))===66409,'Subscriber filter regression');
  await page.screenshot({path:path.join(out,`atlas_labels_subscribers10k_dpr${dpr}.png`)});
  await page.locator('#showCommunityLabels').uncheck();
  const state=await page.evaluate(()=>atlas.state());assert(state.showCommunityLabels===false,'Label toggle not saved');
  await page.locator('#reset').click();await page.evaluate(v=>atlas.loadState(v),state);assert(!(await page.locator('#showCommunityLabels').isChecked()),'Label toggle not restored');
  const atomic=await page.evaluate(()=>{const before=JSON.stringify(atlas.state());let error=false;try{atlas.loadState({...atlas.state(),showCommunityLabels:'yes'})}catch{error=true}return error&&JSON.stringify(atlas.state())===before});assert(atomic,'Malformed view is not atomic');
  const xy=await page.evaluate(()=>Array.from(nodes.filter((_,i)=>i%14<2)));assert(JSON.stringify(before.xy)===JSON.stringify(xy),'Semantic UI moved coordinates');
  await page.locator('#reset').click();await page.setViewportSize({width:390,height:844});await page.locator('#fit').click();await page.screenshot({path:path.join(out,`atlas_labels_mobile_dpr${dpr}.png`),fullPage:true});
  assert((await page.evaluate(()=>document.documentElement.scrollWidth))===390,'Mobile overflow');
  await page.goto(pathToFileURL(path.join(out,'community_reports.html')).href);
  assert(await page.locator('article').count()===semantic.communities.length,'Report index incomplete');
  await page.locator('#search').fill('username');const visible=await page.locator('article:visible').count();assert(visible>0&&visible<semantic.communities.length,'Report search failed');
  assert(errors.length===0,'Browser errors: '+errors.join('; '));results.push({dpr,groups:before.groups,collisions,visible_search_results:visible,errors});await ctx.close();
 }
 await browser.close();fs.writeFileSync(path.join(out,'community_browser_verification.json'),JSON.stringify(results,null,2));console.log('Community-label integration passed at DPR 1 and 2.');
})().catch(e=>{console.error(e);process.exit(1)});
