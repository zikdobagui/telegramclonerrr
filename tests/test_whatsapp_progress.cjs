const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
class Element {
 constructor(){this.hidden=false;this.disabled=false;this.children=[];this.events={};this.attrs={};this.dataset={};this.textContent='';this.classList={contains:()=>true,toggle:()=>{}};}
 addEventListener(name,fn){this.events[name]=fn;}
 setAttribute(k,v){this.attrs[k]=v;}
 removeAttribute(k){delete this.attrs[k];if(k==='src')this.src='';}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=[...nodes];}
 querySelectorAll(){return stages;}
}
const nodes=new Map(),stages=[1,2,3,4].map(n=>{const el=new Element();el.dataset.waStage=String(n);return el;});
const get=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
const requests=[],timers=new Map();let next=0;
const fetch=(url,options)=>new Promise((resolve,reject)=>{
 const row={url,options,reply:data=>resolve({ok:true,json:async()=>data})};requests.push(row);
 options.signal.addEventListener('abort',()=>{const e=new Error('aborted');e.name='AbortError';reject(e);});
});
const context={document:{getElementById:get,querySelector:()=>new Element(),querySelectorAll:()=>[],createElement:()=>new Element(),createTextNode:text=>({textContent:text})},window:{},location:{hash:''},fetch,AbortController,Date,console,encodeURIComponent,
 setTimeout:(fn,ms)=>{const id=++next;timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id),setInterval:()=>0};
vm.runInNewContext(fs.readFileSync('static/whatsapp.js','utf8'),context);
(async()=>{
 let action=get('wa-connect').events.click();
 assert.equal(get('wa-progress').hidden,false);assert.equal(get('wa-connect').textContent,'Conectando...');assert.equal(get('wa-connect').attrs['aria-busy'],'true');
 requests.at(-1).reply({success:true,connection:{status:'connecting',phase:'waiting_whatsapp',message:'Waiting',started_at:Date.now()/1000}});await action;
 let poll=get('wa-refresh-status').events.click();requests.at(-1).reply({success:true,connection:{status:'qr',phase:'awaiting_scan',message:'Ready',qr_available:true,qr_revision:'rev1'}});await poll;
 assert.equal(get('wa-qr-box').hidden,false);assert.match(get('wa-qr').src,/^\/api\/whatsapp\/qr\?v=rev1/);assert.equal(get('wa-progress').hidden,true);
 poll=get('wa-refresh-status').events.click();requests.at(-1).reply({success:true,connection:{status:'timeout',phase:'timeout',message:'Timeout',error_code:'WA_CONNECT_TIMEOUT'}});await poll;
 assert.equal(get('wa-connect').disabled,false);assert.match(get('wa-diagnostic').textContent,/WA_CONNECT_TIMEOUT/);
 // An earlier GET must not overwrite the response to a new connect operation.
 const stalePoll=get('wa-refresh-status').events.click(),stale=requests.at(-1);
 action=get('wa-connect').events.click();requests.at(-1).reply({success:true,connection:{status:'connecting',phase:'loading_library',message:'Loading'}});await action;
 stale.reply({success:true,connection:{status:'disconnected',message:'Old status'}});await stalePoll;
 assert.equal(get('wa-connect').textContent,'Conectando...');assert.equal(get('wa-progress-title').textContent,'Preparando a conexão');
 // Turn a slow HTTP connection into an actionable error rather than an endless loader.
 action=get('wa-connect').events.click();
 const timeout=[...timers.values()].filter(x=>x.ms===12000).at(-1);timeout.fn();await action;
 assert.match(get('wa-error').textContent,/12 segundos/);assert.equal(get('wa-connect').disabled,false);assert.equal(get('wa-progress').hidden,true);
 console.log('PASS: immediate loader, stages, private QR image, timeout diagnostics, stale-poll protection and HTTP abort');
})().catch(error=>{console.error(error);process.exitCode=1;});
