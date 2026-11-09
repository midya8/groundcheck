'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),{spawn,execFileSync}=require('node:child_process'),{waitForDebugger}=require('./chrome_support.cjs');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
function compare(a,b,p='root'){assert.equal(typeof a,typeof b,p);if(typeof a==='number')assert.ok(Number.isFinite(b)&&Math.abs(a-b)<=1e-11*Math.max(1,Math.abs(a),Math.abs(b)),p);else if(a===null||typeof a!=='object')assert.equal(a,b,p);else{assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),p);for(const k of Object.keys(a))compare(a[k],b[k],p+'.'+k);}}
test('actual Chrome all evidence rows, policies and source offsets',{timeout:180000},async()=>{
 const server=require('node:http').createServer((req,res)=>{try{const file=path.join(__dirname,'../docs',req.url==='/'?'index.html':req.url);const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json'};res.setHeader('Content-Type',types[path.extname(file)]||'text/plain');res.end(fs.readFileSync(file));}catch(e){res.statusCode=404;res.end('not found');}});await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const profile=fs.mkdtempSync(path.join(os.tmpdir(),'groundcheck-audit-')),browser=spawn(process.env.CHROME_BIN||'google-chrome',['--headless','--no-sandbox','--disable-gpu','--disable-extensions','--disable-dev-shm-usage','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{stdio:['ignore','ignore','pipe']});let ws,startupError,diagnostics='';browser.on('error',e=>startupError=e);browser.stderr.on('data',d=>diagnostics=(diagnostics+d).slice(-4000));
 try{for(let i=0;i<1200&&!startupError&&browser.exitCode===null&&!fs.existsSync(path.join(profile,'DevToolsActivePort'));i++)await delay(25);assert.ok(fs.existsSync(path.join(profile,'DevToolsActivePort')),startupError?.message||diagnostics||'Chrome unavailable');const port=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0],tab=await waitForDebugger(`http://127.0.0.1:${port}/json/list`,{alive:()=>browser.exitCode===null&&!startupError});ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise((res,rej)=>{ws.onopen=res;ws.onerror=rej;});let seq=0;const pending=new Map();ws.onmessage=e=>{const m=JSON.parse(e.data);if(pending.has(m.id)){const {res,rej}=pending.get(m.id);pending.delete(m.id);m.error?rej(Error(JSON.stringify(m.error))):res(m.result);}};const call=(method,params={})=>new Promise((res,rej)=>{const id=++seq;pending.set(id,{res,rej});ws.send(JSON.stringify({id,method,params}));});const js=async expression=>{const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 await call('Page.enable');await call('Page.navigate',{url:process.env.GROUND_URL||`http://127.0.0.1:${server.address().port}/`});
 for(let i=0;i<500;i++){if(await js('Boolean(window.currentAudit)'))break;await delay(20);}assert.ok(await js('window.currentAudit'));


 const fixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'../docs/audit.json'),'utf8'));
 const set=async(id,value,event='input')=>js(`document.getElementById(${JSON.stringify(id)}).value=${JSON.stringify(String(value))};document.getElementById(${JSON.stringify(id)}).dispatchEvent(new Event(${JSON.stringify(event)}))`);
 const table=async id=>js(`Array.from(document.querySelectorAll('#'+${JSON.stringify(id)}+' tr'),tr=>Array.from(tr.cells,c=>c.textContent))`);
 let unitRows=0,sourceRows=0,numberRows=0;
 for(let i=0;i<fixtures.cases.length;i++){
  const r=fixtures.cases[i].report;
  await set('fixture',i,'change');assert.equal(await js('currentAudit'),null);assert.equal(await js('document.getElementById("results").hidden'),true);
  await js('document.getElementById("run").click()');assert.equal(await js('document.getElementById("results").hidden'),false);
  compare(await js('currentAudit'),r);
  unitRows+=r.units.length;
  const engine=await import('../docs/engine.js');
  const g=engine.audit({...r.spec,scope:'all'}),c=engine.audit({...r.spec,scope:'cited'});
  assert.deepEqual(await table('matrix'),r.units.map((u,i)=>[String(i+1),(g.units[i].support*100).toFixed(2)+'%',(c.units[i].support*100).toFixed(2)+'%',u.citations.filter(c=>c.valid).map(c=>c.marker).join(' ')||'none',String(u.tokens.length)]));
  assert.equal(await js('document.querySelectorAll(".sourcecard img").length'),0);
  for(const u of r.units){await set('inspect',u.index,'change');
   assert.equal(await js('document.getElementById("claim").textContent'),u.raw);
   assert.deepEqual(await table('scores'),u.source_scores.map(x=>[r.sources[x.source_index].id,x.eligible?'yes':'no',x.numerator+' / '+x.denominator,(x.score*100).toFixed(2)+'%',x.missing.join(', ')||'none']));sourceRows+=u.source_scores.length;
   assert.deepEqual(await js('Array.from(document.querySelectorAll(".sourcebody"),e=>e.textContent)'),r.sources.map(s=>s.text));
   assert.equal(await js('document.querySelectorAll(".number").length'),u.numbers.length);numberRows+=u.numbers.length;
  }
 }
 await set('answer','é');await js('document.getElementById("run").click()');assert.equal(await js('currentAudit'),null);assert.equal(await js('document.getElementById("download").disabled'),true);
 await set('fixture',3,'change');await js('document.getElementById("run").click()');
 await js('HTMLAnchorElement.prototype.click=function(){window.downloaded={name:this.download,url:this.href}};URL.revokeObjectURL=function(){}');await js('document.getElementById("download").click()');assert.deepEqual(await js('fetch(downloaded.url).then(r=>r.json())'),await js('currentAudit'));
 for(const width of [320,390,1280]){await call('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width<700});await js('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');assert.ok(await js('document.documentElement.scrollWidth<=innerWidth'),'overflow '+width);}
 console.log(JSON.stringify({cases:fixtures.cases.length,unitRows,sourceRows,numberRows,exports:1,widths:[320,390,1280]}));
 if(process.env.GROUND_SCREENSHOT){const width=Number(process.env.GROUND_WIDTH||1280);await call('Emulation.setDeviceMetricsOverride',{width,height:1200,deviceScaleFactor:1,mobile:width<700});await js('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');await js('document.activeElement.blur();window.scrollTo(0,0)');if(process.env.GROUND_EXPAND)await js('document.querySelectorAll("details").forEach(e=>e.open=true)');const m=await call('Page.getLayoutMetrics'),image=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height:m.cssContentSize.height,scale:1}});fs.writeFileSync(process.env.GROUND_SCREENSHOT,Buffer.from(image.data,'base64'));}
 }finally{server.close();if(ws)ws.close();if(browser.pid&&browser.exitCode===null){browser.kill('SIGTERM');await new Promise(r=>browser.once('exit',r));}await fs.promises.rm(profile,{recursive:true,force:true,maxRetries:10,retryDelay:200});}
});
