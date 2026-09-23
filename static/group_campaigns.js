(() => {
    const el = id => document.getElementById(id);
    const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const labels = {paused:'Pausada', running:'Em execução', pending:'A criar / vincular', creating:'Criando', warming:'Aquecendo', ready:'Pronto para distribuir', error:'Precisa de revisão'};
    let version = 0;
    let snapshot = null;
    let viewInitialized = false;
    async function api(path = '', options = {}) {
        const response = await fetch('/api/group-campaigns' + path, {cache:'no-store', ...options});
        const result = await response.json();
        if (!response.ok || !result.success) throw new Error(result.error || 'Não foi possível concluir a operação');
        return result;
    }
    const json = (method, data) => ({method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    function notice(message, error = false) {
        el('campaign-status').textContent = message;
        showNotification(message, error ? 'error' : 'success');
    }
    function reveal(id) {
        const target = el(id);
        if (id === 'campaign-builder') viewInitialized = true;
        if (target.tagName === 'DETAILS') target.open = true;
        target.scrollIntoView({behavior:'smooth', block:'start'});
    }
    function preview() {
        const count = Number(el('campaign-count').value) || 0;
        const limit = Number(el('campaign-limit').value) || 0;
        const perGroup = el('campaign-limit-scope').value === 'group';
        const sessions = el('campaign-sessions').selectedOptions.length;
        el('campaign-session-count').textContent = `${sessions} selecionadas`;
        el('campaign-limit-explanation').textContent = perGroup
            ? `${count} grupos × ${limit} leads = até ${count * limit} adições por dia na tarefa. O limite de cada grupo pode ser editado depois.`
            : `Até ${limit} adições por dia, divididas entre os ${count} grupos.`;
        el('campaign-preview').textContent = `${count} grupos · ${sessions} sessões · até ${perGroup ? count * limit : limit} adições/dia · ${el('campaign-warming').value === 'yes' ? 'com aquecimento' : 'sem aquecimento'}`;
    }
    function renderSessions() {
        el('campaign-session-options').innerHTML = [...el('campaign-sessions').options].map(option => `<label class="gc-session"><input type="checkbox" value="${esc(option.value)}" ${option.selected ? 'checked' : ''} ${option.disabled ? 'disabled' : ''}><span>${esc(option.text)}</span></label>`).join('') || '<p>Nenhuma sessão cadastrada. Adicione uma conta na aba Sessões.</p>';
        preview();
    }
    async function loadSessions() {
        const response = await fetch('/api/sessions', {cache:'no-store'});
        if (!response.ok) throw new Error('Não foi possível carregar sessões');
        const data = await response.json();
        const selected = new Set(Array.from(el('campaign-sessions').selectedOptions, option => option.value));
        el('campaign-sessions').innerHTML = (data.sessions || []).map(s => {
            const unavailable = s.active === false || (s.status && s.status !== 'active');
            return `<option value="${esc(s.session_name)}" ${unavailable ? 'disabled' : ''} ${selected.has(s.session_name) && !unavailable ? 'selected' : ''}>${esc(s.first_name || s.session_name)}${unavailable ? ' — indisponível' : ''}</option>`;
        }).join('');
        renderSessions();
    }
    async function load() {
        const current = ++version;
        try {
            const data = await api();
            if (current !== version) return;
            snapshot = data;
            if (!viewInitialized) {
                el('campaign-builder').open = data.campaigns.length === 0;
                viewInitialized = true;
            }
            el('campaign-lead-total').textContent = data.total_leads.toLocaleString('pt-BR');
            el('campaign-task-total').textContent = data.campaigns.length;
            el('campaign-running-total').textContent = `${data.campaigns.filter(task => task.status === 'running').length} em execução`;
            el('campaign-added-total').textContent = data.campaigns.reduce((total, task) => total + (task.counts.added || 0), 0).toLocaleString('pt-BR');
            // Preserve forms while the user is editing a group.
            if (el('campaign-list').contains(document.activeElement) && document.activeElement.matches('input')) return;
            const openDetails = new Set([...el('campaign-list').querySelectorAll('details[open][data-detail]')].map(detail => detail.dataset.detail));
            el('campaign-list').innerHTML = data.campaigns.map(task => {
                const busy = data.worker_active || task.status === 'running';
                const counts = task.counts;
                return `<section class="gc-task">
                    <header class="gc-task-head"><div><span class="gc-task-id">TAREFA #${task.id}</span><h3>${esc(task.name)}</h3></div><div class="gc-task-actions"><span class="gc-badge ${esc(task.status)}">${esc(labels[task.status] || task.status)}</span>
                    ${task.status === 'running' ? `<button class="btn gc-secondary" data-action="pause" data-id="${task.id}">Pausar tarefa</button>` : `<button class="btn btn-primary" data-action="start" data-id="${task.id}" ${busy ? 'disabled' : ''}>Iniciar tarefa</button>`}</div></header>
                    <div class="gc-task-body">
                    <div class="gc-task-meta"><span>${task.groups.length} grupos</span><span>${task.settings.sessions.length} sessões</span><span>${task.settings.warming ? 'Com aquecimento' : 'Sem aquecimento'}</span><span>${task.settings.dedup === 'task' ? 'Um grupo por lead' : 'Uma vez por grupo'}</span></div>
                    <div class="gc-task-stats"><div><strong>${counts.added || 0}</strong><span>Adicionados</span></div><div><strong>${counts.failed || 0}</strong><span>Não adicionados</span></div><div><strong>${counts.skipped || 0}</strong><span>Duplicados ignorados</span></div><div><strong>${(counts.unknown || 0) + (counts.sending || 0)}</strong><span>Sem confirmação</span></div></div>
                    ${task.error ? `<p class="gc-alert" role="alert">${esc(task.error)}</p>` : ''}
                    ${busy ? '<p class="gc-note">Para editar ou substituir grupos, pause a tarefa e aguarde a ação atual terminar.</p>' : ''}
                    ${task.settings.limit_scope === 'task' ? `<form data-settings="${task.id}" class="gc-upload"><div class="form-group"><label>Limite diário de todos os grupos juntos<input name="daily_limit" type="number" value="${task.settings.daily_limit}" min="1" max="10000" required ${busy ? 'disabled' : ''}></label></div><button class="btn gc-secondary" ${busy ? 'disabled' : ''}>Salvar limite</button></form>` : ''}
                    <h4>Grupos da tarefa</h4>
                    ${task.groups.map(group => `<details class="gc-group" data-detail="group-${group.id}">
                        <summary><span><span class="gc-group-title">${esc(group.title)}</span><small>${group.added} adicionados · hoje: ${group.today}${task.settings.limit_scope === 'group' ? '/' + group.daily_limit : ''}</small></span><span class="gc-badge ${esc(group.status)}">${esc(labels[group.status] || group.status)}</span><i class="fas fa-chevron-down" aria-hidden="true"></i></summary>
                        <div class="gc-group-content">
                        ${group.invite && /^https:\/\/t\.me\//.test(group.invite) ? `<p><a href="${esc(group.invite)}" target="_blank" rel="noopener noreferrer">Abrir grupo no Telegram ↗</a></p>` : ''}
                        ${group.error ? `<p class="gc-alert" role="alert">${esc(group.error)}</p>` : ''}
                        ${group.status === 'warming' ? `<p>Aquecimento até ${esc(new Date(group.warm_until * 1000).toLocaleString('pt-BR'))}</p>` : ''}
                        <form data-group="${group.id}" data-task="${task.id}">
                            ${task.settings.limit_scope === 'group' ? `<div class="gc-upload"><div class="form-group"><label>Leads por dia neste grupo<input name="daily_limit" type="number" value="${group.daily_limit}" min="1" max="10000" required ${busy ? 'disabled' : ''}></label></div><button class="btn gc-secondary" name="action" value="limit" ${busy ? 'disabled' : ''}>Salvar limite</button></div>` : ''}
                            <details class="gc-replace" data-detail="replace-${group.id}"><summary>Precisa substituir este grupo?</summary><p>Use outro grupo no lugar deste. O histórico de leads e a cota do dia são mantidos.</p>
                            <div class="form-group"><label>Nome do novo grupo<input name="title" value="${esc(group.title)}" maxlength="100" ${busy ? 'disabled' : ''}></label></div>
                            <div class="form-group"><label>Link de um grupo existente (opcional)<input name="reference" placeholder="https://t.me/+..." ${busy ? 'disabled' : ''}></label><small>Deixe vazio para criar um novo grupo quando iniciar a tarefa.</small></div>
                            <button class="btn gc-secondary" name="action" value="replace" ${busy ? 'disabled' : ''}>Substituir grupo</button><small>O grupo anterior permanece no Telegram.</small></details>
                        </form></div>
                    </details>`).join('')}
                    <details class="gc-history" data-detail="events-${task.id}"><summary>Ver histórico e informações de execução</summary><p>Sem confirmação: o lead fica reservado para evitar repetição. As cotas renovam à meia-noite de São Paulo. Após reiniciar o servidor, use Iniciar tarefa para retomar.</p>${task.events.map(event => `<p>${esc(new Date(event.created * 1000).toLocaleString('pt-BR'))} — ${esc(event.message)}</p>`).join('') || '<p>Aguardando início.</p>'}</details>
                    </div>
                </section>`;
            }).join('') || '<div class="gc-empty"><i class="fas fa-layer-group" aria-hidden="true"></i><h3>Sua primeira tarefa começa aqui</h3><p>Escolha os grupos e as sessões. Depois de salvar, ela aparecerá neste espaço.</p><button class="btn btn-primary" type="button" data-reveal="campaign-builder">Criar minha primeira tarefa</button></div>';
            el('campaign-list').querySelectorAll('details[data-detail]').forEach(detail => detail.open = openDetails.has(detail.dataset.detail));
        } catch (error) {
            el('campaign-status').textContent = error.message;
        }
    }
    async function submit(form, work) {
        const buttons = [...form.querySelectorAll('button')];
        buttons.forEach(button => button.disabled = true);
        try { await work(); } catch (error) { notice(error.message, true); }
        finally { buttons.forEach(button => button.disabled = false); }
    }
    document.addEventListener('DOMContentLoaded', () => {
        el('comingSoon').addEventListener('click', event => {
            const button = event.target.closest('[data-reveal]');
            if (button) reveal(button.dataset.reveal);
        });
        el('campaign-new').addEventListener('click', () => reveal('campaign-builder'));
        el('campaign-create-form').addEventListener('input', preview);
        el('campaign-create-form').addEventListener('change', preview);
        el('campaign-session-options').addEventListener('change', event => {
            const option = [...el('campaign-sessions').options].find(option => option.value === event.target.value);
            if (option) option.selected = event.target.checked;
            preview();
        });
        preview();
        el('campaign-warming').addEventListener('change', () => {
            el('campaign-warm-fields').hidden = el('campaign-warming').value !== 'yes';
        });
        el('campaign-sessions').addEventListener('change', () => {
            el('campaign-session-count').textContent = `${el('campaign-sessions').selectedOptions.length} selecionadas`;
        });
        el('campaign-phrases-file').addEventListener('change', async event => {
            const file = event.target.files[0];
            if (!file) return;
            if (file.size > 1024 * 1024) return notice('O arquivo de frases deve ter até 1 MB', true);
            el('campaign-phrases').value = await file.text();
        });
        el('campaign-create-form').addEventListener('submit', event => {
            event.preventDefault();
            submit(event.currentTarget, async () => {
                if (!el('campaign-sessions').selectedOptions.length) {
                    el('campaign-session-options').scrollIntoView({behavior:'smooth', block:'center'});
                    throw new Error('Marque pelo menos uma sessão na etapa 02.');
                }
                const payload = {
                    name:el('campaign-name').value, count:el('campaign-count').value, daily_limit:el('campaign-limit').value,
                    sessions:Array.from(el('campaign-sessions').selectedOptions, option => option.value),
                    warming:el('campaign-warming').value === 'yes', messages:el('campaign-phrases').value,
                    warm_days:el('campaign-warm-days').value, warm_interval:el('campaign-warm-interval').value,
                    delay:el('campaign-delay').value, dedup:el('campaign-dedup').value, limit_scope:el('campaign-limit-scope').value,
                };
                const result = await api('', json('POST', payload));
                notice(`Tarefa #${result.id} salva. Clique em Iniciar para executar.`);
                await load();
                el('campaign-builder').open = false;
                reveal('campaign-monitor');
            });
        });
        el('campaign-leads-form').addEventListener('submit', event => {
            event.preventDefault();
            submit(event.currentTarget, async () => {
                const data = new FormData();
                data.append('file', el('campaign-leads-file').files[0]);
                const result = await api('/leads', {method:'POST', body:data});
                el('campaign-import-result').textContent = `${result.added} novos · ${result.duplicates} duplicados · ${result.invalid} inválidos`;
                notice('Importação concluída');
                await load();
            });
        });
        el('campaign-list').addEventListener('click', async event => {
            const button = event.target.closest('button[data-action]');
            if (!button) return;
            button.disabled = true;
            try {
                await api(`/${button.dataset.id}/${button.dataset.action}`, {method:'POST'});
                notice(button.dataset.action === 'pause' ? 'Pausa solicitada. Aguardando a ação atual terminar.' : 'Tarefa iniciada');
                await load();
            } catch (error) { notice(error.message, true); button.disabled = false; }
        });
        el('campaign-list').addEventListener('submit', event => {
            event.preventDefault();
            const form = event.target;
            const replace = event.submitter?.value === 'replace';
            const data = Object.fromEntries(new FormData(form));
            const taskId = form.dataset.task || form.dataset.settings;
            submit(form, async () => {
                const task = snapshot.campaigns.find(task => task.id === Number(taskId));
                if (replace) {
                    data.replace = true;
                    data.daily_limit ??= task.groups.find(group => group.id === Number(form.dataset.group)).daily_limit;
                }
                const path = form.dataset.group ? `/${taskId}/groups/${form.dataset.group}` : `/${taskId}/settings`;
                await api(path, json('PUT', data));
                notice(replace ? 'Grupo substituído. Clique em Iniciar para continuar o ciclo.' : 'Limite atualizado');
                document.activeElement?.blur();
                await load();
            });
        });
        el('campaign-refresh').addEventListener('click', () => { load(); loadSessions().catch(error => notice(error.message, true)); });
        document.querySelector('[data-tab="comingSoon"]').addEventListener('click', () => { load(); loadSessions().catch(error => notice(error.message, true)); });
        setInterval(() => { if (el('comingSoon').classList.contains('active')) load(); }, 10000);
    });
})();
