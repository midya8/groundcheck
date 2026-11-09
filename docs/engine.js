// Independent scalar ASCII evidence engine. No Python report drives these calculations.
export const STOPWORDS = new Set(('a an and are as at be but by for from has have he her his i in is it its of on or she so that the their they this to was we were which will with you').split(' '));
const cite = /\[(\d+)\]/g;
const unique = a => [...new Set(a)];
export function tokens(text) {
 return [...text.toLowerCase().matchAll(/[a-z0-9']+/g)].filter(m=>!STOPWORDS.has(m[0])).map(m=>({token:m[0],start:m.index,end:m.index+m[0].length}));
}
export function numbers(text) {
 return [...text.matchAll(/(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?!\w|\.\d)/g)].map(m=>({literal:m[0],number:m[0].replaceAll(',',''),start:m.index,end:m.index+m[0].length}));
}
export function canonical(s) {
 let sign=''; if(s.startsWith('-')) {sign='-';s=s.slice(1);}
 let [whole,fraction='']=s.split('.');whole=whole.replace(/^0+/,'')||'0';fraction=fraction.replace(/0+$/,'');
 return (whole==='0'&&!fraction?'':sign)+whole+(fraction?'.'+fraction:'');
}
const same = (a,b)=>canonical(a)===canonical(b);
export function units(text) {
 const masked=text.replace(/(?<=\d)\.(?=\d)/g,'\x00');
 return [...masked.matchAll(/[^.!?\n]+[.!?]+(?:["')\]]+)?|[^.!?\n]+$/gm)].map(m=> {
 const lo=m.index+(m[0].length-m[0].trimStart().length),hi=m.index+m[0].trimEnd().length;
 return {lo,hi,raw:text.slice(lo,hi)};
 }).filter(u=>u.raw);
}
export function validate(input) {
 if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).some(k=>!['answer','sources','threshold','scope'].includes(k)))throw Error('Unknown spec fields');
 const spec={answer:input.answer,sources:input.sources,threshold:Object.hasOwn(input,'threshold')?input.threshold:.6,scope:Object.hasOwn(input,'scope')?input.scope:'all'};
 if(typeof spec.threshold!=='number'||!Number.isFinite(spec.threshold)||spec.threshold<0||spec.threshold>1)throw Error('Finite threshold in [0,1] required');
 if(!['all','cited'].includes(spec.scope)||!Array.isArray(spec.sources)||spec.sources.length<1||spec.sources.length>8)throw Error('Scope all/cited and 1..8 sources required');
 const ids=[];const texts=[spec.answer];
 for(const s of spec.sources) {
 if(!s||typeof s!=='object'||Array.isArray(s)||Object.keys(s).sort().join(',')!=='id,text'||typeof s.id!=='string'||!s.id.length||s.id.length>64||/[^\x00-\x7f]/.test(s.id))throw Error('Sources need ASCII id and text');
 ids.push(s.id);texts.push(s.text);
 }
 if(unique(ids).length!==ids.length)throw Error('Duplicate source id');
 for(const t of texts)if(typeof t!=='string'||t.length>4096||/[^\x00-\x7f]|[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(t))throw Error('Audit needs ASCII text <=4096 chars, no control characters');
 if([...spec.answer.matchAll(cite)].some(m=>m[1].length>6))throw Error('Citation positions limited to six digits');
 if(units(spec.answer).length>64||texts.reduce((n,t)=>n+numbers(t).length,0)>128)throw Error('Audit bounds: 64 units / 128 numeric occurrences');
 return spec;
}
export function audit(input) {
 const spec=validate(input),{answer,sources,threshold,scope}=spec;
 const sourceRows=sources.map((s,index)=>({index,...s,tokens:tokens(s.text),numbers:numbers(s.text)}));
 const result=[],findings=[];
 for(const {lo,hi,raw} of units(answer)) {
 const claim=raw.replace(cite,''),plain=raw.replace(cite,m=>' '.repeat(m.length));
 const words=unique(tokens(plain).map(t=>t.token)).sort();
 const citations=[...raw.matchAll(cite)].map(m=>({marker:m[0],position:Number(m[1]),start:lo+m.index,end:lo+m.index+m[0].length,valid:Number(m[1])>=1&&Number(m[1])<=sources.length}));
 const eligible=scope==='all'?sources.map((s,i)=>i):unique(citations.filter(c=>c.valid).map(c=>c.position-1)).sort((a,b)=>a-b);
 const rows=sourceRows.map(s=> {
 const available=new Set(s.tokens.map(t=>t.token)),matched=words.filter(t=>available.has(t));
 return {source_index:s.index,eligible:eligible.includes(s.index),matched,missing:words.filter(t=>!available.has(t)),numerator:matched.length,denominator:words.length,score:words.length?matched.length/words.length:1};
 });
 let best=null;for(const r of rows)if(r.eligible&&(!best||r.score>best.score))best=r;
 const score=best?best.score:0,supported=score>=threshold;
 const nums=numbers(plain).map(n=> {
 const matches=sourceRows.flatMap(s=>s.numbers.filter(o=>same(n.number,o.number)).map(o=>({source_index:s.index,...o,eligible:eligible.includes(s.index)})));
 return {...n,start:n.start+lo,end:n.end+lo,matches,present:matches.some(m=>m.eligible)};
 });
 const unit={index:result.length,start:lo,end:hi,raw,claim,tokens:words,token_occurrences:tokens(plain).map(t=>({...t,start:lo+t.start,end:lo+t.end})),citations,eligible_sources:eligible,source_scores:rows,best_source:best?best.source_index:null,support:score,supported,no_content:!words.length,numbers:nums};result.push(unit);
 if(scope==='cited'&&!eligible.length)findings.push({kind:'no_resolved_citation',unit:unit.index});
 if(!supported)findings.push({kind:'lexical_below_threshold',unit:unit.index});
 for(const c of citations)if(!c.valid)findings.push({kind:'citation_unresolvable',unit:unit.index,marker:c.marker});
 for(const n of nums)if(!n.present)findings.push({kind:'number_absent_in_scope',unit:unit.index,number:n.number,start:n.start});
 }
 return {schema:'groundcheck.evidence.v1',spec,sources:sourceRows,units:result,findings,mean_support:result.length?result.reduce((n,u)=>n+u.support,0)/result.length:1,legacy_all_source_report:legacyCheck(answer,sources,threshold)};
}
// Historical all-source check protocol, independently reconstructed in JavaScript.
// It strips answer citations before splitting, unlike provenance-unit segmentation.
export function legacyCheck(answer,sources,threshold=.6) {
 const findings=[],citations=unique([...answer.matchAll(cite)].map(m=>m[1]));let cited=new Set();
 for(const num of citations){const pos=Number(num);if(pos>=1&&pos<=sources.length)cited.add(pos-1);else findings.push({kind:'citation_unresolvable',severity:'high',detail:`citation [${num}] has no matching source (${sources.length} provided)`});}
 const truncate=text=>{const t=text.trim().replace(/\s+/g,' ');return t.length<=100?t:t.slice(0,99)+'…';};
 const sentences=[];let unsupported=0;
 for(const {raw:sent} of units(answer.replace(cite,''))){
  const words=new Set(tokens(sent).map(t=>t.token));let score=words.size?0:1,index=-1,excerpt='';
  if(words.size)for(let i=0;i<sources.length;i++){
   const available=new Set(tokens(sources[i].text).map(t=>t.token));if(!available.size)continue;
   const current=[...words].filter(t=>available.has(t)).length/words.size;
   if(current>score){score=current;index=i;let best=-1;for(const {raw} of units(sources[i].text)){
    const present=new Set(tokens(raw).map(t=>t.token)),count=[...words].filter(t=>present.has(t)).length;if(count>best){best=count;excerpt=raw;}
   }}
  }
  const supported=score>=threshold;
  if(!supported){unsupported++;findings.push({kind:'unsupported_sentence',severity:'medium',detail:`sentence support ${format2(score)} below ${format2(threshold)}: ${truncate(sent)}`,sentence:sent,support:score});}
  sentences.push({sentence:sent,support:score,supported,source:index>=0?sources[index].id:null,source_excerpt:excerpt?truncate(excerpt):null});
 }
 const sourceNumbers=sources.flatMap(s=>numbers(s.text).map(n=>n.number));
 for(const s of sentences)for(const n of numbers(s.sentence))if(!sourceNumbers.some(other=>same(n.number,other)))findings.push({kind:'number_not_in_sources',severity:'high',detail:`number ${n.number} in answer appears in no source: ${truncate(s.sentence)}`,sentence:s.sentence,number:n.number});
 return {answer_sentences:sentences.length,unsupported_sentences:unsupported,mean_support:sentences.length?sentences.reduce((sum,s)=>sum+s.support,0)/sentences.length:1,support_threshold:threshold,citations,sources_cited:cited.size,sources_provided:sources.length,sentences,findings,finding_count:findings.length};
}

// Match Python's binary64 fixed-two display using exact integer rounding, ties to even.
export function format2(value) {
 const data=new DataView(new ArrayBuffer(8));data.setFloat64(0,value);const bits=data.getBigUint64(0);
 const exponent=Number((bits>>52n)&2047n)-1023-52;let n=(bits&((1n<<52n)-1n))+(value===0?0n:1n<<52n);n*=100n;
 let d=1n;if(exponent>=0)n<<=BigInt(exponent);else d<<=BigInt(-exponent);
 let q=n/d,r=n%d;if(2n*r>d||(2n*r===d&&q%2n))q++;return (bits>>63n?'-':'')+(q/100n).toString()+'.'+(q%100n).toString().padStart(2,'0');
}
