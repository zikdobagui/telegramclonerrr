(() => {
    const el = id => document.getElementById(id);
    const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const labels = {paused:'Pausada', running:'Em execução', pending:'A criar / vincular', creating:'Criando', warming:'Aquecendo', ready:'Pronto para distribuir', error:'Precisa de revisão'};
    let editingId = null;
    let selectedImages = [];
    let selectedGroupImage = '';
    let selectedDescriptions = [];
    let version = 0;
    let snapshot = null;
    let viewInitialized = false;
    let groupActionSubmitting = false;
    let logStream = null;
    let streamState = 'connecting';
    const liveEvents = new Map();
    const logFilters = new Map();
    function rememberEvents(id, events) {
        const merged = new Map((liveEvents.get(id) || []).map(event => [event.id, event]));
        for (const event of events) merged.set(event.id, event);
        liveEvents.set(id, [...merged.values()].sort((a, b) => b.id - a.id).slice(0, 500));
    }
    function updateLogs(id) {
        const history = el('campaign-list').querySelector(`[data-detail="events-${id}"]`);
        if (!history) return;
        const list = history.querySelector('.gc-live-content');
        const scroll = list.querySelector('.gc-log-list')?.scrollTop || 0;
        list.innerHTML = renderHistory(liveEvents.get(id) || [], logFilters.get(id));
        const next = list.querySelector('.gc-log-list');
        if (next) next.scrollTop = scroll;
        history.querySelector('.gc-log-count').textContent = (liveEvents.get(id) || []).length;
    }
    function updateStreamState(state) {
        streamState = state;
        document.querySelectorAll('.gc-live-state').forEach(node => {
            node.dataset.state = state;
            node.textContent = state === 'live' ? 'Ao vivo' : state === 'connecting' ? 'Conectando…' : 'Reconectando…';
        });
    }
    function startLogStream() {
        if (logStream) return;
        logStream = new EventSource('/api/group-campaigns/events/stream');
        logStream.onopen = () => updateStreamState('live');
        logStream.onerror = () => updateStreamState('reconnecting');
        logStream.onmessage = message => {
            const rows = JSON.parse(message.data);
            const ids = new Set(rows.map(row => row.campaign_id));
            for (const id of ids) {
                rememberEvents(id, rows.filter(row => row.campaign_id === id));
                updateLogs(id);
            }
        };
    }

    const percent = (value, total) => total > 0 ? Math.min(100, Math.max(0, Math.round(value / total * 100))) : 0;
    function progress(value, total, label) {
        const pct = percent(value, total);
        return `<div class="gc-progress"><div class="gc-progress-label"><span>${esc(label)}</span><strong>${pct}%</strong></div><progress max="${Math.max(1, total)}" value="${Math.min(value, total)}" aria-label="${esc(label)}"></progress><small>${value.toLocaleString('pt-BR')} de ${total.toLocaleString('pt-BR')} adições confirmadas neste ciclo de 24h</small></div>`;
    }

    function groupShareLink(group) {
        if (!group.channel_id) return '';
        const link = group.invite || group.reference || '';
        if (/^https:\/\/t\.me\/[\w+/-]+$/.test(link)) return link;
        if (/^t\.me\/[\w+/-]+$/.test(link)) return 'https://' + link;
        if (/^@[\w]+$/.test(link)) return 'https://t.me/' + link.slice(1);
        return '';
    }

    async function copyGroupList(task) {
        const groups = task.groups.filter(group => groupShareLink(group));
        if (!groups.length) throw new Error('Esta tarefa ainda não tem grupos com links disponíveis.');
        const text = groups.map(group => `${group.title}\n${groupShareLink(group)}`).join('\n\n');
        let copied = false;
        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(text);
                copied = true;
            }
        } catch (_) { /* Try the fallback for browsers without clipboard permission. */ }
        if (!copied) {
            const input = document.createElement('textarea');
            input.value = text;
            input.style.position = 'fixed';
            input.style.opacity = '0';
            document.body.appendChild(input);
            input.select();
            try { copied = document.execCommand('copy'); } catch (_) { /* Manual copy below. */ }
            finally { input.remove(); }
        }
        if (!copied) {
            window.prompt('Copie a lista de nomes e links abaixo:', text);
            return;
        }
        const missing = task.groups.length - groups.length;
        notice(`${groups.length} grupo(s) copiado(s) com nome e link.${missing ? ` ${missing} grupo(s) sem link disponível ficaram de fora.` : ''}`);
    }

    function deletionControls(task, group, busy) {
        if (!group.channel_id || !group.access_hash || !group.creator) return '';
        return `<details class="gc-ownership gc-delete-group" data-detail="delete-${group.id}">
            <summary>Excluir grupo do painel e do Telegram</summary>
            <p>Apaga permanentemente este grupo no Telegram para todos os participantes e o remove da lista. A ação não pode ser desfeita. O histórico de leads é preservado e nenhum grupo substituto será criado.</p>
            <p>A tarefa deve estar pausada e a sessão criadora precisa continuar sendo dona do grupo.</p>
            ${group.deletion_status === 'unknown' ? '<p class="gc-alert">A tentativa anterior não foi confirmada. Confira o grupo no Telegram antes de tentar novamente. Falta de acesso não significa que ele foi excluído.</p>' : ''}
            <form data-delete-group="${group.id}" data-task="${task.id}"><button type="submit" class="btn btn-danger" ${busy ? 'disabled' : ''}>Excluir permanentemente do Telegram e do painel</button></form>
        </details>`;
    }

    function ownershipControls(task, group, busy) {
        if (!group.channel_id || !group.access_hash || !group.creator) return '';
        const transfer = group.ownership;
        const blocked = transfer && transfer.status !== 'failed';
        const username = transfer?.username || (task.settings.admin_usernames || [])[0] || '';
        return `<details class="gc-ownership" data-detail="owner-${group.id}">
            <summary>Transferir posse do grupo <span class="gc-badge">Beta — em testes</span></summary>
            <p>Este recurso está em beta. A sessão criadora (${esc(group.creator)}) passará a posse para o usuário informado. Depois da transferência, só o novo dono poderá devolver a posse. As permissões das sessões ficam sob controle dele.</p>
            ${transfer ? `<p role="status">${transfer.status === 'confirmed' ? 'Posse transferida' : transfer.status === 'failed' ? 'Transferência não realizada' : 'Resultado ainda não confirmado'}: @${esc(transfer.username)}</p>` : ''}
            ${blocked ? (transfer.status === 'confirmed' ? '' : `<form data-owner="${group.id}" data-task="${task.id}" data-owner-check="true"><button class="btn btn-primary" ${busy ? 'disabled' : ''}>Consultar resultado no Telegram</button><small>A consulta não repete a transferência.</small></form>`) : `
            <form data-owner="${group.id}" data-task="${task.id}" autocomplete="off">
                <p>Pause a tarefa e adicione o destinatário como administrador do grupo antes de transferir. O Telegram exige verificação em duas etapas e pode impor prazos de espera para senha ou sessão recente.</p>
                <div class="form-group"><label>Novo dono (@username)<input name="username" value="${esc(username)}" placeholder="@usuario" required maxlength="33" ${busy ? 'disabled' : ''}></label></div>
                <div class="form-group"><label>Senha de verificação em duas etapas da conta criadora<input name="password" type="password" autocomplete="new-password" required ${busy ? 'disabled' : ''}></label><small>Use a senha do Telegram da sessão criadora. A senha não será salva.</small></div>
                <label class="gc-owner-confirm"><input name="confirmed" type="checkbox" required ${busy ? 'disabled' : ''}>Confirmo que quero passar a posse deste grupo ao usuário acima.</label>
                <button class="btn btn-warning" ${busy ? 'disabled' : ''}>Transferir posse — Beta</button>
            </form>`}
        </details>`;
    }
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
    function eventTone(message) {
        const text = String(message || '').toLocaleLowerCase('pt-BR');
        if (/não confirmado|não adicionado|não foi possível|erro|rejeitad|spam|flood|indisponível|falha|inválid|desativad/.test(text)) return 'warning';
        if (/aguardando|meta diária|intervalo|espera|pendente/.test(text)) return 'waiting';
        if (/adicionado|sucesso|iniciado|confirmad/.test(text)) return 'success';
        return 'info';
    }
    function renderHistory(events, filter = {}) {
        const tones = {success:'Sucesso', warning:'Atenção', waiting:'Espera', info:'Etapa'};
        const query = String(filter.query || '').toLocaleLowerCase('pt-BR');
        const shown = events.filter(event => (!filter.tone || eventTone(event.message) === filter.tone) && String(event.message).toLocaleLowerCase('pt-BR').includes(query));
        if (!shown.length) return '<p class="gc-log-empty">Nenhum evento para exibir. Novas etapas aparecem automaticamente.</p>';
        return `<div class="gc-log-list" role="log" aria-label="Eventos da tarefa">${shown.map(event => `<article class="gc-log ${eventTone(event.message)}"><time datetime="${esc(new Date(event.created * 1000).toISOString())}">${esc(new Date(event.created * 1000).toLocaleString('pt-BR'))}</time><span class="gc-log-level">${tones[eventTone(event.message)]}</span><p>${esc(event.message)}</p></article>`).join('')}</div>`;
    }
    function reveal(id) {
        const target = el(id);
        if (id === 'campaign-builder') viewInitialized = true;
        if (target.tagName === 'DETAILS') target.open = true;
        target.scrollIntoView({behavior:'smooth', block:'start'});
    }
    function customGroupNames() {
        return el('campaign-names').value.split(/\r?\n/).map(name => name.trim()).filter(Boolean);
    }
    function preview() {
        if (editingId === null) {
            const names = customGroupNames();
            el('campaign-count').disabled = names.length > 0;
            if (names.length) el('campaign-count').value = names.length;
        }
        const count = Number(el('campaign-count').value) || 0;
        const limit = Number(el('campaign-limit').value) || 0;
        const perGroup = el('campaign-limit-scope').value === 'group';
        const sessions = el('campaign-sessions').selectedOptions.length;
        el('campaign-session-count').textContent = `${sessions} selecionadas`;
        el('campaign-limit-explanation').textContent = perGroup
            ? `Meta de ${limit} leads por grupo: o Grupo 1 recebe até ${limit} primeiro; só então o sistema passa ao Grupo 2. Total máximo em 24h: ${count * limit}.`
            : `Até ${limit} adições a cada 24h, divididas entre os ${count} grupos.`;
        el('campaign-preview').textContent = `${count} grupos · ${sessions} sessões · até ${perGroup ? count * limit : limit} adições/24h · ${el('campaign-warming').value === 'yes' ? 'com aquecimento' : 'sem aquecimento'}`;
    }
    function renderSessions() {
        const query = String(el('campaign-session-search')?.value || '').trim().toLocaleLowerCase('pt-BR');
        const available = [...el('campaign-sessions').options].filter(option => !option.disabled);
        const shown = available.filter(option => !query || `${option.dataset.name} ${option.dataset.phone} ${option.value}`.toLocaleLowerCase('pt-BR').includes(query));
        el('campaign-session-available').textContent = `${shown.length} de ${available.length} disponíveis`;
        el('campaign-session-options').innerHTML = shown.map(option => `<label class="gc-session"><input type="checkbox" value="${esc(option.value)}" ${option.selected ? 'checked' : ''}><span class="gc-session-identity"><strong>${esc(option.dataset.name)}</strong><small>${esc(option.dataset.phone)}</small></span><span class="gc-session-state">Disponível</span></label>`).join('') || `<p>${query ? 'Nenhuma sessão disponível encontrada.' : 'Nenhuma sessão disponível no momento.'}</p>`;
        preview();
    }
    async function loadSessions() {
        // The session picker must remain usable even if the optional task-lock
        // endpoint is temporarily unavailable.
        const response = await fetch('/api/sessions', {cache:'no-store'});
        if (!response.ok) throw new Error('Não foi possível carregar sessões');
        const data = await response.json();
        let taskData = {};
        try {
            const tasksResponse = await fetch('/api/tasks/blocked-sessions', {cache:'no-store'});
            if (tasksResponse.ok) taskData = await tasksResponse.json();
        } catch (_) {
            // Continue with the active sessions; this list is refreshed when
            // the task-lock endpoint becomes available again.
        }
        const occupied = new Set(taskData.reserved_sessions || taskData.blocked_sessions || []);
        for (const task of snapshot?.campaigns || []) {
            if (task.status === 'running' && task.id !== editingId) {
                for (const name of task.settings.sessions || []) occupied.add(name);
            }
        }
        const selected = new Set(Array.from(el('campaign-sessions').selectedOptions, option => option.value));
        el('campaign-sessions').innerHTML = (data.sessions || []).map((s, index) => {
            const unavailable = s.active === false || (s.status && s.status !== 'active') || occupied.has(index) || occupied.has(s.session_name);
            const name = [s.first_name, s.last_name].filter(Boolean).join(' ').trim() || s.name || s.username || s.session_name || 'Sem nome';
            const phone = s.phone ? String(s.phone) : 'Telefone não informado';
            return `<option data-name="${esc(name)}" data-phone="${esc(phone)}" value="${esc(s.session_name)}" ${unavailable ? 'disabled' : ''} ${selected.has(s.session_name) && !unavailable ? 'selected' : ''}>${esc(name)} · ${esc(phone)}${unavailable ? ' — indisponível' : ''}</option>`;
        }).join('');
        renderSessions();
    }
    function resetEditor() {
        editingId = null;
        selectedImages = [];
        selectedGroupImage = '';
        selectedDescriptions = [];
        el('campaign-images-status').textContent = '';
        el('campaign-group-image-status').textContent = '';
        el('campaign-descriptions-status').textContent = '';
        el('campaign-create-form').reset();
        el('campaign-count').disabled = false;
        el('campaign-names').disabled = false;
        el('campaign-names-file').disabled = false;
        el('campaign-dedup').disabled = false;
        el('campaign-editor-title').textContent = 'Criar uma tarefa';
        el('campaign-save-button').textContent = 'Salvar tarefa';
        el('campaign-cancel-edit').hidden = true;
        el('campaign-edit-note').hidden = true;
        el('campaign-warm-fields').hidden = true;
        for (const option of el('campaign-sessions').options) option.selected = false;
        renderSessions();
    }
    async function editTask(task) {
        await loadSessions();
        editingId = task.id;
        el('campaign-names').value = task.groups.map(group => group.title).join('\n');
        el('campaign-names').disabled = true;
        el('campaign-names-file').disabled = true;
        const settings = task.settings;
        selectedImages = [...(settings.images || [])];
        selectedGroupImage = settings.group_image || '';
        selectedDescriptions = [...(settings.descriptions || [])];
        el('campaign-images').value = '';
        el('campaign-images-status').textContent = `${selectedImages.length} imagens salvas`;
        el('campaign-group-image').value = '';
        el('campaign-group-image-status').textContent = selectedGroupImage ? 'Imagem dos grupos salva' : '';
        el('campaign-descriptions-file').value = '';
        el('campaign-descriptions-status').textContent = selectedDescriptions.length ? `${selectedDescriptions.length} descrições salvas` : '';
        const fields = {name:task.name, count:task.groups.length, limit:settings.daily_limit,
            parallel:'yes', 'limit-scope':settings.limit_scope, dedup:settings.dedup, 'delay-min':settings.delay_min ?? settings.delay ?? 60, 'delay-max':settings.delay_max ?? settings.delay ?? 60,
            admin:(settings.admin_usernames || [settings.admin_username].filter(Boolean)).join('\n'),
            warming:settings.warming ? 'yes' : 'no', phrases:settings.messages.join('\n'),
            'warm-days':settings.warm_days, 'warm-interval':settings.warm_interval};
        for (const [field, value] of Object.entries(fields)) el('campaign-' + field).value = value;
        for (const option of el('campaign-sessions').options) option.selected = settings.sessions.includes(option.value) && !option.disabled;
        el('campaign-count').disabled = true;
        el('campaign-dedup').disabled = Object.values(task.counts).some(count => count > 0);
        el('campaign-editor-title').textContent = `Editar tarefa #${task.id}`;
        el('campaign-save-button').textContent = 'Salvar alterações';
        el('campaign-cancel-edit').hidden = false;
        el('campaign-edit-note').hidden = false;
        el('campaign-warm-fields').hidden = !settings.warming;
        renderSessions();
        reveal('campaign-builder');
    }
    async function load() {
        const current = ++version;
        try {
            const data = await api();
            if (current !== version) return;
            snapshot = data;
            const leadTask = el('campaign-leads-task');
            const chosenTask = leadTask.value;
            leadTask.innerHTML = '<option value="">Selecione uma tarefa</option>' + data.campaigns.map(task => `<option value="${task.id}">#${task.id} · ${esc(task.name)}</option>`).join('');
            leadTask.value = chosenTask;

            if (!viewInitialized) {
                el('campaign-builder').open = data.campaigns.length === 0;
                viewInitialized = true;
            }
            el('campaign-lead-total').textContent = (data.assigned_leads || 0).toLocaleString('pt-BR');
            el('campaign-task-total').textContent = data.campaigns.length;
            el('campaign-running-total').textContent = `${data.campaigns.filter(task => task.status === 'running').length} em execução`;
            el('campaign-added-total').textContent = data.campaigns.reduce((total, task) => total + (task.counts.added || 0), 0).toLocaleString('pt-BR');
            // Preserve forms while the user is editing a group.
            if (groupActionSubmitting || (el('campaign-list').contains(document.activeElement) && document.activeElement.matches('input')) || [...el('campaign-list').querySelectorAll('input[name="password"]')].some(input => input.value)) return;
            const openDetails = new Set([...el('campaign-list').querySelectorAll('details[open][data-detail]')].map(detail => detail.dataset.detail));
            const logScroll = new Map([...el('campaign-list').querySelectorAll('.gc-history')].map(history => [history.dataset.detail, history.querySelector('.gc-log-list')?.scrollTop || 0]));
            el('campaign-list').innerHTML = data.campaigns.map(task => {
                const busy = data.worker_active || task.status === 'running';
                const counts = task.counts;
                rememberEvents(task.id, task.events);
                const perGroup = task.settings.limit_scope === 'group';
                const dailyGoal = perGroup ? task.groups.reduce((sum, group) => sum + group.daily_limit, 0) : task.settings.daily_limit;
                const dailyAdded = task.groups.reduce((sum, group) => sum + (group.today_added || 0), 0);
                const focus = perGroup ? task.groups.find(group => group.status !== 'error' && (group.today_added || 0) < group.daily_limit) : null;
                const sessionWaits = task.session_waits || [];
                const spamAlert = sessionWaits.length ? `<div class="gc-alert" role="alert"><strong>⚠️ Sessões limitadas pelo Telegram (spam/flood)</strong><p>Estas contas não serão usadas até o horário indicado. A tarefa não envia leads enquanto todas estiverem limitadas.</p><ul>${sessionWaits.map(wait => `<li><strong>${esc(wait.name)}</strong> — limitada até ${esc(new Date(wait.until * 1000).toLocaleString('pt-BR'))}${wait.kind ? ` · ${esc(wait.kind)}` : ''}${wait.reason ? ` · ${esc(wait.reason)}` : ''}</li>`).join('')}</ul></div>` : `<p class="info gc-note"><strong>Sessões:</strong> nenhuma limitação de spam/flood registrada para as contas desta tarefa.</p>`;
                return `<section class="card task-card-modern gc-task">
                    <div class="gc-task-head"><div><span class="gc-task-id">TAREFA #${task.id}</span><h3>${esc(task.name)}</h3></div><div class="gc-task-actions"><span class="gc-badge ${esc(task.status)}">${esc(labels[task.status] || task.status)}</span>
                    ${task.status === 'running' ? `<button class="btn btn-warning" data-action="pause" data-id="${task.id}">Pausar tarefa</button>` : `<button class="btn btn-primary" data-action="start" data-id="${task.id}" ${busy || !task.groups.length ? 'disabled' : ''}>Iniciar tarefa</button>`}
                    <button class="btn btn-primary" data-action="edit" data-id="${task.id}" ${busy || !task.groups.length ? 'disabled' : ''}>Editar tarefa</button>
                    <button type="button" class="btn btn-primary" data-action="copy-links" data-id="${task.id}" ${task.groups.some(group => groupShareLink(group)) ? '' : 'disabled'} title="Copiar nomes e links dos grupos desta tarefa">Copiar nomes e links</button>
                    <button class="btn btn-danger" data-action="delete" data-id="${task.id}" ${busy ? 'disabled' : ''}>Excluir tarefa</button></div></div>
                    <div class="gc-task-body">
                    <div class="gc-task-meta"><span>${task.groups.length} grupos</span><span>${task.settings.sessions.length} sessões</span><span>${counts.unresolved || 0} referências não resolvidas · preservadas na base</span><span>${task.settings.sessions.length > 1 ? 'Multi-sessão simultâneo' : 'Uma sessão selecionada'}</span><span title="${esc((task.active_sessions || []).join(', '))}">${(task.active_sessions || []).length} sessão(ões) com tentativa em andamento</span><span>${task.settings.warming ? 'Com aquecimento' : 'Sem aquecimento'}</span><span>${task.settings.dedup === 'task' ? 'Um grupo por lead' : 'Uma vez por grupo'}</span></div>
                    <div class="gc-daily-overview">${progress(dailyAdded, dailyGoal, 'Meta da tarefa · 24 horas')}<div class="gc-focus"><span class="gc-eyebrow">${task.status === 'running' ? 'Destino prioritário' : 'Próximo destino'}</span><strong>${focus ? esc(focus.title) : perGroup ? 'Sem grupo elegível agora' : 'Distribuição entre grupos'}</strong><small>${focus ? focus.status === 'error' ? 'Sequência bloqueada: revise o erro deste grupo e reinicie a tarefa. Os próximos grupos aguardam.' : focus.today >= focus.daily_limit ? 'Aguardando confirmação das vagas reservadas. Os próximos grupos aguardam.' : 'As sessões trabalham neste grupo até a meta. Grupos com erro são sinalizados e ignorados.' : 'Confira as cotas e os estados dos grupos abaixo.'}</small></div></div>
                    ${spamAlert}
                    <div class="task-queue-summary gc-task-stats"><div><strong>${counts.added || 0}</strong><span>Adicionados</span></div><div><strong>${counts.failed || 0}</strong><span>Não adicionados</span></div><div><strong>${counts.skipped || 0}</strong><span>Duplicados ignorados</span></div><div><strong>${(counts.unknown || 0) + (counts.sending || 0)}</strong><span>Sem confirmação</span></div></div>
                    <p class="info">${task.lead_source ? `Arquivo desta tarefa: <strong>${esc(task.lead_source.filename)}</strong> · ${task.lead_count} contatos importados · ${task.excluded_lead_count || 0} retirados por conta desativada` : 'Esta tarefa está sem arquivo próprio. Importe os contatos para habilitar as adições; a lista compartilhada antiga não será usada.'}</p>
                    <button type="button" class="btn btn-primary" data-action="import-leads" data-id="${task.id}">Importar arquivo desta tarefa</button><a class="btn btn-primary gc-export-leads" href="/api/group-campaigns/${task.id}/leads/export" download="leads-tarefa-${task.id}.json">Exportar base limpa (JSON)</a><small>Exporte os contatos desta tarefa e importe o JSON no outro login. O arquivo exclui contas comprovadamente desativadas. Referências não resolvidas em uma sessão são preservadas. Contatos adicionados e outros resultados continuam incluídos. O arquivo original no computador é preservado.</small>
                    ${task.error ? `<p class="gc-alert" role="alert">${esc(task.error)}</p>` : ''}
                    ${!task.groups.length ? '<p class="info">Esta tarefa não tem mais grupos. O histórico foi mantido; você pode excluir a tarefa quando quiser.</p>' : ''}
                    ${busy ? '<p class="info gc-note">Para editar, excluir ou substituir grupos, pause a tarefa e aguarde a ação atual terminar.</p>' : ''}
                    <form data-settings="${task.id}" class="gc-upload gc-delay-settings"><div class="form-group"><label>Delay mínimo (segundos)<input name="delay_min" type="number" min="1" max="3600" required value="${task.settings.delay_min ?? task.settings.delay ?? 60}" ${busy ? 'disabled' : ''}></label></div><div class="form-group"><label>Delay máximo (segundos)<input name="delay_max" type="number" min="1" max="3600" required value="${task.settings.delay_max ?? task.settings.delay ?? 60}" ${busy ? 'disabled' : ''}></label></div><button class="btn btn-primary" ${busy ? 'disabled' : ''}>Salvar delay</button></form><small>Pause a tarefa para ajustar. Para delay fixo, informe o mesmo valor nos dois campos. No modo simultâneo, o intervalo vale por sessão. O tempo de resposta e as esperas exigidas pelo Telegram continuam valendo.</small>
                    ${task.settings.limit_scope === 'task' ? `<form data-settings="${task.id}" class="gc-upload"><div class="form-group"><label>Limite por ciclo de 24h de todos os grupos juntos<input name="daily_limit" type="number" value="${task.settings.daily_limit}" min="1" max="10000" required ${busy ? 'disabled' : ''}></label></div><button class="btn btn-primary" ${busy ? 'disabled' : ''}>Salvar limite</button></form>` : ''}
                    <details class="gc-group-list" data-detail="groups-${task.id}"><summary>Ver grupos da tarefa <span class="gc-badge">${task.groups.length}</span></summary><div class="gc-group-grid">
                    ${task.groups.map(group => `<details class="gc-group ${group.status === 'error' ? 'gc-group-error' : ''} ${focus?.id === group.id ? 'gc-focused' : ''}" data-detail="group-${group.id}">
                        <summary><span><span class="gc-group-title">${esc(group.title)}</span><small>${group.members?.count != null ? `${Number(group.members.count).toLocaleString('pt-BR')} membros no grupo · ` : ''}${group.added} adicionados pela tarefa · cota usada no ciclo: ${group.today}${task.settings.limit_scope === 'group' ? '/' + group.daily_limit : ''}</small>${group.status === 'error' ? `<span class="gc-group-error-message" role="status">Erro: ${esc(group.error || 'Revise o acesso e as permissões deste grupo.')} · Grupo ignorado na distribuição.</span>` : ''}${perGroup ? progress(group.today_added || 0, group.daily_limit, 'Meta do grupo · 24 horas') : ''}${group.quota_resets_at ? `<small>Ciclo renova em ${esc(new Date(group.quota_resets_at * 1000).toLocaleString('pt-BR'))}</small>` : '<small>O ciclo de 24h começa na primeira tentativa.</small>'}${group.today > (group.today_added || 0) ? `<small class="gc-reserved">${group.today - (group.today_added || 0)} vaga(s) reservada(s) por envios em andamento ou sem confirmação</small>` : ''}</span><span class="gc-badge ${esc(group.status)}">${esc(labels[group.status] || group.status)}</span><i class="fas fa-chevron-down" aria-hidden="true"></i></summary>
                        <div class="gc-group-content">
                        ${group.channel_id ? `<div class="gc-members"><p><strong>Membros no Telegram: ${group.members?.count != null ? Number(group.members.count).toLocaleString('pt-BR') : 'Ainda não consultado'}</strong></p>${group.members?.updated ? `<small>Consultado em ${esc(new Date(group.members.updated * 1000).toLocaleString('pt-BR'))}. Atualização automática durante a execução, com intervalo mínimo de 1 minuto.</small>` : ''}${group.members?.error ? `<p class="gc-alert">${esc(group.members.error)}</p>` : ''}<button type="button" class="btn btn-primary" data-action="members" data-id="${task.id}" data-group-id="${group.id}">Atualizar membros</button><button type="button" class="btn btn-danger" data-action="remove-deleted-members" data-id="${task.id}" data-group-id="${group.id}" ${busy ? 'disabled' : ''} title="Usa uma sessão dona ou administradora com permissão para remover membros">Remover contas excluídas</button><small>Use com a tarefa pausada. A ação procura uma sessão dona ou administradora deste grupo.</small></div>` : ''}
                        ${group.invite && /^https:\/\/t\.me\//.test(group.invite) ? `<p><a href="${esc(group.invite)}" target="_blank" rel="noopener noreferrer">Abrir grupo no Telegram ↗</a></p>` : ''}
                        ${group.error ? `<p class="gc-alert" role="alert">${esc(group.error)}</p>` : ''}
                        ${group.status === 'warming' ? `<p>Aquecimento até ${esc(new Date(group.warm_until * 1000).toLocaleString('pt-BR'))}</p>` : ''}
                        <form data-group="${group.id}" data-task="${task.id}">
                            ${task.settings.limit_scope === 'group' ? `<div class="gc-upload"><div class="form-group"><label>Leads por dia neste grupo<input name="daily_limit" type="number" value="${group.daily_limit}" min="1" max="10000" required ${busy ? 'disabled' : ''}></label></div><button class="btn btn-primary" name="action" value="limit" ${busy ? 'disabled' : ''}>Salvar limite</button></div>` : ''}
                            <details class="gc-replace" data-detail="replace-${group.id}"><summary>Precisa substituir este grupo?</summary><p>Use outro grupo no lugar deste. O histórico de leads e a cota do dia são mantidos.</p>
                            <div class="form-group"><label>Nome do novo grupo<input name="title" value="${esc(group.title)}" maxlength="100" ${busy ? 'disabled' : ''}></label></div>
                            <div class="form-group"><label>Link de um grupo existente (opcional)<input name="reference" placeholder="https://t.me/+..." ${busy ? 'disabled' : ''}></label><small>Deixe vazio para criar um novo grupo quando iniciar a tarefa.</small></div>
                            <button class="btn btn-primary" name="action" value="replace" ${busy ? 'disabled' : ''}>Substituir grupo</button><small>O grupo anterior permanece no Telegram.</small></details>
                        </form>${ownershipControls(task, group, busy)}${deletionControls(task, group, busy)}</div>
                    </details>`).join('')}</div></details>
                    <details class="gc-history" data-detail="events-${task.id}"><summary><span>Central de logs</span><span class="gc-live-state" data-state="${streamState}">${streamState === 'live' ? 'Ao vivo' : 'Conectando…'}</span><span class="gc-badge gc-log-count">${(liveEvents.get(task.id) || []).length}</span></summary><div class="gc-log-toolbar"><input type="search" data-log-search="${task.id}" placeholder="Buscar sessão, grupo ou mensagem…" aria-label="Buscar nos logs" value="${esc(logFilters.get(task.id)?.query || '')}"><select data-log-tone="${task.id}" aria-label="Filtrar tipo de evento">${[['','Todos os eventos'],['info','Etapas'],['success','Sucessos'],['warning','Atenção'],['waiting','Esperas']].map(([value,label]) => `<option value="${value}" ${logFilters.get(task.id)?.tone === value ? 'selected' : ''}>${label}</option>`).join('')}</select></div><p class="gc-history-help">Eventos mais recentes primeiro · até 500 eventos no painel · conexão automática com o servidor. Você pode acompanhar os logs enquanto edita os grupos.</p><div class="gc-live-content">${renderHistory(liveEvents.get(task.id), logFilters.get(task.id))}</div></details>
                    </div>
                </section>`;
            }).join('') || '<div class="gc-empty"><i class="fas fa-layer-group" aria-hidden="true"></i><h3>Sua primeira tarefa começa aqui</h3><p>Escolha os grupos e as sessões. Depois de salvar, ela aparecerá neste espaço.</p><button class="btn btn-primary" type="button" data-reveal="campaign-builder">Criar minha primeira tarefa</button></div>';
            el('campaign-list').querySelectorAll('details[data-detail]').forEach(detail => detail.open = openDetails.has(detail.dataset.detail));
            el('campaign-list').querySelectorAll('.gc-history').forEach(history => {
                const list = history.querySelector('.gc-log-list');
                if (list) list.scrollTop = logScroll.get(history.dataset.detail) || 0;
            });
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
        el('campaign-new').addEventListener('click', async () => {
            resetEditor();
            reveal('campaign-builder');
            try { await loadSessions(); } catch (error) { notice(error.message, true); }
        });
        el('campaign-cancel-edit').addEventListener('click', () => { resetEditor(); el('campaign-builder').open = false; });
        el('campaign-create-form').addEventListener('input', preview);
        el('campaign-create-form').addEventListener('change', preview);
        el('campaign-session-options').addEventListener('change', event => {
            const option = [...el('campaign-sessions').options].find(option => option.value === event.target.value);
            if (option) option.selected = event.target.checked;
            preview();
        });
        el('campaign-session-search').addEventListener('input', renderSessions);
        preview();
        el('campaign-images-clear').addEventListener('click', () => {
            selectedImages = [];
            el('campaign-images').value = '';
            el('campaign-images-status').textContent = 'Nenhuma imagem selecionada';
        });
        el('campaign-images').addEventListener('change', () => {
            el('campaign-images-status').textContent = [...el('campaign-images').files].map(file => file.name).join(', ');
        });
        el('campaign-group-image').addEventListener('change', () => {
            const file = el('campaign-group-image').files[0];
            el('campaign-group-image-status').textContent = file ? file.name : '';
        });
        el('campaign-descriptions-file').addEventListener('change', async event => {
            const file = event.target.files[0];
            if (!file) return;
            try {
                if (file.size > 1024 * 1024) throw new Error('O arquivo de descrições deve ter até 1 MB.');
                const text = await file.text();
                const blocks = text.replace(/\r/g, '').split(/\n\s*\n/).map(item => item.trim()).filter(Boolean);
                selectedDescriptions = (blocks.length > 1 ? blocks : text.split(/\r?\n/)).map(item => item.trim()).filter(Boolean).slice(0, 30);
                if (!selectedDescriptions.length) throw new Error('O arquivo não contém descrições válidas.');
                el('campaign-descriptions-status').textContent = `${selectedDescriptions.length} descrições carregadas`;
            } catch (error) { selectedDescriptions = []; el('campaign-descriptions-status').textContent = ''; notice(error.message, true); }
        });
        el('campaign-warming').addEventListener('change', () => {
            el('campaign-warm-fields').hidden = el('campaign-warming').value !== 'yes';
        });
        el('campaign-sessions').addEventListener('change', () => {
            el('campaign-session-count').textContent = `${el('campaign-sessions').selectedOptions.length} selecionadas`;
        });
        el('campaign-names-file').addEventListener('change', async event => {
            const file = event.target.files[0];
            if (!file) return;
            try {
                if (file.size > 1024 * 1024) throw new Error('O arquivo de nomes deve ter até 1 MB.');
                el('campaign-names').value = await file.text();
                preview();
            } catch (error) { notice(error.message, true); }
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
                if (Number(el('campaign-delay-max').value) < Number(el('campaign-delay-min').value)) throw new Error('O intervalo máximo deve ser maior ou igual ao mínimo.');
                const names = editingId === null ? customGroupNames() : [];
                if (names.length > 30 || names.some(name => Array.from(name).length > 100)) throw new Error('Use até 30 nomes com no máximo 100 caracteres cada.');
                const files = [...el('campaign-images').files];
                if (files.length) {
                    if (files.length > 30 || files.some(file => file.size > 10 * 1024 * 1024) || files.reduce((sum, file) => sum + file.size, 0) > 30 * 1024 * 1024) throw new Error('Selecione até 30 imagens: 10 MB por arquivo e 30 MB no total.');
                    const data = new FormData();
                    files.forEach(file => data.append('images', file));
                    selectedImages = (await api('/images', {method:'POST', body:data})).images;
                    el('campaign-images').value = '';
                    el('campaign-images-status').textContent = `${selectedImages.length} imagens carregadas`;
                }
                const groupImage = el('campaign-group-image').files[0];
                if (groupImage) {
                    if (groupImage.size > 10 * 1024 * 1024) throw new Error('A imagem do grupo deve ter até 10 MB.');
                    const data = new FormData();
                    data.append('images', groupImage);
                    selectedGroupImage = (await api('/images', {method:'POST', body:data})).images[0];
                    el('campaign-group-image').value = '';
                    el('campaign-group-image-status').textContent = 'Imagem dos grupos carregada';
                }
                const payload = {
                    images:selectedImages,
                    group_image:selectedGroupImage, descriptions:selectedDescriptions,
                    group_names:editingId === null ? names : undefined,
                    name:el('campaign-name').value, count:el('campaign-count').value, daily_limit:el('campaign-limit').value,
                    admin_usernames:el('campaign-admin').value,
                    sessions:Array.from(el('campaign-sessions').selectedOptions, option => option.value),
                    warming:el('campaign-warming').value === 'yes', messages:el('campaign-phrases').value,
                    warm_days:el('campaign-warm-days').value, warm_interval:el('campaign-warm-interval').value,
                    parallel_sessions:el('campaign-parallel').value === 'yes', delay_min:el('campaign-delay-min').value, delay_max:el('campaign-delay-max').value, dedup:el('campaign-dedup').value, limit_scope:el('campaign-limit-scope').value,
                };
                const result = await api(editingId === null ? '' : `/${editingId}`, json(editingId === null ? 'POST' : 'PUT', payload));
                resetEditor();
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
                data.append('campaign_id', el('campaign-leads-task').value);
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
                const id = Number(button.dataset.id);
                if (button.dataset.action === 'import-leads') {
                    el('campaign-leads-task').value = String(id);
                    reveal('campaign-bank');
                    button.disabled = false;
                    return;
                }
                if (button.dataset.action === 'members') {
                    button.textContent = 'Consultando Telegram…';
                    try {
                        const result = await api(`/${id}/groups/${button.dataset.groupId}/members`, {method:'POST'});
                        notice(result.members.error || (result.members.count != null ? `${Number(result.members.count).toLocaleString('pt-BR')} membros na última consulta ao Telegram.` : 'Consulta em andamento. Atualize novamente em instantes.'), Boolean(result.members.error));
                        document.activeElement?.blur();
                        await load();
                    } finally {
                        button.disabled = false;
                        button.textContent = 'Atualizar membros';
                    }
                    return;
                }
                if (button.dataset.action === 'remove-deleted-members') {
                    const task = snapshot.campaigns.find(task => task.id === id);
                    const group = task.groups.find(group => group.id === Number(button.dataset.groupId));
                    if (!window.confirm(`Remover do grupo "${group.title}" todas as contas marcadas como excluídas pelo Telegram?`)) {
                        button.disabled = false;
                        return;
                    }
                    button.textContent = 'Removendo contas…';
                    try {
                        const result = await api(`/${id}/groups/${group.id}/remove-deleted-members`, {method:'POST'});
                        notice(result.message);
                        await load();
                    } finally {
                        button.disabled = false;
                        button.textContent = 'Remover contas excluídas';
                    }
                    return;
                }
                if (button.dataset.action === 'copy-links') {
                    await copyGroupList(snapshot.campaigns.find(task => task.id === id));
                    button.disabled = false;
                    return;
                }
                if (button.dataset.action === 'edit') {
                    await editTask(snapshot.campaigns.find(task => task.id === id));
                    button.disabled = false;
                    return;
                }
                if (button.dataset.action === 'delete') {
                    const task = snapshot.campaigns.find(task => task.id === id);
                    if (!window.confirm(`Excluir a tarefa "${task.name}" e seu histórico? Os grupos no Telegram e o banco de leads serão mantidos.`)) {
                        button.disabled = false;
                        return;
                    }
                    await api(`/${id}`, {method:'DELETE'});
                    if (editingId === id) { resetEditor(); el('campaign-builder').open = false; }
                    notice('Tarefa excluída');
                    await load();
                    return;
                }
                await api(`/${button.dataset.id}/${button.dataset.action}`, {method:'POST'});
                notice(button.dataset.action === 'pause' ? 'Pausa solicitada. Aguardando a ação atual terminar.' : 'Tarefa iniciada');
                await load();
            } catch (error) { notice(error.message, true); button.disabled = false; }
        });
        el('campaign-list').addEventListener('submit', event => {
            event.preventDefault();
            const form = event.target;
            if (form.dataset.deleteGroup) {
                if (groupActionSubmitting) return;
                const task = snapshot.campaigns.find(item => item.id === Number(form.dataset.task));
                const group = task.groups.find(item => item.id === Number(form.dataset.deleteGroup));
                if (!window.confirm(`Excluir permanentemente o grupo "${group.title}" (ID Telegram: ${group.channel_id})?\n\nO grupo será apagado no Telegram para todos os participantes e removido do painel. Essa ação não pode ser desfeita.`)) return;
                groupActionSubmitting = true;
                submit(form, async () => {
                    try {
                        const result = await api(`/${task.id}/groups/${group.id}`, json('DELETE', {confirmed:true, title:group.title, channel_id:group.channel_id}));
                        if (editingId === task.id) resetEditor();
                        notice(result.message);
                    } finally {
                        groupActionSubmitting = false;
                        document.activeElement?.blur();
                        await load();
                    }
                });
                return;
            }
            if (form.dataset.owner) {
                if (groupActionSubmitting) return;
                const checkOnly = form.dataset.ownerCheck === 'true';
                const payload = checkOnly ? {} : {
                    username:form.elements.username.value,
                    password:form.elements.password.value,
                    confirmed:form.elements.confirmed.checked,
                };
                groupActionSubmitting = true;
                submit(form, async () => {
                    try {
                        const result = await api(`/${form.dataset.task}/groups/${form.dataset.owner}/ownership${checkOnly ? '/check' : ''}`, json('POST', payload));
                        notice(result.message, result.status !== 'confirmed');
                    } finally {
                        delete payload.password;
                        if (!checkOnly) {
                            form.elements.password.value = '';
                            form.elements.confirmed.checked = false;
                        }
                        groupActionSubmitting = false;
                        document.activeElement?.blur();
                        await load();
                    }
                });
                return;
            }
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
                notice(replace ? 'Grupo substituído. Clique em Iniciar para continuar o ciclo.' : 'delay_min' in data ? 'Delay atualizado. Inicie a tarefa para usar o novo intervalo.' : 'Limite atualizado');
                document.activeElement?.blur();
                await load();
            });
        });
        el('campaign-list').addEventListener('input', event => {
            const id = Number(event.target.dataset.logSearch || event.target.dataset.logTone);
            if (!id) return;
            const filter = logFilters.get(id) || {};
            if (event.target.dataset.logSearch) filter.query = event.target.value;
            else filter.tone = event.target.value;
            logFilters.set(id, filter);
            updateLogs(id);
        });
        startLogStream();
        window.addEventListener('pagehide', () => { logStream?.close(); logStream = null; });
        window.addEventListener('pageshow', startLogStream);
        el('campaign-refresh').addEventListener('click', async () => {
            await load();
            loadSessions().catch(error => notice(error.message, true));
        });
        document.querySelector('[data-tab="comingSoon"]').addEventListener('click', async () => {
            await load();
            loadSessions().catch(error => notice(error.message, true));
        });
        if (el('comingSoon').classList.contains('active')) {
            load();
            loadSessions().catch(error => notice(error.message, true));
        }
        setInterval(() => { if (el('comingSoon').classList.contains('active')) load(); }, 10000);
    });
})();
