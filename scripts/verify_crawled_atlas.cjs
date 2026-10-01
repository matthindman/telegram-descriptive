/* Browser integration and pixel measurements. Outputs only under the supplied root. */
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
const root=path.resolve(process.argv[2]),out=path.join(root,'visualization');
const expected=JSON.parse(fs.readFileSync(path.join(root,'graph_manifest.json'))),layout=JSON.parse(fs.readFileSync(path.join(root,'layout/layout_manifest.json')));
function assert(x,message){if(!x)throw Error(message)}
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',args:['--enable-unsafe-swiftshader']});
 const results={};const overlapChecks=JSON.parse(fs.readFileSync(path.join(root,'revision/overlap_verification.json')));
 for(const dpr of [1,2]){
  const context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:dpr,acceptDownloads:true});const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const url=pathToFileURL(path.join(out,'crawled_channels_atlas.html')).href;
  await page.goto(url);await page.waitForFunction(()=>window.atlas?.metrics.ready,{timeout:60000});await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  const metrics=await page.evaluate(()=>atlas.metrics);assert(metrics.N===expected.nodes&&metrics.E===expected.undirected_edges&&metrics.glError===0,'Initial graph/GPU');
  await page.screenshot({path:path.join(out,`atlas_overview_dpr${dpr}.png`),fullPage:true});
  const positionBefore=await page.evaluate(()=>[atlas.nval(0,0),atlas.nval(0,1),atlas.nval(1000,0)]);
  for(const row of overlapChecks.threshold_counts){await page.locator('#subscriberInput').fill(String(row.minimum_subscribers));await page.locator('#coreInput').fill(String(row.minimum_core));const actual=await page.evaluate(()=>atlas.metrics);assert(actual.visibleCount===row.nodes&&actual.visibleEdges===row.edges,'Subscriber/core intersection: '+JSON.stringify(row));}
  await page.locator('#subscriberInput').fill(String(expected.max_subscribers));await page.locator('#coreInput').fill(String(layout.max_core));await page.locator('#fit').click();assert((await page.evaluate(()=>atlas.metrics.visibleCount))===0,'Empty combined filter');
  await page.locator('#reset').click();await page.locator('#subs10k').click();await page.locator('#fit').click();const subscriber10k=await page.evaluate(()=>atlas.metrics);await page.screenshot({path:path.join(out,`atlas_subscribers10k_dpr${dpr}.png`),fullPage:true});
  await page.locator('#minSubscribers').fill('500');const slider=await page.evaluate(()=>({actual:atlas.state().subscribersMin,expected:Math.round(Math.expm1(.5*Math.log1p(atlas.data.graph.max_subscribers)))}));assert(slider.actual===slider.expected,'Log subscriber slider');
  const positionAfter=await page.evaluate(()=>[atlas.nval(0,0),atlas.nval(0,1),atlas.nval(1000,0)]);assert(JSON.stringify(positionBefore)===JSON.stringify(positionAfter),'Filters moved positions');
  const guard=await page.evaluate(()=>{const old=camera.scale;const rows=[];for(const zoom of [.25,1,8,100])for(const size of [.2,1,8]){camera.scale=baseScale*zoom;sizeMul=size;const a=labels.findIndex((_,i)=>nval(i,2)===1000),b=labels.findIndex((_,i)=>nval(i,2)===100000);rows.push({zoom,size,guard:effectiveReferenceDiameter()<=8*Math.sqrt(D.style.subscriber_reference/100000)*camera.scale+1e-8,ratio:a<0||b<0?true:Math.abs(diameter(a)/diameter(b)-.1)<1e-8})}camera.scale=old;sizeMul=1;return rows});assert(guard.every(r=>r.guard&&r.ratio),'Overlap guard and subscriber ratio');
  await page.locator('#reset').click();await page.locator('#subscriberInput').fill('1000000');
  await page.locator('#search').fill('@fragment_monitor');await page.locator('#searchForm button').click();assert((await page.locator('#details').innerText()).includes('176,254'),'Resolved denominator');assert((await page.evaluate(()=>atlas.state().subscribersMin))===0,'Search reveals hidden low-subscriber channel');
  await page.locator('#focusOnly').check();const focused=await page.evaluate(()=>atlas.metrics);assert(focused.visibleCount<expected.nodes,'Focus');
  await page.screenshot({path:path.join(out,`atlas_neighborhood_dpr${dpr}.png`),fullPage:true});
  await page.locator('#reset').click();await page.locator('#core10').click();const kc=layout.coreness_checks.find(x=>x.k===10);const core=await page.evaluate(()=>atlas.metrics);assert(core.visibleCount===kc.nodes&&core.visibleEdges===kc.edges,'Exact 10-core');
  await page.locator('#colorMode').selectOption('core');await page.locator('#fit').click();await page.screenshot({path:path.join(out,`atlas_core10_dpr${dpr}.png`),fullPage:true});
  await page.locator('#reset').click();await page.locator('#scope').selectOption('4');const sans=await page.evaluate(()=>atlas.metrics);assert(sans.visibleCount===layout.dense_block.excluding_block_nodes&&sans.visibleEdges===layout.dense_block.excluding_block_edges,'Block exclusion');
  await page.locator('#scope').selectOption('5');const block=await page.evaluate(()=>atlas.metrics);assert(block.visibleCount===layout.dense_block.nodes&&block.visibleEdges===layout.dense_block.internal_edges,'Block-only');
  await page.screenshot({path:path.join(out,`atlas_dense_block_dpr${dpr}.png`),fullPage:true});
  await page.locator('#reset').click();await page.locator('#resolution').selectOption('2');await page.locator('#weightMode').selectOption('all');assert((await page.evaluate(()=>atlas.state().resolution))==='1','All-target gamma label');assert(await page.locator('#resolution').isDisabled(),'All-target partition fixed gamma');
  const weights=await page.evaluate(()=>({weight:edges[2],expected:weightsAll[0],position:atlas.nval(0,0)}));assert(weights.weight===weights.expected,'Sensitivity weight');
  const alias=await page.evaluate(()=>{const i=D.aliases.findIndex(a=>a.length>1);return {handle:D.aliases[i].find(x=>x!==labels[i]),id:i}});await page.locator('#search').fill(alias.handle);await page.locator('#searchForm button').click();assert((await page.evaluate(()=>atlas.metrics.selected))===alias.id,'Alias search');
  await page.locator('#subscriberInput').fill('12345');await page.locator('#avoidOverlap').uncheck();await page.locator('#edgeOpacity').fill('0');await page.locator('#nodeSize').fill('1.5');const downloadPromise=page.waitForEvent('download');await page.locator('#saveView').click();const dl=await downloadPromise;const saved=path.join(out,`qa_view_dpr${dpr}.json`);await dl.saveAs(saved);
  const view=JSON.parse(fs.readFileSync(saved));await page.locator('#reset').click();await page.locator('#viewFile').setInputFiles(saved);await page.waitForFunction(()=>atlas.state().edgeMul===0);assert((await page.evaluate(()=>atlas.state().sizeMul))===1.5,'Saved view');assert((await page.evaluate(()=>atlas.state().subscribersMin))===12345&&!(await page.evaluate(()=>atlas.state().avoidOverlap)),'Subscriber/overlap saved view');
  const robust=await page.evaluate(()=>{let v=atlas.state();delete v.edgeMul;atlas.loadState(v);const defaultEdge=atlas.state().edgeMul;const before=JSON.stringify(atlas.state());let scopeError=false,cameraError=false;try{atlas.loadState({...v,scope:7})}catch{scopeError=true}try{atlas.loadState({...v,camera:{...v.camera,x:NaN}})}catch{cameraError=true}return {defaultEdge,scopeError,cameraError,atomic:before===JSON.stringify(atlas.state())}});assert(robust.defaultEdge===1&&robust.scopeError&&robust.cameraError&&robust.atomic,'Malformed view handling');
  const malformed=await page.evaluate(()=>{const state=atlas.state();let errors=0;for(const bad of [{subscribersMin:-1},{subscribersMin:NaN},{avoidOverlap:'yes'},{layout_sha256:'wrong'}])try{atlas.loadState({...state,...bad})}catch{errors++}return errors});assert(malformed===4,'Invalid new saved-view fields');
  const zoomBefore=await page.evaluate(()=>atlas.state().camera.zoom);await page.setViewportSize({width:1100,height:850});await page.waitForTimeout(200);assert(Math.abs((await page.evaluate(()=>atlas.state().camera.zoom))-zoomBefore)<1e-7,'Relative zoom on resize');
  await page.locator('#reset').click();await page.locator('#scope').selectOption('3');assert((await page.evaluate(()=>atlas.metrics.visibleCount))===expected.isolates,'Isolates');
  await page.locator('#reset').click();await page.setViewportSize({width:390,height:844});await page.locator('#fit').click();await page.screenshot({path:path.join(out,`atlas_mobile_dpr${dpr}.png`),fullPage:true});assert((await page.evaluate(()=>document.documentElement.scrollWidth))===390,'Mobile overflow');
  await page.setViewportSize({width:1440,height:1000});await page.reload();await page.waitForFunction(()=>window.atlas?.metrics.ready);
  const gpuFilter=await page.evaluate(()=>{
   selected=-1;focus=false;coreMin=scope=0;subscribersMin=100000;
   const bytes=()=>{const a=new Uint8Array(canvas.width*canvas.height*4);gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,a);return a};
   paintEdges(E);const edgeFiltered=bytes();const ee=[];for(let i=0;i<E;i++)if(nval(edges[i*4],2)>=100000&&nval(edges[i*4+1],2)>=100000)ee.push(...edges.subarray(i*4,i*4+4));
   subscribersMin=0;gl.bindBuffer(gl.ARRAY_BUFFER,edgeBuffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,new Float32Array(ee));paintEdges(ee.length/4);const edgeCPU=bytes();let edgeDiff=0;for(let i=0;i<edgeCPU.length;i++)if(edgeCPU[i]!==edgeFiltered[i])edgeDiff++;
   gl.bindBuffer(gl.ARRAY_BUFFER,edgeBuffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,edges);
   subscribersMin=100000;paintEdges(0);paintNodes();const nodeFiltered=bytes();const nn=[];for(let j=0;j<N;j++)if(nodeData[j*10+2]>=100000)nn.push(...nodeData.subarray(j*10,j*10+10));
   subscribersMin=0;gl.bindBuffer(gl.ARRAY_BUFFER,nodeBuffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,new Float32Array(nn));paintEdges(0);paintNodes(nn.length/10);const nodeCPU=bytes();let nodeDiff=0;for(let i=0;i<nodeCPU.length;i++)if(nodeCPU[i]!==nodeFiltered[i])nodeDiff++;
   updateNodes();requestDraw();return {edge_pixel_differences:edgeDiff,node_pixel_differences:nodeDiff,filtered_edges:ee.length/4,filtered_nodes:nn.length/10};
  });assert(gpuFilter.edge_pixel_differences===0&&gpuFilter.node_pixel_differences===0,'GPU subscriber filtering differs from independently subsetted draw');
  const pixels=await page.evaluate(async()=>{
   ready=false;await new Promise(r=>requestAnimationFrame(r));
   camera={x:0,y:0,scale:1};baseScale=1;coreMin=scope=0;selected=-1;focus=false;sizeMul=1;
   gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,canvas.width,canvas.height);
   const readSize=256,buf=new Uint8Array(readSize*readSize*4);let seed=42;const rnd=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296};
   const nodeRows=[];
   for(const productionColor of [false,true])for(const subscribers of [1,10,79,387,1000,6250,25000,100000,1000000,11919181]){
    let ratios=[],visible=0;const intended=Math.PI*(D.style.reference_diameter_css_px*Math.sqrt(subscribers/D.style.subscriber_reference)*dpr/2)**2;
    for(let phase=0;phase<32;phase++){
     const bg=productionColor?colorRGB(D.style.background):[0,0,0],fg=productionColor?colorRGB(D.style.monochrome):[1,1,1];gl.clearColor(...bg,1);gl.clear(gl.COLOR_BUFFER_BIT);
     const cx=canvas.width/2+rnd(),cy=canvas.height/2+rnd();
     gl.bindBuffer(gl.ARRAY_BUFFER,nodeBuffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,new Float32Array([(cx/dpr-W/2),-(cy/dpr-H/2),subscribers,...fg,0,0,1,0]));paintNodes(1);
     gl.readPixels(Math.floor(canvas.width/2)-128,Math.floor(canvas.height/2)-128,readSize,readSize,gl.RGBA,gl.UNSIGNED_BYTE,buf);
     let ink=0;const contrast=fg.map((x,j)=>Math.round(x*255)-Math.round(bg[j]*255)),norm=contrast.reduce((a,b)=>a+b*b,0);for(let k=0;k<buf.length;k+=4)for(let j=0;j<3;j++)ink+=(buf[k+j]-Math.round(bg[j]*255))*contrast[j]/norm;ratios.push(ink/intended);if(ink>0)visible++;
    }
    nodeRows.push({productionColor,subscribers,mean_ink_to_intended:ratios.reduce((a,b)=>a+b)/ratios.length,min_ratio:Math.min(...ratios),max_ratio:Math.max(...ratios),visible_phases:visible,phases:32});
   }
   // Actual line programs, physical readback, random angles/phases, no nodes.
   const oldTexture=nodeTexture;nodeTexture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,nodeTexture);const nt=new Float32Array(512*4);
   edgeMul=1;const edgeRows=[];
   for(const [name,w,multiplicity] of [['weak',D.legend_weights[0],1],['median',D.legend_weights[1],1],['strong',D.legend_weights[2],1],['median_10',D.legend_weights[1],10],['median_1000',D.legend_weights[1],1000],['weak_1000',D.legend_weights[0],1000]]){
    let traced=0,maxima=[],sums=[];
    for(let phase=0;phase<16;phase++){
     const angle=rnd()*Math.PI,dx=Math.cos(angle)*50,dy=Math.sin(angle)*50,x=rnd(),y=rnd();nt.set([x-dx,y-dy,0,0,x+dx,y+dy,0,0]);gl.bindTexture(gl.TEXTURE_2D,nodeTexture);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA32F,512,1,0,gl.RGBA,gl.FLOAT,nt);textureParams();
     const ee=new Float32Array(multiplicity*4);for(let k=0;k<multiplicity;k++)ee.set([0,1,w,1],k*4);gl.bindBuffer(gl.ARRAY_BUFFER,edgeBuffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,ee);paintEdges(multiplicity);
     gl.readPixels(Math.floor(canvas.width/2)-128,Math.floor(canvas.height/2)-128,readSize,readSize,gl.RGBA,gl.UNSIGNED_BYTE,buf);let sum=0,max=0;const bg=Math.round(colorRGB(D.style.background)[0]*255);for(let k=0;k<buf.length;k+=4){const delta=buf[k]-bg;sum+=delta;max=Math.max(max,delta)}if(max>0)traced++;maxima.push(max);sums.push(sum);
    }
    edgeRows.push({name,weight:w,multiplicity,traced_phases:traced,phases:16,mean_peak:maxima.reduce((a,b)=>a+b)/16,mean_summed_change:sums.reduce((a,b)=>a+b)/16});
   }
   const gpu={renderer:gl.getParameter(gl.RENDERER),vendor:gl.getParameter(gl.VENDOR),error:gl.getError()};return {nodeRows,edgeRows,gpu};
  });
  fs.writeFileSync(path.join(out,`pixel_measurements_dpr${dpr}.json`),JSON.stringify(pixels,null,2));
  for(const row of pixels.nodeRows)if(row.subscribers>=79)assert(Math.abs(row.mean_ink_to_intended-1)<.05,'Pixel area mismatch: '+JSON.stringify(row));
  for(const row of pixels.edgeRows)assert(row.traced_phases===row.phases,'Invisible edge: '+JSON.stringify(row));
  assert(pixels.edgeRows[4].mean_peak>pixels.edgeRows[1].mean_peak*3,'Median overlap fails to accumulate');assert(pixels.edgeRows[5].mean_peak>pixels.edgeRows[0].mean_peak*3,'Weak overlap fails to accumulate');
  assert(pixels.gpu.error===0&&errors.length===0,'GPU or JS errors: '+errors);
  results['dpr'+dpr]={metrics,focused,core,block,sans,robust,subscriber10k,guard,gpuFilter,pixels,errors};await context.close();
 }
 fs.writeFileSync(path.join(out,'browser_verification.json'),JSON.stringify(results,null,2));await browser.close();console.log('Integration and pixel checks passed at DPR 1 and 2');
})().catch(e=>{console.error(e);process.exit(1)});
