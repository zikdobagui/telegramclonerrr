(() => {
 'use strict';
 const page=document.getElementById('whatsapp');if(!page)return;
 const el=id=>document.getElementById('wa-'+id);
 let disconnecting=false;
 let timer=null,pollPromise=null,groups=[],snapshot=null,requesting=false,requestStarted=0,operation=0,qrRevision=null,qrAttempts=0;
 const stateLabels={pending:'Na fila',sending:'Enviando',sent:'Confirmado',unknown:'Sem confirmação',failed:'Falhou'};
 const selected=new Map();
 async function api(path='',method='GET') {
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),12000);
  try {
  const response=await fetch('/api/whatsapp'+path,{method,cache:'no-store',signal:controller.signal});
  let data;try{data=await response.json();}catch(_){throw new Error('Resposta inválida do servidor.');}
  if(!response.ok||!data.success)throw new Error(data.error||'Não foi possível acessar o WhatsApp.');
  return data;
  } catch(err) {
   if(err.name==='AbortError')throw new Error('O servidor não respondeu em 12 segundos. A tentativa pode continuar no servidor; use Atualizar estado para conferir.');
   throw err;
  } finally {clearTimeout(timeout);}
 }
 function error(node,message){node.textContent=message||'';node.hidden=!message;}
 function render() {
  if(!snapshot)return;
  const status=disconnecting?'disconnecting':requesting?'requesting':snapshot.status;
  const phase=requesting?'preparing':snapshot.phase;
  el('status').textContent=requesting?'Solicitando uma conexão ao servidor...':snapshot.message;
  const hasQR=!requesting&&!disconnecting&&status!=='disconnecting'&&Boolean(snapshot.qr_available||snapshot.qr);
  el('qr-box').hidden=!hasQR;
  if(hasQR){
   const revision=snapshot.qr_revision||snapshot.qr_expires_at||snapshot.qr;
   if(qrRevision!==revision){qrRevision=revision;el('qr').src='/api/whatsapp/qr?v='+encodeURIComponent(String(snapshot.qr_revision||snapshot.qr_expires_at||'current'))+'&attempt='+(qrAttempts++);}
  }else{qrRevision=null;el('qr').removeAttribute('src');}
  el('qr-time').textContent='Leia este código no celular. Se expirar, o próximo será exibido automaticamente.';
  const waiting=requesting||['connecting','reconnecting'].includes(status)||(status==='qr'&&!hasQR);
  const busy=requesting||disconnecting||status==='disconnecting'||['connecting','qr','reconnecting','connected'].includes(status);
  el('connect').disabled=busy||snapshot.status==='unavailable';
  el('connect').setAttribute('aria-busy',String(waiting));
  el('connect').textContent=status==='disconnecting'?'Removendo sessão...':status==='connected'?'WhatsApp conectado':waiting?'Conectando...':status==='qr'?'Aguardando leitura do QR':['error','timeout','disconnected','logged_out','replaced'].includes(status)?'Conectar novamente':'Conectar WhatsApp';
  el('progress').hidden=!waiting;
  const phaseText={preparing:['Iniciando conexão','Enviando sua solicitação ao servidor.'],loading_library:['Preparando a conexão','Carregando a biblioteca de WhatsApp.'],opening_session:['Abrindo seu aparelho','Verificando o pareamento salvo no servidor.'],waiting_whatsapp:['Aguardando o WhatsApp','O QR Code aparecerá aqui assim que chegar.'],reconnecting:['Reconectando','Tentando reutilizar o aparelho já vinculado.']};
  const progress=phaseText[phase]||['Atualizando QR Code','Aguardando um novo código válido do WhatsApp.'];
  el('progress-title').textContent=progress[0];el('progress-detail').textContent=progress[1];
  el('connect-stages').hidden=!busy;
  const step=status==='connected'?4:hasQR?3:phase==='waiting_whatsapp'||status==='reconnecting'||status==='qr'?2:1;
  page.querySelectorAll('[data-wa-stage]').forEach(item=>{const number=Number(item.dataset.waStage);item.classList.toggle('is-done',number<step||status==='connected');item.classList.toggle('is-active',number===step&&status!=='connected');});
  const diagnostic=snapshot.error_code?`Diagnóstico: ${snapshot.error_code}. ${snapshot.message}`:'';
  error(el('diagnostic'),diagnostic);
  el('disconnect').hidden=!busy;el('disconnect').disabled=disconnecting||status==='disconnecting';
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
 function poll(){
  if(pollPromise)return pollPromise;
  clearTimeout(timer);const version=operation;
  pollPromise=(async()=>{
   try{const data=await api();if(version===operation&&!requesting&&!disconnecting){snapshot=data.connection;render();error(el('error'),'');}}
   catch(err){
    if(version===operation&&!requesting&&!disconnecting&&snapshot&&['connecting','reconnecting','qr'].includes(snapshot.status)){
     snapshot={...snapshot,status:'error',phase:'error',error_code:'WA_STATUS_UNAVAILABLE',message:'Não foi possível acompanhar a conexão. A tentativa pode continuar no servidor; atualize o estado.',qr:null,qr_available:false};render();
    }
    error(el('error'),err.message);
   }
   finally{pollPromise=null;if(page.classList.contains('active'))timer=setTimeout(poll,2000);}
  })();
  return pollPromise;
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
 el('connect').addEventListener('click',async()=>{
  if(requesting||disconnecting||snapshot?.status==='disconnecting')return;const version=++operation;clearTimeout(timer);requesting=true;requestStarted=Date.now();snapshot=snapshot||{};render();error(el('error'),'');
  try{const data=await api('/connect','POST');if(version!==operation)return;requesting=false;snapshot=data.connection||{status:'connecting',phase:'waiting_whatsapp',message:'Aguardando o WhatsApp...',started_at:requestStarted/1000};render();}
  catch(err){if(version!==operation)return;requesting=false;snapshot={...snapshot,status:'error',phase:'error',message:err.message,qr:null,qr_available:false};render();error(el('error'),err.message);}
  finally{if(version===operation)timer=setTimeout(poll,500);}
 });
 el('disconnect').addEventListener('click',async()=>{
  if(disconnecting)return;
  const version=++operation;clearTimeout(timer);requesting=false;disconnecting=true;
  snapshot={...snapshot,status:'disconnecting',phase:'disconnecting',message:'Removendo a sessão anterior do WhatsApp...',qr:null,qr_available:false};
  render();error(el('error'),'');
  try{const data=await api('/disconnect','POST');if(version!==operation)return;if(data.connection)snapshot=data.connection;
   groups=[];el('groups').replaceChildren();for(const key of ['clone','editClone'])renderOptions(key);
  }catch(err){error(el('error'),err.message);}
  finally{disconnecting=false;render();timer=setTimeout(poll,500);}
 });
 el('refresh-groups').addEventListener('click',()=>loadGroups());
 el('refresh-status').addEventListener('click',poll);
 el('qr').addEventListener('error',()=>{qrRevision=null;error(el('error'),'O QR chegou, mas a imagem não carregou. Tentando obter uma nova imagem...');});
 setInterval(()=>{if(!el('progress').hidden){const started=requesting?requestStarted:(snapshot?.started_at||Date.now()/1000)*1000;el('progress-elapsed').textContent=`${Math.max(0,Math.floor((Date.now()-started)/1000))} s decorridos · atualização automática`; }},1000);
 document.querySelectorAll('[data-wa-load]').forEach(button=>button.addEventListener('click',async()=>{button.disabled=true;try{await loadGroups(button.dataset.waLoad);}finally{button.disabled=false;}}));
 document.querySelector('[data-tab="whatsapp"]')?.addEventListener('click',event=>{if(!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey)poll();});
 window.WhatsAppUI={
  setDestinations(scope,values){selected.set(scope,new Set(values));renderOptions(scope);error(document.getElementById(scope+'WhatsAppError'),'');},
  getDestinations(scope){return [...(selected.get(scope)||[])];}
 };
 if(location.hash==='#whatsapp')poll();
})();
