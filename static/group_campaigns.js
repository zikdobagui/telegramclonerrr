(() => {
    const el = id => document.getElementById(id);
    const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const labels = {paused:'Pausada', running:'Em execução', pending:'A criar / vincular', creating:'Criando', warming:'Aquecendo', ready:'Distribuindo / aguardando cota ou leads', error:'Precisa de revisão'};
    let version = 0;
    let snapshot = null;
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
    async function loadSessions() {
        const response = await fetch('/api/sessions', {cache:'no-store'});
        if (!response.ok) throw new Error('Não foi possível carregar sessões');
        const data = await response.json();
        const selected = new Set(Array.from(el('campaign-sessions').selectedOptions, option => option.value));
        el('campaign-sessions').innerHTML = (data.sessions || []).map(s => {
            const unavailable = s.active === false || (s.status && s.status !== 'active');
            return `<option value="${esc(s.session_name)}" ${unavailable ? 'disabled' : ''} ${selected.has(s.session_name) ? 'selected' : ''}>${esc(s.first_name || s.session_name)}${unavailable ? ' — indisponível' : ''}</option>`;
        }).join('');
    }
    async function load() {
        const current = ++version;
        try {
            const data = await api();
            if (current !== version) return;
            snapshot = data;
            el('campaign-lead-total').textContent = `${data.total_leads} leads no banco`;
            // Preserve forms while the user is editing a group.
            if (el('campaign-list').contains(document.activeElement) && document.activeElement.matches('input')) return;
            const openDetails = new Set([...el('campaign-list').querySelectorAll('details[open][data-detail]')].map(detail => detail.dataset.detail));
            el('campaign-list').innerHTML = data.campaigns.map(task => {
                const busy = data.worker_active || task.status === 'running';
                const counts = task.counts;
                return `<section class="card" style="margin-top:18px">
                    <h3>#${task.id} · ${esc(task.name)} — ${esc(labels[task.status] || task.status)}</h3>
                    <p>${task.settings.sessions.length} sessões · ${task.groups.length} grupos · Aquecimento: ${task.settings.warming ? 'sim' : 'não'} · ${task.settings.dedup === 'task' ? 'Lead único na tarefa' : 'Lead único por grupo'}</p>
                    <p>Adicionados: ${counts.added || 0} · Não adicionados: ${counts.failed || 0} · Duplicados ignorados: ${counts.skipped || 0} · Sem confirmação: ${(counts.unknown || 0) + (counts.sending || 0)}</p>
                    <p>Leads sem confirmação ficam reservados para evitar repetição.</p>
                    ${task.error ? `<p role="alert">${esc(task.error)}</p>` : ''}
                    <button class="btn btn-primary" data-action="start" data-id="${task.id}" ${busy ? 'disabled' : ''}>Iniciar / continuar</button>
                    <button class="btn btn-danger" data-action="pause" data-id="${task.id}" ${task.status !== 'running' ? 'disabled' : ''}>Pausar</button>
                    ${task.settings.limit_scope === 'task' ? `<form data-settings="${task.id}" style="margin-top:12px"><label>Limite diário da tarefa <input name="daily_limit" type="number" value="${task.settings.daily_limit}" min="1" max="10000" required ${busy ? 'disabled' : ''}></label><button class="btn btn-primary" ${busy ? 'disabled' : ''}>Salvar limite</button></form>` : ''}
                    ${task.groups.map(group => `<details data-detail="group-${group.id}" style="margin-top:16px;border-top:1px solid var(--ui-border, #334155);padding-top:12px">
                        <summary>${esc(group.title)} · ${esc(labels[group.status] || group.status)} · ${group.added} adicionados · hoje: ${group.today}${task.settings.limit_scope === 'group' ? '/' + group.daily_limit : ''}</summary>
                        ${group.invite && /^https:\/\/t\.me\//.test(group.invite) ? `<p><a href="${esc(group.invite)}" target="_blank" rel="noopener noreferrer">Abrir grupo no Telegram</a></p>` : ''}
                        ${group.error ? `<p role="alert">${esc(group.error)}</p>` : ''}
                        ${group.status === 'warming' ? `<p>Aquecimento até ${esc(new Date(group.warm_until * 1000).toLocaleString('pt-BR'))}</p>` : ''}
                        <form data-group="${group.id}" data-task="${task.id}">
                            <div class="form-group"><label>Limite diário deste grupo<input name="daily_limit" type="number" value="${group.daily_limit}" min="1" max="10000" required ${busy || task.settings.limit_scope === 'task' ? 'disabled' : ''}></label></div>
                            ${task.settings.limit_scope === 'group' ? `<button class="btn btn-primary" name="action" value="limit" ${busy ? 'disabled' : ''}>Salvar limite</button>` : ''}
                            <div class="form-group"><label>Nome do grupo substituto<input name="title" value="${esc(group.title)}" maxlength="100" ${busy ? 'disabled' : ''}></label></div>
                            <div class="form-group"><label>Link do grupo substituto (vazio = criar um novo ao iniciar)<input name="reference" placeholder="https://t.me/+..." ${busy ? 'disabled' : ''}></label></div>
                            <button class="btn btn-danger" name="action" value="replace" ${busy ? 'disabled' : ''}>Retirar este grupo e substituir</button>
                            <small>Retira apenas da tarefa. O grupo anterior permanece no Telegram e no histórico.</small>
                        </form>
                    </details>`).join('')}
                    <details data-detail="events-${task.id}" style="margin-top:16px"><summary>Histórico recente</summary>${task.events.map(event => `<p>${esc(new Date(event.created * 1000).toLocaleString('pt-BR'))} — ${esc(event.message)}</p>`).join('') || '<p>Aguardando início.</p>'}</details>
                </section>`;
            }).join('') || '<p>Nenhuma tarefa criada ainda.</p>';
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
