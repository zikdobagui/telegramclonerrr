(() => {
 'use strict';
 const page=document.getElementById('whatsapp');if(!page)return;
 const el=id=>document.getElementById('wa-'+id);
 let timer=null,loading=false,groups=[],snapshot=null;
 const stateLabels={pending:'Na fila',sending:'Enviando',sent:'Confirmado',unknown:'Sem confirmação',failed:'Falhou'};
 const selected=new Map();
 async function api(path='',method='GET') {
  const response=await fetch('/api/whatsapp'+path,{method,cache:'no-store'});
  let data;try{data=await response.json();}catch(_){throw new Error('Resposta inválida do servidor.');}
  if(!response.ok||!data.success)throw new Error(data.error||'Não foi possível acessar o WhatsApp.');
  return data;
 }
 function error(node,message){node.textContent=message||'';node.hidden=!message;}
 function render() {
  if(!snapshot)return;
  el('status').textContent=snapshot.message;
  el('qr-box').hidden=!snapshot.qr;
  if(snapshot.qr)el('qr').src=snapshot.qr;else el('qr').removeAttribute('src');
  el('qr-time').textContent='O QR Code é atualizado automaticamente enquanto aguarda a leitura.';
  const busy=['connecting','qr','reconnecting','connected'].includes(snapshot.status);
  el('connect').disabled=busy||snapshot.status==='unavailable';
  el('connect').textContent=snapshot.status==='connected'?'WhatsApp conectado':'Conectar WhatsApp';
  el('disconnect').hidden=!busy;
  el('refresh-groups').disabled=snapshot.status!=='connected';
  error(el('last-error'),snapshot.last_error);
  const outbox=snapshot.outbox||{};el('counts').replaceChildren();
  for(const [state,label] of Object.entries(stateLabels)){
   const block=document.createElement('span'),number=document.createElement('b');number.textContent=outbox.counts?.[state]||0;block.append(number,document.createTextNode(label));el('counts').append(block);
  }
  el('deliveries').replaceChildren();
  for(const row of outbox.recent||[]){
   const tr=document.createElement('tr');
   for(const text of [row.clone_id,groups.find(g=>g.id===row.group_jid)?.name||row.group_jid,stateLabels[row.state]||row.state,row.detail]){const td=document.createElement('td');td.textContent=text;tr.append(td);}
   el('deliveries').append(tr);
  }
  if(!el('deliveries').children.length){const tr=document.createElement('tr'),td=document.createElement('td');td.colSpan=4;td.textContent='Nenhum envio preparado.';tr.append(td);el('deliveries').append(tr);}
 }
 async function poll(){
  if(loading)return;clearTimeout(timer);loading=true;
  try{snapshot=(await api()).connection;render();}catch(err){error(el('error'),err.message);}
  finally{loading=false;if(page.classList.contains('active'))timer=setTimeout(poll,3000);}
 }
 function renderOptions(scope){
  const container=document.getElementById(scope+'WhatsAppOptions');if(!container)return;
  const values=selected.get(scope)||new Set();container.replaceChildren();
  const items=[...groups];
  for(const id of values)if(!items.some(g=>g.id===id))items.push({id,name:id,members:null});
  for(const group of items){
   const label=document.createElement('label');label.className='wa-option';const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.value=group.id;checkbox.checked=values.has(group.id);
   checkbox.addEventListener('change',()=>{if(checkbox.checked&&values.size>=5){checkbox.checked=false;error(document.getElementById(scope+'WhatsAppError'),'Selecione no máximo 5 grupos.');return;}checkbox.checked?values.add(group.id):values.delete(group.id);selected.set(scope,values);});
   const text=document.createElement('span');text.textContent=group.name;const detail=document.createElement('small');detail.textContent=group.members==null?'Destino já configurado':`${group.members} membros${group.admin_only?' · Somente administradores podem enviar':''}`;text.append(detail);label.append(checkbox,text);container.append(label);
  }
  if(!items.length)container.textContent='Nenhum grupo carregado. Conecte sua conta na aba WhatsApp e clique em Carregar meus grupos.';
 }
 async function loadGroups(scope){
  const errorNode=scope?document.getElementById(scope+'WhatsAppError'):el('error');
  try{
   error(errorNode,'');groups=(await api('/groups')).groups;
   el('groups').replaceChildren();
   for(const group of groups){const card=document.createElement('div');card.className='wa-group';const name=document.createElement('strong'),detail=document.createElement('small');name.textContent=group.name;detail.textContent=`${group.members} membros${group.admin_only?' · Envio restrito a administradores':''}`;card.append(name,detail);el('groups').append(card);}
   if(!groups.length)el('groups').textContent='Nenhum grupo encontrado nesta conta.';
   for(const key of ['clone','editClone'])renderOptions(key);
   render();
  }catch(err){error(errorNode,err.message);}
 }
 el('connect').addEventListener('click',async()=>{el('connect').disabled=true;try{error(el('error'),'');await api('/connect','POST');await poll();}catch(err){error(el('error'),err.message);el('connect').disabled=false;}});
 el('disconnect').addEventListener('click',async()=>{el('disconnect').disabled=true;try{await api('/disconnect','POST');await poll();}catch(err){error(el('error'),err.message);}finally{el('disconnect').disabled=false;}});
 el('refresh-groups').addEventListener('click',()=>loadGroups());
 document.querySelectorAll('[data-wa-load]').forEach(button=>button.addEventListener('click',async()=>{button.disabled=true;try{await loadGroups(button.dataset.waLoad);}finally{button.disabled=false;}}));
 document.querySelector('[data-tab="whatsapp"]')?.addEventListener('click',event=>{if(!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey)poll();});
 window.WhatsAppUI={
  setDestinations(scope,values){selected.set(scope,new Set(values));renderOptions(scope);error(document.getElementById(scope+'WhatsAppError'),'');},
  getDestinations(scope){return [...(selected.get(scope)||[])];}
 };
 if(location.hash==='#whatsapp')poll();
})();
