import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {audit,canonical,format2} from '../docs/engine.js';
const data=JSON.parse(fs.readFileSync(new URL('../docs/audit.json',import.meta.url)));
let numbers=0,leaves=0;
function compare(a,b,path='') {
 if(typeof b==='number'){numbers++;assert.ok(Math.abs(a-b)<1e-12,`${path}: ${a} != ${b}`);}
 else if(Array.isArray(b)){assert.equal(a.length,b.length,path);b.forEach((v,i)=>compare(a[i],v,path+'/'+i));}
 else if(b&&typeof b==='object'){for(const k of Object.keys(b))compare(a[k],b[k],path+'/'+k);}
 else{leaves++;assert.equal(a,b,path);}
}
test('independent full evidence replay',()=>{
 for(const c of data.cases){const r=c.report;compare(audit(r.spec),r,c.title);}
 console.log(JSON.stringify({cases:data.cases.length,numbers,leaves}));
});
test('strict profile and exact decimal controls',()=> {
 for(const s of [{answer:'é',sources:[{id:'x',text:'x'}]},{answer:'[1234567]',sources:[{id:'x',text:'x'}]},{answer:'x',sources:[{id:'x',text:'x'}],threshold:NaN}])assert.throws(()=>audit(s));
 assert.notEqual(canonical('9007199254740993'),canonical('9007199254740992'));assert.equal(canonical('-0.00'),'0');
});

test('binary64 display ties are Python-compatible',()=>{
 for(const [x,out] of [[.625,'0.62'],[.645,'0.65'],[.675,'0.68'],[.615,'0.61'],[0,'0.00'],[-0,'-0.00'],[1,'1.00']])assert.equal(format2(x),out);
});
