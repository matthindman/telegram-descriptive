/* v9 tie layer: ink proportional to weight, fixed calibration, highlight layer, linked communities.
   Usage: NODE_PATH=<playwright node_modules> node scripts/verify_tie_layer.cjs <atlas root>
   Writes visualization/tie_layer_verification.json and tie_*.png under <root>.
   Ink checks read the actual RGBA32F tie buffer and compare its integral with sums
   computed independently in JavaScript from the edge list (no shader code reused). */
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
const root=path.resolve(process.argv[2]),out=path.join(root,'visualization');
const assert=(x,m)=>{if(!x)throw Error(m)};
const helpers=`
window.__readTies=()=>{paintEdges(E);gl.bindFramebuffer(gl.FRAMEBUFFER,densityFBO);const a=new Float32Array(densityW*densityH*4);gl.readPixels(0,0,densityW,densityH,gl.RGBA,gl.FLOAT,a);gl.bindFramebuffer(gl.FRAMEBUFFER,null);return a};
window.__sums=a=>{let r=0,g=0,rn=0,gn=0;for(let k=0;k<a.length;k+=4){r+=a[k];g+=a[k+1];if(a[k]>0)rn++;if(a[k+1]>0)gn++}return {r,g,rn,gn}};
// Independent expected integral: density x width(device px) x length(device px), for ties fully on screen.
window.__expected=(pred)=>{let r=0,g=0,inside=true;const st=D.style,chosen=referencePartition()&&chosenCommunity!==null?chosenCommunity:-1,ctx=selected>=0?st.edge_context_dim_selection:chosen>=0?st.edge_context_dim_community:1;
 for(let j=0;j<E;j++){const u=edges[j*4],v=edges[j*4+1],w=edges[j*4+2];if(!(nval(u,2)>=subscribersMin&&nval(v,2)>=subscribersMin&&nval(u,7)>=coreMin&&nval(v,7)>=coreMin))continue;
  const [ax,ay]=screen(u),[bx,by]=screen(v);if(Math.min(ax,bx)<0||Math.max(ax,bx)>W||Math.min(ay,by)<0||Math.max(ay,by)>H)inside=false;
  const lpx=Math.hypot(bx-ax,by-ay)*dpr,lw=Math.max(Math.hypot(nval(u,0)-nval(v,0),nval(u,1)-nval(v,1)),st.edge_ink_min_length_world),t=Math.min(1,Math.max(0,(Math.log(w)-st.log_weight_min)/(st.log_weight_max-st.log_weight_min)));
  const hit=pred(u,v);if(hit)g+=edgeMul*w/Math.pow(lw,st.edge_highlight_length_exponent)*(st.edge_width_min_css_px+(st.edge_width_max_css_px-st.edge_width_min_css_px)*t)*dpr*lpx;else r+=edgeMul*w/lw*ctx*st.edge_base_width_css_px*dpr*lpx}
 return {r,g,allInside:inside}};
`;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',args:['--enable-unsafe-swiftshader']});
 const results=[];
 for(const spec of [{width:1500,height:1000,dpr:1},{width:1200,height:800,dpr:1},{width:390,height:844,dpr:2}]){
  const context=await browser.newContext({viewport:{width:spec.width,height:spec.height},deviceScaleFactor:spec.dpr}),page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
  await page.goto(pathToFileURL(path.join(out,'crawled_channels_atlas.html')).href);await page.waitForFunction(()=>window.atlas?.metrics.ready,{},{timeout:120000});await page.evaluate(helpers);
  const tag=`${spec.width}_dpr${spec.dpr}`,R={viewport:spec};
  // 1. Ink is proportional to weight and independent of a tie's length (synthetic ties, real pipeline).
  R.ink_law=await page.evaluate(()=>{const saved={W,H,dpr,camera,selected,scope,coreMin,focus,nodeTexture,subscribersMin,chosenCommunity};W=1024;H=96;dpr=1;camera={x:0,y:0,scale:1};selected=-1;scope=coreMin=subscribersMin=0;focus=false;chosenCommunity=null;
   const cases=[[.1,100],[.1,400],[.2,100],[.01,250],[.5,600]],nt=new Float32Array(512*4),ee=[];cases.forEach(([w,L],i)=>{const y=-40+i*20;nt.set([-L/2,y,0,0,L/2,y,0,0],i*8);ee.push(i*2,i*2+1,w,1)});
   nodeTexture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,nodeTexture);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA32F,512,1,0,gl.RGBA,gl.FLOAT,nt);textureParams();gl.bindBuffer(gl.ARRAY_BUFFER,edgeBuffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,new Float32Array(ee));
   paintEdges(cases.length,1024,96,1);gl.bindFramebuffer(gl.FRAMEBUFFER,densityFBO);const a=new Float32Array(1024*96*4);gl.readPixels(0,0,1024,96,gl.RGBA,gl.FLOAT,a);gl.bindFramebuffer(gl.FRAMEBUFFER,null);
   const band=new Array(cases.length).fill(0);for(let y=0;y<96;y++)for(let x=0;x<1024;x++){const yc=48-(y+.5);const i=Math.round((yc+40)/20);if(i>=0&&i<cases.length)band[i]+=a[(y*1024+x)*4]}
   gl.deleteTexture(nodeTexture);({W,H,dpr,camera,selected,scope,coreMin,focus,nodeTexture,subscribersMin,chosenCommunity}=saved);gl.bindBuffer(gl.ARRAY_BUFFER,edgeBuffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,edges);requestDraw();
   const perWeight=band.map((b,i)=>b/cases[i][0]);return {cases,integrals:band,inkPerUnitWeight:perWeight,maxRelSpread:(Math.max(...perWeight)-Math.min(...perWeight))/Math.min(...perWeight)}});
  assert(R.ink_law.maxRelSpread<.03,'Tie ink not proportional to weight: '+JSON.stringify(R.ink_law));
  // 2. Overview: real buffer integral equals the independent sum; brightness rarely near the cap.
  await page.evaluate(()=>{reset();draw()});
  R.overview=await page.evaluate(()=>{const a=__readTies(),s=__sums(a),e=__expected(()=>false),c=tieCalibration,cap=D.style.edge_tone_cap;let near=0;for(let k=0;k<a.length;k+=4)if(a[k]>0&&cap*Math.min(1,Math.log1p(a[k]/c.d0)/Math.log1p(c.d1/c.d0))>.95*cap)near++;
   return {baseIntegral:s.r,expectedBase:e.r,relError:Math.abs(s.r-e.r)/e.r,highlightIntegral:s.g,tiePixels:s.rn,nearCapShare:near/s.rn,allTiesOnScreen:e.allInside,calibration:c}});
  assert(R.overview.relError<.03&&R.overview.highlightIntegral===0&&R.overview.nearCapShare<.03,'Overview tie ink/calibration: '+JSON.stringify(R.overview));
  // 3. Calibration is fixed during pan, zoom, filters and highlighting; it changes only on material resize.
  R.calibration_stability=await page.evaluate(()=>{const c0=JSON.stringify([tieCalibration.d0,tieCalibration.d1]);const res={};
   camera.x+=200/camera.scale;camera.scale*=3;draw();res.panZoom=JSON.stringify([tieCalibration.d0,tieCalibration.d1])===c0;
   setSubscribers(10000);draw();res.filter=JSON.stringify([tieCalibration.d0,tieCalibration.d1])===c0;
   chooseCommunity([...semanticById.values()].find(x=>x.rank_subscribers===1).community);draw();res.highlight=JSON.stringify([tieCalibration.d0,tieCalibration.d1])===c0;
   const h0=JSON.stringify([highlightCalibration.h0,highlightCalibration.h1]);camera.scale*=2;draw();res.highlightFixedOnZoom=JSON.stringify([highlightCalibration.h0,highlightCalibration.h1])===h0;
   reset();draw();return res});
  assert(Object.values(R.calibration_stability).every(Boolean),'Calibration moved during navigation: '+JSON.stringify(R.calibration_stability));
  // 4. Highlights: community external ties, one pair, and a selected channel (independent sums).
  R.highlight=await page.evaluate(()=>{const res={},cid=[...semanticById.values()].find(x=>x.rank_subscribers===1).community,comm=i=>Math.round(nval(i,8));
   chooseCommunity(cid);draw();let a=__readTies(),s=__sums(a),e=__expected((u,v)=>(comm(u)===cid)!==(comm(v)===cid));res.community={g:s.g,expected:e.g,relError:Math.abs(s.g-e.g)/e.g,baseRelError:Math.abs(s.r-e.r)/e.r,calibration:{h0:highlightCalibration.h0,h1:highlightCalibration.h1}};
   const top=communityPartners(cid).rows.slice().sort((x,y)=>y.weight-x.weight)[0].community;setPartner(top);draw();a=__readTies();s=__sums(a);e=__expected((u,v)=>((comm(u)===cid)!==(comm(v)===cid))&&(comm(u)===top||comm(v)===top));res.pair={partner:top,g:s.g,expected:e.g,relError:Math.abs(s.g-e.g)/e.g,endpointsBrightened:partnerEndpoints.size};
   chooseCommunity(null);const id=labels.indexOf('rian_ru');setSelection(id);draw();a=__readTies();s=__sums(a);e=__expected((u,v)=>u===id||v===id);res.channel={g:s.g,expected:e.g,relError:Math.abs(s.g-e.g)/e.g,baseRelError:Math.abs(s.r-e.r)/e.r};
   setSelection(-1);reset();draw();return res});
  for(const k of ['community','pair','channel'])assert(R.highlight[k].relError<.03,'Highlight ink mismatch '+k+': '+JSON.stringify(R.highlight[k]));
  assert(R.highlight.community.baseRelError<.03&&R.highlight.channel.baseRelError<.03,'Context dimming mismatch');
  // 5. Linked-communities numbers reconcile independently; direction split sums to the pair weight.
  R.partners=await page.evaluate(()=>{const cid=[...semanticById.values()].find(x=>x.rank_subscribers===2).community,{rows,external}=communityPartners(cid);let ext=0,X=new Map(),X2=0;
   for(let j=0;j<E;j++){const a=Math.round(nval(edges[j*4],8)),b=Math.round(nval(edges[j*4+1],8)),w=weightsValid[j];if(a===b)continue;X.set(a,(X.get(a)||0)+w);X.set(b,(X.get(b)||0)+w);X2+=2*w;if((a===cid)!==(b===cid))ext+=w}
   const top=rows.slice().sort((x,y)=>y.weight-x.weight)[0],aff=top.weight*X2/(X.get(cid)*X.get(top.community));
   return {rows:rows.length,sumRows:rows.reduce((t,r)=>t+r.weight,0),external,independentExternal:ext,maxDirectionRelErr:Math.max(...rows.map(r=>Math.abs(r.out+r.in-r.weight)/r.weight)),topAffinity:top.affinity,independentTopAffinity:aff}});
  assert(Math.abs(R.partners.sumRows-R.partners.independentExternal)/R.partners.independentExternal<1e-9&&R.partners.maxDirectionRelErr<1e-5&&Math.abs(R.partners.topAffinity-R.partners.independentTopAffinity)/R.partners.independentTopAffinity<1e-9,'Partner panel numbers: '+JSON.stringify(R.partners));
  // 6. Real controls: rank button -> panel; partner row -> pair focus; show-all; sort; saved view; atomic rejection.
  await page.evaluate(()=>{reset();draw()});await page.locator('#communityRanking button').nth(0).click();
  await page.locator('.partnerList [data-partner]').first().click();
  R.ui={pairSelected:await page.evaluate(()=>chosenPartner!==null&&document.querySelector('.partnerList [aria-pressed="true"]')!==null)};
  const saved=await page.evaluate(()=>state());R.ui.savedHasPartner=saved.chosenPartner!==null;
  await page.locator('#partnerAll').click();R.ui.showAllClears=await page.evaluate(()=>chosenPartner===null);
  await page.locator('[data-psort="affinity"]').click();R.ui.affinityRows=await page.locator('.partnerList [data-partner]').count();
  await page.evaluate(v=>{reset();loadState(v);draw()},saved);R.ui.restored=await page.evaluate(p=>chosenPartner===p&&partnerEndpoints.size>0,saved.chosenPartner);
  R.ui.atomic=await page.evaluate(()=>{const before=JSON.stringify(state());let err=false;try{loadState({...state(),chosenPartner:chosenCommunity})}catch{err=true}return err&&JSON.stringify(state())===before});
  assert(Object.values(R.ui).every(x=>x===true||(typeof x==='number'&&x>0)),'Tie/partner UI: '+JSON.stringify(R.ui));
  // Screenshots.
  await page.evaluate(()=>{reset();draw()});await page.screenshot({path:path.join(out,`tie_overview_${tag}.png`).replace(/\\/g,'/'),fullPage:spec.width<640});
  await page.evaluate(()=>{chooseCommunity([...semanticById.values()].find(x=>x.rank_subscribers===1).community);draw()});await page.screenshot({path:path.join(out,`tie_community_${tag}.png`),fullPage:spec.width<640});
  await page.evaluate(()=>{const cid=chosenCommunity;setPartner(communityPartners(cid).rows.slice().sort((x,y)=>y.weight-x.weight)[0].community);draw()});await page.screenshot({path:path.join(out,`tie_pair_${tag}.png`),fullPage:spec.width<640});
  await page.evaluate(()=>{reset();setSelection(labels.indexOf('rian_ru'));camera.scale=baseScale;draw()});await page.screenshot({path:path.join(out,`tie_channel_${tag}.png`),fullPage:spec.width<640});
  await page.evaluate(()=>{reset();draw()});
  assert(errors.length===0,'Browser errors: '+errors.join('; '));R.errors=errors;results.push(R);await context.close();
  console.log(tag,'ok',JSON.stringify({nearCap:+R.overview.nearCapShare.toFixed(4),inkSpread:+R.ink_law.maxRelSpread.toFixed(4),community:+R.highlight.community.relError.toFixed(4),pair:+R.highlight.pair.relError.toFixed(4)}));
 }
 await browser.close();fs.writeFileSync(path.join(out,'tie_layer_verification.json'),JSON.stringify(results,null,2)+'\n');
 console.log('Ink proportional to weight, overview/highlight ink integrals, fixed calibration, linked-community numbers and UI checks passed.');
})().catch(e=>{console.error(e);process.exit(1)});
