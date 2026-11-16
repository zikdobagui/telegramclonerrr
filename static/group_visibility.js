(() => {
 'use strict';
 const page = document.getElementById('groupVisibility');
 if (!page) return;
 const el = id => document.getElementById('gv-' + id);
 const labels = {visible:'Visíveis',hidden:'Ocultos',inaccessible:'Sem acesso',inconclusive:'Inconclusivo',invalid:'Link inválido',not_group:'Não é grupo',session_error:'Falha de sessão',error:'Erro',flood:'Espera Telegram'};
 let job = null, timer = null, polling = false, loaded = false, submitting = false;
 const active = () => job && ['running','cancelling'].includes(job.status);
 function error(message) {el('error').textContent=message || '';el('error').hidden=!message;}
 async function api(path, body) {
  const response = await fetch('/api/group-visibility' + path, {method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),cache:'no-store'});
  let result;
  try {result=await response.json();} catch (_) {throw new Error('Resposta inválida do servidor. Tente novamente.');}
  if (!response.ok || !result.success) throw new Error(result.error || 'Não foi possível concluir a solicitação.');
  return result;
 }
 function selectedCount() {el('selected-count').textContent=`${el('sessions').querySelectorAll('input:checked').length} sessões selecionadas`;}
 async function loadSessions() {
  try {
   const response=await fetch('/api/sessions',{cache:'no-store'});
   if (!response.ok) throw new Error('Não foi possível carregar suas sessões.');
   const data=await response.json();
   const selected=new Set([...el('sessions').querySelectorAll('input:checked')].map(input=>input.value));
   el('sessions').replaceChildren();
   for (const session of data.sessions || []) {
    const name=session.session_name;
    if (!name) continue;
    const disabled=session.active===false || ['flood','disconnected','invalid','corrupted','banned'].includes(session.status);
    const label=document.createElement('label');label.className='gv-session';
    const input=document.createElement('input');input.type='checkbox';input.value=name;input.dataset.available=String(!disabled);input.disabled=disabled || Boolean(active());input.checked=selected.has(name) && !disabled;
    const text=document.createElement('span');text.textContent=name;
    const status=document.createElement('small');status.textContent=disabled?'Indisponível':'Disponível';text.append(status);
    label.append(input,text);el('sessions').append(label);
   }
   if (!el('sessions').children.length) el('sessions').textContent='Nenhuma sessão cadastrada. Adicione uma sessão na aba Sessões.';
   selectedCount();
  } catch (err) {error(err.message);}
 }
 function render() {
  const rows=job?.results || [], visible=rows.filter(row=>row.status==='visible');
  const busy=Boolean(active());
  for (const control of el('form').querySelectorAll('input,textarea,button')) {
   if (control.id==='gv-cancel') continue;
   if (control.closest('.gv-session')) continue;
   control.disabled=busy;
  }
  el('sessions').querySelectorAll('input').forEach(input=>{
   if (!('available' in input.dataset)) input.dataset.available=String(!input.disabled);
   input.disabled=busy || input.dataset.available==='false';
  });
  el('cancel').hidden=!busy;el('cancel').disabled=job?.status==='cancelling';
  el('copy').disabled=!visible.length;el('export').hidden=!visible.length;
  el('status').textContent=job?`${job.message} ${job.processed}/${job.total} grupos consultados.`:'Nenhuma verificação realizada.';
  el('progress').max=job?.total || 1;el('progress').value=job?.processed || 0;
  el('summary').replaceChildren();
  const counts=[['Visíveis',visible.length],['Ocultos',rows.filter(r=>r.status==='hidden').length],['Sem acesso',rows.filter(r=>r.status==='inaccessible').length],['Outros',rows.filter(r=>!['visible','hidden','inaccessible'].includes(r.status)).length]];
  for (const [title,count] of counts) {
   const stat=document.createElement('div');stat.className='gv-stat';const number=document.createElement('strong');number.textContent=count;
   const label=document.createElement('span');label.textContent=title;stat.append(number,label);el('summary').append(stat);
  }
  el('result-note').textContent=job?`${job.valid_links} links únicos na lista; ${job.duplicates} repetidos ignorados; ${job.invalid_lines.length} linhas inválidas. O arquivo exporta somente os confirmados como visíveis, preservando as linhas originais.`:'';
  const filter=el('filter').value;
  const filtered=rows.filter(row=>filter==='all' || row.status===filter || (filter==='other' && !['visible','hidden','inaccessible'].includes(row.status)));
  el('rows').replaceChildren();
  for (const row of filtered) {
   const tr=document.createElement('tr');const group=document.createElement('td');
   const link=document.createElement('a');link.href=row.link;link.target='_blank';link.rel='noopener noreferrer';link.textContent=row.title || row.link;
   const subtitle=document.createElement('small');subtitle.textContent=row.members_count==null?row.link:`${row.members_count} membros · ${row.link}`;
   group.append(link,subtitle);
   const state=document.createElement('td');const badge=document.createElement('span');badge.className='gv-badge gv-badge--'+row.status;badge.textContent=labels[row.status] || row.status;state.append(badge);
   const session=document.createElement('td');session.textContent=row.session;
   const detail=document.createElement('td');detail.textContent=row.reason;
   tr.append(group,state,session,detail);el('rows').append(tr);
  }
  if (!filtered.length) {const tr=document.createElement('tr'),td=document.createElement('td');td.colSpan=4;td.textContent=busy?'Aguardando resultados para este filtro...':'Nenhum grupo encontrado neste filtro.';tr.append(td);el('rows').append(tr);}
 }
 async function poll() {
  if (polling) return;
  clearTimeout(timer);polling=true;
  try {job=(await api('')).job;render();}
  catch (err) {el('status').textContent='Não foi possível atualizar o progresso. Tentando novamente...';}
  finally {polling=false;if (active() || page.classList.contains('active')) timer=setTimeout(poll,2500);}
 }
 async function preview() {
  const info=await api('/preview',{groups:el('groups').value});
  el('list-info').textContent=`${info.valid_links} links únicos válidos · ${info.duplicates} repetidos · ${info.invalid_lines.length} linhas inválidas${info.invalid_lines.length?' (linhas '+info.invalid_lines.slice(0,15).join(', ')+')':''}. Até ${info.max_groups} grupos por execução.`;
  return info;
 }
 el('analyze').addEventListener('click',async()=>{error('');try {await preview();}catch(err){error(err.message);}});
 el('reload').addEventListener('click',loadSessions);
 el('sessions').addEventListener('change',selectedCount);
 el('filter').addEventListener('change',render);
 el('file').addEventListener('change',async()=>{
  const file=el('file').files[0];if (!file)return;
  try {if (file.size>1_000_000)throw new Error('O arquivo deve ter até 1 MB.');el('groups').value=await file.text();await preview();error('');}catch(err){error(err.message);}
 });
 el('form').addEventListener('submit',async event=>{
  event.preventDefault();if (active() || submitting)return;submitting=true;error('');el('start').disabled=true;
  try {
   const info=await preview();
   const limit=el('limit').value?Number(el('limit').value):Math.min(info.valid_links,500);
   const sessions=[...el('sessions').querySelectorAll('input:checked')].map(input=>input.value);
   if (!sessions.length)throw new Error('Selecione pelo menos uma sessão disponível.');
   job=(await api('/start',{groups:el('groups').value,limit,sessions})).job;render();poll();
  }catch(err){error(err.message);el('start').disabled=false;}finally{submitting=false;}
 });
 el('cancel').addEventListener('click',async()=>{try {await api('/cancel',{});await poll();}catch(err){error(err.message);}});
 el('copy').addEventListener('click',async()=>{
  try {await navigator.clipboard.writeText((job?.results || []).filter(r=>r.status==='visible').map(r=>r.link).join('\n'));el('status').textContent='Links visíveis copiados.';}catch(_){error('Não foi possível copiar. Use Baixar visíveis (.txt).');}
 });
 async function open() {if (!loaded){loaded=true;await loadSessions();}await poll();}
 document.querySelector('[data-tab="groupVisibility"]')?.addEventListener('click',event=>{if (!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey)open();});
 if (location.hash==='#groupVisibility') open();
})();
