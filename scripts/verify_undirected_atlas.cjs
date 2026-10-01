// Exercise the generated standalone atlas in a fresh headless browser profile.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const root = path.resolve(process.argv[2]);
  const expected = JSON.parse(fs.readFileSync(path.join(root, 'render_verification.json'), 'utf8'));
  const browser = await chromium.launch({
    executablePath: '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    headless: true,
  });
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  await page.goto('file://' + path.join(root, 'undirected_atlas.html'));
  await page.waitForFunction(() => ready && image.naturalWidth > 0);
  const initial = await page.evaluate(() => ({ scale, mode, nodes: atlasData.nodes.length,
    edges: atlasData.edges.length, canvasWidth: width, canvasHeight: height }));
  if (initial.mode !== 'full' || initial.nodes !== expected.main_component_communities || initial.edges !== expected.between_community_connections) {
    throw new Error('Unexpected atlas data or initial view');
  }
  await page.screenshot({ path: path.join(root, 'atlas_full_qa.png'), fullPage: true });
  await page.locator('#plus').click();
  const zoomed = await page.evaluate(() => scale);
  if (!(zoomed > initial.scale)) throw new Error('Zoom did not change the view');
  await page.locator('#fit').click();
  await page.locator('#groups').click();
  if (await page.locator('#groups').getAttribute('aria-pressed') !== 'true') {
    throw new Error('Group view did not activate');
  }
  const point = await page.evaluate(() => {
    const n = atlasData.nodes.find(n => n.rank === 1);
    const b = canvas.getBoundingClientRect();
    return { x: b.left + n.x * scale + ox, y: b.top + n.y * scale + oy, id: n.id };
  });
  await page.mouse.move(point.x, point.y);
  await page.waitForFunction(id => document.querySelector('#details h2')?.textContent === 'Group ' + id, point.id);
  await page.screenshot({ path: path.join(root, 'atlas_groups_qa.png'), fullPage: true });
  const before = await page.evaluate(() => ox);
  await page.mouse.move(500, 500);
  await page.mouse.down();
  await page.mouse.move(560, 530);
  await page.mouse.up();
  const after = await page.evaluate(() => ox);
  if (Math.abs(after - before) < 30) throw new Error('Drag did not pan the graph');
  await page.locator('#matrix').click();
  const matrix = await page.evaluate(() => ({mode, loaded: matrixImage.naturalWidth > 0}));
  if (matrix.mode !== 'matrix' || !matrix.loaded) throw new Error('Matrix view failed');
  await page.screenshot({path: path.join(root, 'atlas_matrix_qa.png'), fullPage: true});
  if (errors.length) throw new Error(errors.join('\n'));
  fs.writeFileSync(path.join(root, 'atlas_browser_verification.json'), JSON.stringify({
    ...initial, full_image_loaded: true, group_view_activated: true,
    hover_detail_verified: true, zoom_verified: true, pan_verified: true,
    matrix_view_verified: true, javascript_errors: errors,
  }, null, 2) + '\n');
  await browser.close();
  console.log('Atlas browser checks passed.');
})().catch(error => { console.error(error); process.exit(1); });
