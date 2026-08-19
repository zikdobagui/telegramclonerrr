const socket = io();
let currentSessions = [];
let selectedSessionIndex = null;
let currentSessionFilter = 'all';
let liveRefreshTimer = null;
let liveRefreshBusy = false;
let lastLiveRefreshAt = null;
let lastImportProgressLogAt = 0;

function getActiveTabId() {
    return document.querySelector('.tab-content.active')?.id || 'dashboard';
}

function getFloodAdvice(info = {}) {
    if (info.expired) {
        return {
            title: 'Prazo de quarentena expirou',
            detail: info.flood_until ? `Registrado até ${info.flood_until}` : 'Sem prazo ativo no momento',
            hint: info.recommended_action || 'O sistema vai liberar automaticamente ao sincronizar as sessões.'
        };
    }

    if (info.flood_until) {
        const hours = info.remaining_hours || 0;
        const minutes = info.remaining_minutes || 0;
        return {
            title: `Quarentena até ${info.flood_until}`,
            detail: `${hours}h ${minutes}min restantes`,
            hint: info.recommended_action || 'O sistema libera automaticamente quando o prazo terminar.'
        };
    }

    return {
        title: 'Aguardando validação manual',
        detail: 'Sem prazo de liberação informado pela plataforma',
        hint: info.recommended_action || 'Não use esta sessão automaticamente; valide manualmente antes de reativar.'
    };
}

async function refreshActiveTab(silent = true) {
    if (liveRefreshBusy) return;
    liveRefreshBusy = true;

    try {
        const tab = getActiveTabId();
        if (tab === 'dashboard' && typeof loadDashboard === 'function') await loadDashboard();
        if (tab === 'sessions' && typeof loadSessions === 'function') await loadSessions();
        if (tab === 'tasks' && typeof loadTasks === 'function') await loadTasks();
        if (tab === 'stats' && typeof loadStats === 'function') await loadStats();

        lastLiveRefreshAt = new Date();
        const indicator = document.getElementById('live-refresh-at');
        if (indicator) {
            indicator.textContent = lastLiveRefreshAt.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
        }
    } catch (error) {
        console.error('Erro na atualização automática:', error);
        if (!silent) showNotification('Não consegui atualizar os dados agora', 'warning', 4000);
    } finally {
        liveRefreshBusy = false;
    }
}

function startPanelLiveRefresh() {
    if (liveRefreshTimer) clearInterval(liveRefreshTimer);
    liveRefreshTimer = setInterval(() => refreshActiveTab(true), 10000);
}

function updateFooterClock() {
    const clock = document.getElementById('footer-clock');
    if (!clock) return;
    clock.textContent = new Date().toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

async function readJsonResponse(response) {
    const contentType = response.headers.get('content-type') || '';
    const text = await response.text();

    if (!contentType.includes('application/json')) {
        const plain = text.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
        throw new Error(plain ? plain.slice(0, 180) : `Resposta inválida do servidor (${response.status})`);
    }

    try {
        return JSON.parse(text);
    } catch (error) {
        throw new Error(`JSON inválido do servidor (${response.status})`);
    }
}

// Monitor de conexão do Socket
socket.on('connect', () => {
    console.log('✅ Socket.IO conectado!');
    showNotification('Conectado ao servidor', 'success', 3000);
    // Ao reconectar, recarrega o estado persistido para recuperar tarefas
    // que continuaram executando enquanto a página estava fechada.
    if (typeof loadTasks === 'function') {
        loadTasks().catch(error => console.warn('Falha ao recuperar tarefas:', error));
    }
});

socket.on('disconnect', () => {
    console.log('❌ Socket.IO desconectado!');
    showNotification('Painel desconectado; as tarefas continuam no servidor. Reconectando...', 'warning', 6000);
});

socket.on('connect_error', (error) => {
    console.error('❌ Erro de conexão Socket.IO:', error);
    showNotification('Sem conexão com os logs; o processamento no servidor não é cancelado.', 'warning', 5000);
});

// Quando o usuário volta para a aba, recupera status e logs atualizados.
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && typeof loadTasks === 'function') {
        loadTasks().catch(error => console.warn('Falha ao atualizar tarefas:', error));
    }
});

socket.on('reaction_progress', (data) => {
    appendReactionLiveLog(data);
});

socket.on('process_update', (data) => {
    loadProcesses();
    const activeTab = getActiveTabId();
    if (data.type === 'session_import') {
        const now = Date.now();
        if (data.status === 'running' && now - lastImportProgressLogAt > 2500) {
            lastImportProgressLogAt = now;
            addLog('import-logs', data.message || 'Importação em andamento...', 'info');
        }
        if (data.status === 'completed') {
            addLog('import-logs', data.message || 'Importação concluída.', 'success');
            loadSessions();
            loadDashboard();
            showNotification(data.message || 'Importação concluída!', 'success', 8000);
        }
        if (data.status === 'error') {
            addLog('import-logs', data.message || 'Erro na importação.', 'error');
            showNotification(data.message || 'Erro na importação.', 'error', 10000);
        }
    }
    if (activeTab === 'dashboard') {
        loadDashboard();
        const healthText = document.getElementById('dash-health-text');
        if (healthText && data.status === 'running') {
            healthText.textContent = `${data.title || 'Processo'} em andamento: ${data.message || ''}`;
        }
    }
});

// ========== NOTIFICATION SYSTEM ==========
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const icon = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    }[type] || 'ℹ️';
    
    notification.innerHTML = `
        <div style="display: flex; align-items: start; gap: 12px;">
            <div style="font-size: 24px;">${icon}</div>
            <div style="flex: 1;">
                <div style="font-weight: 700; margin-bottom: 4px; color: #f1f5f9;">${type.toUpperCase()}</div>
                <div style="color: #cbd5e1; font-size: 14px;">${message}</div>
            </div>
            <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 20px; padding: 0; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border-radius: 4px; transition: all 0.2s;">
                ×
            </button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    if (duration > 0) {
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
            setTimeout(() => notification.remove(), 400);
        }, duration);
    }
}

// Adicionar animação de saída
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOutRight {
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
`;
document.head.appendChild(style);

// Aguarda o DOM estar pronto para adicionar event listeners
document.addEventListener('DOMContentLoaded', function() {
    updateFooterClock();
    setInterval(updateFooterClock, 30000);

    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(tab).classList.add('active');
            
            if (tab === 'sessions') loadSessions();
            if (tab === 'tasks') {
                loadTasks();
                loadTaskSessions();
            }
            if (tab === 'extract') loadSessionsForExtract();
            if (tab === 'add') {
                loadActiveSessions();
            }
            if (tab === 'warming') loadWarmingGroups();
            if (tab === 'reactions') loadReactions();
            if (tab === 'stats') loadStats();
        });
    });
    
    // Mostrar arquivos selecionados
    const sessionFilesInput = document.getElementById('session-files');
    if (sessionFilesInput) {
        sessionFilesInput.addEventListener('change', function(e) {
            const files = e.target.files;
            const fileList = document.getElementById('selected-files');
            
            if (files.length > 0) {
                const fileNames = Array.from(files).slice(0, 2).map(f => f.name).join(', ');
                const suffix = files.length > 2 ? ` +${files.length - 2}` : '';
                fileList.innerHTML = `<i class="fas fa-file"></i> ${files.length} arquivo(s): ${fileNames}${suffix}`;
            } else {
                fileList.innerHTML = 'Nenhum arquivo selecionado';
            }
        });
    }

    const sessionFolderInput = document.getElementById('session-folder-files');
    if (sessionFolderInput) {
        sessionFolderInput.setAttribute('webkitdirectory', '');
        sessionFolderInput.setAttribute('directory', '');
        sessionFolderInput.addEventListener('change', function(e) {
            importSessionsFromFileList(e.target.files, 'pasta', e.target);
        });
    }
    
    // Importar membros para adicionar
    const addImportFileInput = document.getElementById('add-import-file');
    if (addImportFileInput) {
        addImportFileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('add-import-status').innerHTML = `<i class="fas fa-file"></i> ${file.name} selecionado`;
            }
        });
    }

    const customReactionInput = document.getElementById('custom-reaction-value');
    if (customReactionInput) {
        customReactionInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addCustomReaction();
            }
        });
    }
});

// ========== CONFIGURAÇÃO DE MÚLTIPLAS APIs ==========

// Adicionar nova API
async function addApiConfig() {
    const api_id = document.getElementById('api_id').value;
    const api_hash = document.getElementById('api_hash').value;
    const api_name = document.getElementById('api_name').value || `API ${Date.now()}`;
    
    if (!api_id || !api_hash) {
        showNotification('Preencha API ID e API Hash!', 'error');
        return;
    }
    
    const response = await fetch('/api/config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            api_id: parseInt(api_id),
            api_hash,
            name: api_name,
            add: true
        })
    });
    
    const data = await response.json();
    
    if (response.ok && data.success) {
        showNotification(`API "${api_name}" adicionada com sucesso!`, 'success');
        showStatus('config-status', `✅ API adicionada! Total: ${data.total}`, 'success');
        
        // Limpa os campos
        document.getElementById('api_id').value = '';
        document.getElementById('api_hash').value = '';
        document.getElementById('api_name').value = '';
        
        // Recarrega a lista
        loadApiList();
    } else {
        showNotification(data.error || 'Erro ao adicionar API', 'error');
        showStatus('config-status', `❌ ${data.error || 'Erro ao adicionar API'}`, 'error');
    }
}

// Remover API
async function removeApi(api_id) {
    if (!confirm('Tem certeza que deseja remover esta API?')) {
        return;
    }
    
    const response = await fetch('/api/config', {
        method: 'DELETE',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({api_id: parseInt(api_id)})
    });
    
    const data = await response.json();
    
    if (response.ok && data.success) {
        showNotification('API removida com sucesso!', 'success');
        loadApiList();
    } else {
        showNotification(data.error || 'Erro ao remover API', 'error');
    }
}

// Carregar lista de APIs
async function loadApiList() {
    const response = await fetch('/api/config');
    const data = await response.json();
    
    const apiList = document.getElementById('api-list');
    const apiCount = document.getElementById('api-count');
    
    if (!data.configured || data.api_credentials.length === 0) {
        apiList.innerHTML = `
            <p style="color: #94a3b8; text-align: center; padding: 20px;">
                Nenhuma API cadastrada ainda
            </p>
        `;
        apiCount.textContent = '(0)';
        return;
    }
    
    apiCount.textContent = `(${data.total})`;
    
    apiList.innerHTML = data.api_credentials.map((api, index) => `
        <div style="background: rgba(15, 23, 42, 0.6); padding: 20px; border-radius: 12px; border: 1px solid rgba(59, 130, 246, 0.2);">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                <div>
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                        <span style="background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%); color: white; padding: 4px 12px; border-radius: 6px; font-size: 0.85em; font-weight: 600;">
                            #${index + 1}
                        </span>
                        <h4 style="margin: 0; color: #e2e8f0; font-size: 1.1em;">
                            ${api.name || 'Sem nome'}
                        </h4>
                    </div>
                    <div style="color: #94a3b8; font-size: 0.9em;">
                        <i class="fas fa-key"></i> API ID: <span style="color: #6ee7b7; font-family: monospace;">${api.api_id}</span>
                    </div>
                </div>
                <button onclick="removeApi(${api.api_id})" class="btn btn-danger" style="padding: 8px 16px;">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
            <div style="background: rgba(59, 130, 246, 0.1); padding: 10px; border-radius: 6px; border-left: 3px solid #3b82f6;">
                <div style="color: #94a3b8; font-size: 0.85em; margin-bottom: 4px;">API Hash:</div>
                <div style="color: #cbd5e1; font-family: monospace; font-size: 0.9em; word-break: break-all;">
                    ${api.api_hash}
                </div>
            </div>
        </div>
    `).join('');
}

// Carregar configuração (compatibilidade)
async function loadConfig() {
    loadApiList();
}

// Função antiga para compatibilidade
async function saveApiConfig() {
    addApiConfig();
}

function selectSessionsFolder() {
    const folderInput = document.getElementById('session-folder-files');
    if (!folderInput) {
        showNotification('Seletor de pasta não encontrado.', 'error');
        return;
    }
    folderInput.value = '';
    folderInput.click();
}

// Importar sessões em massa
async function importSessions() {
    const fileInput = document.getElementById('session-files');
    return importSessionsFromFileList(fileInput.files, 'arquivos', fileInput);
}

async function importSessionsFromFileList(fileList, sourceLabel = 'arquivos', sourceInput = null) {
    const files = Array.from(fileList || []).filter(file => file.name.toLowerCase().endsWith('.session'));

    if (files.length === 0) {
        showNotification(`Nenhum arquivo .session encontrado ${sourceLabel === 'pasta' ? 'na pasta selecionada' : 'na seleção'}!`, 'warning');
        const selectedFiles = document.getElementById('selected-files');
        if (selectedFiles && sourceLabel === 'pasta') {
            selectedFiles.innerHTML = 'Nenhum .session encontrado na pasta';
        }
        return;
    }
    
    // Aviso sobre o processo
    const importDelay = files.length > 300 ? 1.5 : (files.length > 100 ? 0.8 : 0);
    const estimatedMinutes = Math.max(1, Math.ceil((files.length * (2 + importDelay)) / 60));
    const confirmImport = window.confirm(
        `📋 IMPORTAÇÃO COM VALIDAÇÃO\n\n` +
        `Você está importando ${files.length} sessão(ões) via ${sourceLabel}.\n\n` +
        `O sistema irá:\n` +
        `✅ Importar os arquivos .session\n` +
        `🔐 Validar automaticamente\n` +
        `🟢 Vincular só as sessões aprovadas\n\n` +
        `Limite atual: até 500 sessões por vez.\n` +
        `Em lote grande, o sistema usa delay maior para reduzir falhas por excesso de validações.\n\n` +
        `Tempo estimado: pode levar ${estimatedMinutes}+ minuto(s), dependendo do Telegram e do PC.\n` +
        `A importação roda em segundo plano e atualiza o painel em tempo real.\n\n` +
        `Deseja continuar?`
    );
    
    if (!confirmImport) {
        return;
    }
    
    const logsDiv = document.getElementById('import-logs');
    logsDiv.style.display = 'block';
    logsDiv.innerHTML = '';

    const selectedFiles = document.getElementById('selected-files');
    if (selectedFiles) {
        const firstNames = files.slice(0, 2).map(file => file.webkitRelativePath || file.name).join(', ');
        selectedFiles.innerHTML = `<i class="fas fa-folder-tree"></i> ${files.length} .session de ${sourceLabel}: ${firstNames}${files.length > 2 ? ` +${files.length - 2}` : ''}`;
    }
    
    addLog('import-logs', `📦 Iniciando importação de ${files.length} sessão(ões)...`, 'info');
    if (sourceLabel === 'pasta') {
        const rootFolder = files[0]?.webkitRelativePath?.split('/')?.[0];
        addLog('import-logs', `📁 Pasta selecionada: ${rootFolder || 'pasta local'}`, 'info');
    }
    addLog('import-logs', `🔐 Validação automática ligada`, 'info');
    addLog('import-logs', `🟢 Só sessões aprovadas serão vinculadas`, 'success');
    addLog('import-logs', `⏳ Importação grande pode demorar ${estimatedMinutes}+ minuto(s). O painel será atualizado em tempo real.`, 'warning');
    if (files.length > 100) {
        addLog('import-logs', `🐢 Delay automático ativado: ${importDelay}s entre validações.`, 'warning');
    }
    
    // Mostra notificação persistente
    showNotification(`Importando ${files.length} sessão(ões)... Acompanhe em tempo real no painel.`, 'info', 8000);
    
    const formData = new FormData();
    for (let file of files) {
        formData.append('sessions', file);
    }
    
    try {
        // A rota responde rápido e deixa a validação rodando em segundo plano.
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);
        
        const response = await fetch('/api/sessions/import', {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        // Verifica se a resposta é JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Resposta não é JSON:', text);
            
            addLog('import-logs', `❌ ERRO: Servidor retornou erro ao processar`, 'error');
            addLog('import-logs', `💡 Possíveis causas:`, 'warning');
            addLog('import-logs', `   • Timeout do servidor (muitas sessões)`, 'warning');
            addLog('import-logs', `   • Erro interno do servidor`, 'warning');
            
            showNotification(
                `Erro ao importar: timeout/servidor ocupado. Tente dividir em lotes menores, tipo 200-300 por vez. O limite máximo é 500.`,
                'error',
                10000
            );
            return;
        }
        
        const data = await response.json();
        
        if (data.success && data.started) {
            addLog('import-logs', `🚀 Importação iniciada em segundo plano.`, 'success');
            addLog('import-logs', `📊 Processo: ${data.total} sessão(ões), delay ${data.delay_between}s.`, 'info');
            showStatus('import-status', `⏳ Importação em andamento: ${data.total} sessão(ões)`, 'info');
            loadProcesses();
            loadDashboard();
            if (sourceInput) sourceInput.value = '';
        } else if (data.success) {
            addLog('import-logs', `✅ Importação concluída!`, 'success');
            addLog('import-logs', `📊 Total: ${data.total}`, 'info');
            addLog('import-logs', `✅ Aprovadas e vinculadas: ${data.active}`, 'success');
            
            if (data.inactive > 0) {
                addLog('import-logs', `⏭️ Recusadas/puladas: ${data.inactive}`, 'warning');
            }
            
            showNotification(`${data.active} sessão(ões) aprovada(s) e pronta(s) para uso!`, 'success', 8000);
            showStatus('import-status', `✅ ${data.active} sessão(ões) validada(s) e vinculada(s)!`, 'success');
            loadSessions();
            loadDashboard();
            
            // Limpar input
            if (sourceInput) sourceInput.value = '';
        } else {
            addLog('import-logs', `❌ Erro: ${data.error}`, 'error');
            showNotification(`Erro ao importar sessões: ${data.error}`, 'error');
            showStatus('import-status', `❌ Erro ao importar sessões`, 'error');
        }
    } catch (error) {
        addLog('import-logs', `❌ Erro: ${error.message}`, 'error');
        showNotification(`Erro ao importar: ${error.message}`, 'error');
        showStatus('import-status', `❌ Erro ao importar sessões`, 'error');
    }
}

// Sessões
async function loadSessions() {
    const response = await fetch(`/api/sessions?_=${Date.now()}`, {cache: 'no-store'});
    const data = await response.json();
    currentSessions = data.sessions || [];
    
    // Pega informações de uso das sessões
    const locksResponse = await fetch('/api/session/locks');
    const locksData = await locksResponse.json();
    const locks = locksData.locks || {};
    
    // Pega sessões bloqueadas/reservadas por tarefas
    const tasksResponse = await fetch('/api/tasks/blocked-sessions');
    const blockedData = await tasksResponse.json();
    const blockedSessions = blockedData.blocked_sessions || [];
    const reservedSessions = blockedData.reserved_sessions || blockedSessions;
    const sessionTaskMap = blockedData.session_task_map || {};
    
    const list = document.getElementById('sessions-list');
    list.innerHTML = '';
    
    // Controles de seleção em massa
    const selectionControls = document.getElementById('session-selection-controls');
    
    if (currentSessions.length === 0) {
        // Esconde controles de seleção se não houver sessões
        if (selectionControls && selectionControls.querySelector('#selected-count')) {
            selectionControls.style.display = 'none';
        }
        
        list.innerHTML = `
            <div style="text-align: center; padding: 60px 20px; background: rgba(15, 23, 42, 0.5); border-radius: 18px; border: 2px dashed rgba(59, 130, 246, 0.3);">
                <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.5;">📱</div>
                <h3 style="color: #93C5FD; margin-bottom: 10px;">Nenhuma sessão cadastrada</h3>
                <p style="color: #94a3b8; margin-bottom: 30px;">
                    Importe suas sessões do Telegram para começar a usar o sistema
                </p>
                <div style="display: flex; flex-direction: column; gap: 15px; max-width: 500px; margin: 0 auto; text-align: left;">
                    <div style="padding: 15px; background: rgba(59, 130, 246, 0.1); border-radius: 12px; border-left: 3px solid #3B82F6;">
                        <div style="color: #93C5FD; font-weight: 600; margin-bottom: 5px;">
                            📁 Opção 1: Importar Arquivos
                        </div>
                        <div style="color: #94a3b8; font-size: 0.9em;">
                            Clique em "Selecionar Arquivos" acima e escolha seus arquivos .session
                        </div>
                    </div>
                    <div style="padding: 15px; background: rgba(245, 158, 11, 0.1); border-radius: 12px; border-left: 3px solid #F59E0B;">
                        <div style="color: #FCD34D; font-weight: 600; margin-bottom: 5px;">
                            🔍 Opção 2: Escanear Pasta
                        </div>
                        <div style="color: #94a3b8; font-size: 0.9em;">
                            Se já copiou os arquivos .session para a pasta, clique em "Escanear Pasta"
                        </div>
                    </div>
                    <div style="padding: 15px; background: rgba(16, 185, 129, 0.1); border-radius: 12px; border-left: 3px solid #10B981;">
                        <div style="color: #6EE7B7; font-weight: 600; margin-bottom: 5px;">
                            ➕ Opção 3: Criar Nova
                        </div>
                        <div style="color: #94a3b8; font-size: 0.9em;">
                            Clique em "Criar via Telefone" no topo para criar uma nova sessão
                        </div>
                    </div>
                </div>
            </div>
        `;
        renderSessionDetail(null);
        return;
    }
    
    // Mostra controles de seleção se houver sessões
    if (selectionControls && selectionControls.querySelector('#selected-count')) {
        selectionControls.style.display = 'block';
    }
    
    if (selectedSessionIndex === null || !currentSessions[selectedSessionIndex]) {
        selectedSessionIndex = 0;
    }
    
    updateSessionFilterCounts(currentSessions, locks, reservedSessions);
    const visibleSessions = currentSessions
        .map((session, index) => ({session, index}))
        .filter(({session, index}) => currentSessionFilter === 'all' || getSessionFilterKey(session, index, locks, reservedSessions) === currentSessionFilter);

    if (visibleSessions.length === 0) {
        list.innerHTML = `
            <div style="text-align: center; padding: 38px 20px; background: rgba(15, 23, 42, 0.5); border-radius: 12px; border: 1px dashed rgba(148, 163, 184, 0.28);">
                <div style="font-size: 34px; margin-bottom: 12px; color: #94a3b8;"><i class="fas fa-filter"></i></div>
                <h3 style="color: #e2e8f0; margin-bottom: 8px;">Nenhuma sessão neste status</h3>
                <p style="color: #94a3b8;">Troque o filtro acima para ver outras sessões cadastradas.</p>
            </div>
        `;
        renderSessionDetail(null);
        return;
    }

    if (!visibleSessions.some(({index}) => index === selectedSessionIndex)) {
        selectedSessionIndex = visibleSessions[0].index;
    }

    visibleSessions.forEach(({session, index}) => {
        let status = 'active';
        let statusText = 'Conectada';
        let statusColor = '#10b981';
        let statusIcon = '🟢';
        let statusDetail = 'Pronta para uso';
        let floodInfo = '';
        let usageInfo = '';
        
        // Verifica se está corrompida
        if (session.status === 'corrupted') {
            status = 'corrupted';
            statusText = 'Corrompida';
            statusColor = '#dc2626';
            statusIcon = '⚠️';
            statusDetail = 'Recrie ou valide a sessão';
            floodInfo = `
                <div style="margin-top: 8px; padding: 8px; background: rgba(220, 38, 38, 0.1); border-radius: 8px; border-left: 3px solid #dc2626;">
                    <div style="color: #f87171; font-size: 13px; font-weight: 600;">
                        ⚠️ Sessão incompatível (versão antiga do Telethon)
                    </div>
                    <div style="color: #fca5a5; font-size: 12px; margin-top: 4px;">
                        Esta sessão não pode ser usada. Recrie usando o sistema de criação de sessões.
                    </div>
                </div>
            `;
        }
        // Verifica se está inativa
        else if (!session.active) {
            status = 'inactive';
            statusText = session.status === 'invalid' ? 'Inválida' : 'Inativa';
            statusColor = '#ef4444';
            statusIcon = '🔴';
            statusDetail = 'Desativada no painel';
        } 
        // Verifica se está em FLOOD
        else if (session.status === 'flood' || session.flood_info) {
            status = 'flood';
            statusText = 'Flood';
            statusColor = '#f59e0b';
            statusIcon = '🟡';
            const info = session.flood_info || {};
            const advice = getFloodAdvice(info);
            statusDetail = advice.title;
            floodInfo = `
                <div style="margin-top: 8px; padding: 8px; background: rgba(245, 158, 11, 0.1); border-radius: 8px; border-left: 3px solid #f59e0b;">
                    <div style="color: #fbbf24; font-size: 13px; font-weight: 600;">
                        ⚠️ Sessão marcada como FLOOD / QUARENTENA
                    </div>
                    <div style="color: #fcd34d; font-size: 12px; margin-top: 4px;">
                        ⏳ ${advice.title} · ${advice.detail}
                    </div>
                    <div style="color: #fcd34d; font-size: 11px; margin-top: 4px; font-style: italic;">
                        💡 ${advice.hint}
                    </div>
                </div>
            `;
        }
        // Verifica se está sendo usada
        else if (locks.warming || locks.extraction || locks.addition || reservedSessions.includes(index)) {
            let usageType = '';
            let usageColor = '#3b82f6';
            let usageIcon = '🔵';
            
            if (blockedSessions.includes(index)) {
                const taskInfo = sessionTaskMap[String(index)] || {};
                usageType = `EM USO NA TAREFA #${taskInfo.task_id || ''}`.trim();
                usageColor = '#8b5cf6';
                usageIcon = '🟣';
                statusDetail = 'Reservada por tarefa';
            } else if (reservedSessions.includes(index)) {
                const taskInfo = sessionTaskMap[String(index)] || {};
                const statusText = taskInfo.status === 'paused' ? 'PAUSADA' : 'RESERVADA';
                usageType = `${statusText} NA TAREFA #${taskInfo.task_id || ''}`.trim();
                usageColor = '#f59e0b';
                usageIcon = '🔒';
                statusDetail = 'Reservada por tarefa';
            } else if (locks.warming) {
                usageType = 'EM AQUECIMENTO';
                usageColor = '#f97316';
                usageIcon = '🔥';
                statusDetail = 'Aquecimento ativo';
            } else if (locks.extraction) {
                usageType = 'EXTRAINDO MEMBROS';
                usageColor = '#06b6d4';
                usageIcon = '📥';
                statusDetail = 'Extração em andamento';
            } else if (locks.addition) {
                usageType = 'ADICIONANDO MEMBROS';
                usageColor = '#10b981';
                usageIcon = '➕';
                statusDetail = 'Adição em andamento';
            }
            
            statusText = 'Em Uso';
            status = 'in-use';
            statusColor = usageColor;
            statusIcon = usageIcon;
            
            usageInfo = `
                <div style="margin-top: 8px; padding: 8px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; border-left: 3px solid ${usageColor};">
                    <div style="color: ${usageColor}; font-size: 13px; font-weight: 600;">
                        ${usageIcon} ${usageType}
                    </div>
                    <div style="color: #94a3b8; font-size: 11px; margin-top: 4px;">
                        🔒 Sessão bloqueada durante o processo
                    </div>
                </div>
            `;
        }
        
        const item = document.createElement('div');
        item.className = `session-item session-${status} ${selectedSessionIndex === index ? 'selected' : ''}`;
        item.dataset.index = String(index);
        item.onclick = () => selectSession(index);
        
        // Monta o nome de exibição
        let displayName = session.session_name; // Fallback para o nome do arquivo
        if (session.first_name || session.name) {
            displayName = session.first_name || session.name;
        } else if (session.username) {
            displayName = `@${session.username}`;
        }
        
        // Monta o telefone
        let phoneDisplay = session.phone || session.session_name;
        const verificationValue = session.last_checked || session.last_validated || session.last_validation || session.updated_at || session.last_used;
        const detailLine = verificationValue
            ? `Ultima verificacao: ${escapeHtml(verificationValue)}`
            : 'A conta esta livre para uso';
        const statusClass = status === 'active' ? 'connected' : status === 'flood' ? 'flood' : status === 'inactive' ? 'inactive' : status === 'in-use' ? 'busy' : 'warning';
        
        item.innerHTML = `
            <div class="session-row">
                <div class="session-code-cell">
                    <input type="checkbox" class="session-checkbox" data-index="${index}" onclick="event.stopPropagation()" onchange="updateSelectedCount()" title="Selecionar conta">
                    <span>${index + 1}</span>
                </div>
                <div class="session-phone-cell">${escapeHtml(phoneDisplay)}</div>
                <div class="session-status-cell ${statusClass}">
                    <span class="status-led"></span>
                    <strong>${escapeHtml(statusText)}</strong>
                </div>
                <div class="session-name-cell">${escapeHtml(displayName)}</div>
                <div class="session-details-cell">
                    <strong>${escapeHtml(statusDetail)}</strong>
                    <span><span class="detail-led"></span>${detailLine}</span>
                </div>
                <div class="session-actions">
                    <button class="btn btn-warning" onclick="event.stopPropagation(); validateSession('${session.session_name}', this)" title="Verificar conta">
                        <i class="fas fa-check-circle"></i>
                    </button>
                    <button class="btn btn-primary" onclick="event.stopPropagation(); toggleSession(${index})" title="${session.active ? 'Pausar conta' : 'Liberar conta'}">
                        <i class="fas fa-power-off"></i>
                    </button>
                    <button class="btn btn-danger" onclick="event.stopPropagation(); removeSession(${index})" title="Remover conta">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
        list.appendChild(item);
    });
    
    // Atualiza o contador inicial
    updateSelectedCount();
    renderSessionDetail(selectedSessionIndex);
}

function getSessionFilterKey(session, index, locks = {}, blockedSessions = []) {
    const rawStatus = String(session.status || '').toLowerCase();

    if (rawStatus.includes('ban')) return 'banned';
    if (rawStatus === 'flood' || session.flood_info) return 'flood';
    if (!session.active || rawStatus === 'invalid' || rawStatus === 'corrupted') return 'paused';
    if (locks.warming) return 'warming';
    if (blockedSessions.includes(index) || locks.extraction || locks.addition) return 'in_use';

    return 'active';
}

function updateSessionFilterCounts(sessions, locks = {}, blockedSessions = []) {
    const counts = {
        all: sessions.length,
        active: 0,
        in_use: 0,
        warming: 0,
        paused: 0,
        flood: 0,
        banned: 0
    };

    sessions.forEach((session, index) => {
        const key = getSessionFilterKey(session, index, locks, blockedSessions);
        if (counts[key] !== undefined) counts[key] += 1;
    });

    Object.entries(counts).forEach(([key, value]) => {
        const counter = document.getElementById(`session-count-${key}`);
        if (counter) counter.textContent = value;
    });

    document.querySelectorAll('.session-status-tab').forEach((tab) => {
        tab.classList.toggle('active', tab.dataset.sessionFilter === currentSessionFilter);
    });
}

function setSessionFilter(filter) {
    currentSessionFilter = filter;
    selectedSessionIndex = null;
    loadSessions();
}

function getSessionViewState(session, index) {
    let status = 'active';
    let text = 'Disponível';
    let color = '#10b981';
    let icon = '●';

    if (session.status === 'corrupted') {
        status = 'corrupted';
        text = 'Corrompida';
        color = '#dc2626';
        icon = '!';
    } else if (!session.active) {
        status = 'inactive';
        text = session.status === 'invalid' ? 'Inválida' : 'Inativa';
        color = '#ef4444';
        icon = '●';
    } else if (session.status === 'flood' || session.flood_info) {
        status = 'flood';
        text = 'Flood / Quarentena';
        color = '#f59e0b';
        icon = '●';
    }

    return {status, text, color, icon};
}

function selectSession(index) {
    selectedSessionIndex = index;
    document.querySelectorAll('.session-item').forEach((item) => {
        item.classList.toggle('selected', Number(item.dataset.index) === index);
    });
    renderSessionDetail(index);
}

function renderSessionDetail(index) {
    const panel = document.getElementById('session-detail-panel');
    if (!panel) return;

    const session = index !== null ? currentSessions[index] : null;
    if (!session) {
        panel.innerHTML = `
            <div class="session-detail-empty">
                <i class="fas fa-mouse-pointer"></i>
                <h3>Selecione uma sessão</h3>
                <p>Os detalhes, status e ações rápidas aparecem aqui.</p>
            </div>
        `;
        return;
    }

    const state = getSessionViewState(session, index);
    const displayName = session.first_name || session.username || session.session_name;
    const username = session.username ? `@${session.username}` : 'Sem username';
    const phone = session.phone || session.session_name;
    const floodAdvice = getFloodAdvice(session.flood_info || {});
    const floodHtml = (session.status === 'flood' || session.flood_info) ? `
        <div class="session-detail-alert">
            ${floodAdvice.title}
            <span>${floodAdvice.detail}. ${floodAdvice.hint}</span>
        </div>
    ` : '';

    panel.innerHTML = `
        <div class="session-detail-header">
            <div>
                <span class="session-detail-kicker">Sessão selecionada</span>
                <h3>${displayName}</h3>
                <p>${username}</p>
            </div>
            <span class="session-detail-status" style="color:${state.color}; border-color:${state.color}; background:${state.color}18;">
                ${state.icon} ${state.text}
            </span>
        </div>

        <div class="session-detail-grid">
            <div class="session-detail-stat">
                <span>Telefone</span>
                <strong>${phone}</strong>
            </div>
            <div class="session-detail-stat">
                <span>Arquivo</span>
                <strong>${session.session_name}</strong>
            </div>
            <div class="session-detail-stat">
                <span>User ID</span>
                <strong>${session.user_id || 'Não informado'}</strong>
            </div>
            <div class="session-detail-stat">
                <span>Indice</span>
                <strong>#${index + 1}</strong>
            </div>
        </div>

        ${floodHtml}

        <div class="session-detail-actions">
            <button class="btn btn-warning" onclick="validateSession('${session.session_name}', this)" style="background:#7f1d1d;">
                <i class="fas fa-check-circle"></i> Validar
            </button>
            <button class="btn btn-primary" onclick="toggleSession(${index})">
                <i class="fas fa-power-off"></i> ${session.active ? 'Desativar' : 'Ativar'}
            </button>
            <button class="btn btn-danger" onclick="removeSession(${index})">
                <i class="fas fa-trash"></i> Remover
            </button>
        </div>

        <div class="session-detail-notes">
            <h4>Leitura rápida</h4>
            <p>${state.text === 'Disponível' ? 'Pronta para ser usada em uma nova tarefa.' : 'Revise o status antes de usar esta sessão em tarefas.'}</p>
        </div>
    `;
}

function updateSelectedCount() {
    const checkboxes = document.querySelectorAll('.session-checkbox:checked');
    const countElement = document.getElementById('selected-count');
    
    if (countElement) {
        const count = checkboxes.length;
        countElement.textContent = count === 0 ? '0 selecionadas' : 
                                   count === 1 ? '1 selecionada' : 
                                   `${count} selecionadas`;
    }

    document.querySelectorAll('.session-selection-action').forEach((button) => {
        button.style.display = checkboxes.length > 0 ? 'inline-flex' : 'none';
    });
}

function addSession() {
    const phone = document.getElementById('phone').value;
    if (!phone) {
        showNotification('Digite um número de telefone!', 'warning');
        return;
    }
    
    socket.emit('add_session', {phone});
}

async function toggleSession(index) {
    await fetch(`/api/sessions/toggle/${index}`, {method: 'POST'});
    loadSessions();
}

async function removeSession(index) {
    if (!confirm('Confirma remoção?')) return;
    await fetch(`/api/sessions/remove/${index}`, {method: 'DELETE'});
    loadSessions();
}

function selectAllSessions() {
    const checkboxes = document.querySelectorAll('.session-checkbox');
    checkboxes.forEach(cb => cb.checked = true);
    updateSelectedCount();
    showNotification(`${checkboxes.length} sessões selecionadas`, 'info', 3000);
}

function deselectAllSessions() {
    const checkboxes = document.querySelectorAll('.session-checkbox');
    checkboxes.forEach(cb => cb.checked = false);
    updateSelectedCount();
    showNotification('Todas as sessões desmarcadas', 'info', 3000);
}

async function removeSelectedSessions() {
    const checkboxes = document.querySelectorAll('.session-checkbox:checked');
    
    if (checkboxes.length === 0) {
        showNotification('Nenhuma sessão selecionada!', 'warning');
        return;
    }
    
    const confirmMessage = `⚠️ ATENÇÃO: Você está prestes a remover ${checkboxes.length} sessão(ões)!\n\n` +
                          `Esta ação NÃO PODE ser desfeita!\n\n` +
                          `Os arquivos .session serão DELETADOS permanentemente.\n\n` +
                          `Tem certeza que deseja continuar?`;
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    showNotification(`Removendo ${checkboxes.length} sessão(ões)...`, 'warning', 0);
    
    // Pega os índices das sessões selecionadas
    const indices = Array.from(checkboxes).map(cb => parseInt(cb.dataset.index));
    
    try {
        // Remove em ordem reversa para não bagunçar os índices
        indices.sort((a, b) => b - a);
        
        for (const index of indices) {
            await fetch(`/api/sessions/remove/${index}`, {method: 'DELETE'});
        }
        
        showNotification(`✅ ${checkboxes.length} sessão(ões) removida(s) com sucesso!`, 'success', 5000);
        loadSessions();
    } catch (error) {
        console.error('Erro ao remover sessões:', error);
        showNotification('❌ Erro ao remover sessões', 'error');
    }
}

async function removeAllSessions() {
    const response = await fetch('/api/sessions');
    const data = await response.json();
    const totalSessions = data.sessions.length;
    
    if (totalSessions === 0) {
        showNotification('Nenhuma sessão para remover!', 'warning');
        return;
    }
    
    const confirmMessage = `⚠️ ATENÇÃO: Você está prestes a remover TODAS as ${totalSessions} sessões!\n\n` +
                          `Esta ação NÃO PODE ser desfeita!\n\n` +
                          `Os arquivos .session serão DELETADOS permanentemente.\n\n` +
                          `Tem certeza absoluta que deseja continuar?`;
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    // Confirmação dupla para segurança
    const doubleConfirm = confirm(
        `🚨 ÚLTIMA CONFIRMAÇÃO!\n\n` +
        `Deletar ${totalSessions} sessões permanentemente?\n\n` +
        `Digite OK para confirmar ou Cancelar para voltar.`
    );
    
    if (!doubleConfirm) {
        return;
    }
    
    showNotification('Removendo todas as sessões...', 'warning', 0);
    
    try {
        const deleteResponse = await fetch('/api/sessions/remove-all', {
            method: 'DELETE'
        });
        
        const result = await deleteResponse.json();
        
        if (result.success) {
            showNotification(`✅ ${result.removed} sessão(ões) removida(s) com sucesso!`, 'success', 5000);
            loadSessions();
        } else {
            showNotification(`Erro: ${result.error}`, 'error');
        }
    } catch (error) {
        showNotification(`Erro ao remover sessões: ${error.message}`, 'error');
    }
}

let extractSessionRows = [];

// Extração
async function loadSessionsForExtract() {
    const response = await fetch('/api/sessions');
    const data = await response.json();
    
    // Na extração, tarefas não bloqueiam sessão; usamos esses dados só para rotular.
    const tasksResponse = await fetch('/api/tasks/blocked-sessions');
    const blockedData = await tasksResponse.json();
    const blockedSessions = blockedData.blocked_sessions || [];
    const reservedSessions = blockedData.reserved_sessions || blockedSessions;
    const sessionTaskMap = blockedData.session_task_map || {};
    
    const select = document.getElementById('extract-session');
    select.innerHTML = '<option value="">Selecione...</option>';
    extractSessionRows = [];
    
    data.sessions
        .map((session, originalIndex) => ({session, originalIndex}))
        .filter(({session}) => session.active)
        .forEach(({session, originalIndex}) => {
        const taskInfo = sessionTaskMap[String(originalIndex)] || null;
        const isBlocked = blockedSessions.includes(originalIndex);
        const isReserved = reservedSessions.includes(originalIndex);
        const isFlood = session.status === 'flood';
        const disabled = false;
        
        const displayName = session.first_name || session.name || session.phone || session.session_name || `Sessão ${originalIndex + 1}`;
        const username = session.username ? `@${session.username}` : (session.phone || session.session_name || '');
        let label = username ? `${displayName} (${username})` : displayName;
        if (isBlocked) {
            label += ` · EM TAREFA #${taskInfo?.task_id || ''}`.trim();
        } else if (isReserved) {
            const statusText = taskInfo?.status === 'paused' ? 'PAUSADA' : 'RESERVADA';
            label += ` · ${statusText} NA TAREFA #${taskInfo?.task_id || ''}`.trim();
        } else if (isFlood) {
            label += ' · FLOOD';
        }
        
        const option = document.createElement('option');
        option.value = originalIndex;
        option.textContent = label;
        option.disabled = disabled;
        select.appendChild(option);

        extractSessionRows.push({
            index: originalIndex,
            displayName,
            username,
            label,
            disabled,
            isBlocked,
            isReserved,
            inTask: isBlocked || isReserved,
            isFlood,
            taskInfo
        });
    });

    renderExtractSessionList();
}

function renderExtractSessionList(filterText = '') {
    const list = document.getElementById('extract-session-list');
    const select = document.getElementById('extract-session');
    const counter = document.getElementById('extract-session-counter');
    if (!list || !select) return;

    const query = String(filterText || '').trim().toLowerCase();
    const visibleRows = extractSessionRows.filter(row => !query || row.label.toLowerCase().includes(query));

    if (!visibleRows.length) {
        list.innerHTML = '<p style="color:#94a3b8;margin:0;">Nenhuma sessão encontrada.</p>';
    } else {
        list.innerHTML = visibleRows.map(row => {
            const selected = String(select.value) === String(row.index);
            let status = 'Livre';
            if (row.isBlocked) status = `Em tarefa #${row.taskInfo?.task_id || ''}`.trim();
            else if (row.isReserved) status = `${row.taskInfo?.status === 'paused' ? 'Tarefa pausada' : 'Reservada'} #${row.taskInfo?.task_id || ''}`.trim();
            else if (row.isFlood) status = 'Flood liberado';

            return `
                <div class="service-session-option ${selected ? 'selected' : ''} ${row.disabled ? 'disabled' : ''} ${row.inTask && !row.disabled ? 'extract-in-task' : ''}"
                     onclick="selectExtractSession('${row.index}')"
                     data-session-search="${escapeHtml(row.label.toLowerCase())}">
                    <input type="radio" name="extract-session-radio" value="${row.index}" ${selected ? 'checked' : ''} ${row.disabled ? 'disabled' : ''} onchange="selectExtractSession('${row.index}')">
                    <div>
                        <strong>${escapeHtml(row.displayName)}</strong>
                        <small>${escapeHtml(row.username || '')}</small>
                    </div>
                    <span class="service-session-status">${escapeHtml(status)}</span>
                </div>
            `;
        }).join('');
    }

    const selectedRow = extractSessionRows.find(row => String(row.index) === String(select.value));
    if (counter) {
        counter.textContent = selectedRow
            ? `1 selecionada: ${selectedRow.displayName}`
            : `${extractSessionRows.filter(row => !row.disabled).length} disponível(is) para extração`;
    }
}

function selectExtractSession(index) {
    const row = extractSessionRows.find(item => String(item.index) === String(index));
    if (!row) return;
    if (row.disabled && !row.inTask) return;
    const select = document.getElementById('extract-session');
    if (select) select.value = String(index);
    renderExtractSessionList(document.getElementById('extract-session-search')?.value || '');
}

function filterExtractSessionList() {
    renderExtractSessionList(document.getElementById('extract-session-search')?.value || '');
}

function extractMembers() {
    extractMembersList();
}

function extractMembersList() {
    const sessionIndex = parseInt(document.getElementById('extract-session').value);
    const linksText = document.getElementById('extract-group-list').value || '';
    const groupLinks = linksText
        .split(/\r?\n/)
        .map(link => link.trim())
        .filter(Boolean);
    const filters = {
        active_7d: document.getElementById('filter-active-7d')?.checked || false,
        active_3d: document.getElementById('filter-active-3d')?.checked || false,
        online: document.getElementById('filter-online')?.checked || false,
        photo: document.getElementById('filter-photo')?.checked || false,
        username: document.getElementById('filter-username')?.checked || false,
        phone: document.getElementById('filter-phone')?.checked || false,
        private_id_mode: document.getElementById('extract-private-id-mode')?.checked || false
    };

    if (isNaN(sessionIndex) || groupLinks.length === 0) {
        showNotification('Selecione a sessão e informe pelo menos um link na lista.', 'warning');
        return;
    }

    if (groupLinks.length > 20) {
        showNotification('Limite máximo: 20 links por extração em lista.', 'warning');
        return;
    }

    document.getElementById('extract-logs').innerHTML = '';
    showNotification(
        groupLinks.length === 1
            ? 'Iniciando extração do grupo informado...'
            : `Iniciando extração em lista: ${groupLinks.length} grupo(s)...`,
        'info',
        4000
    );

    socket.emit('extract_members_list', {
        session_index: sessionIndex,
        group_links: groupLinks,
        filters
    });
}

// Download exportação
function downloadExport() {
    window.location.href = '/api/members/export';
}

// Listar arquivos de lotes
async function listBatchFiles() {
    try {
        const response = await fetch('/api/members/batches');
        const data = await response.json();
        
        if (data.success && ((data.extractions && data.extractions.length > 0) || (data.list_extractions && data.list_extractions.length > 0))) {
            const container = document.getElementById('batch-files-list');
            const content = document.getElementById('batch-files-content');
            
            let html = '';
            
            (data.list_extractions || []).forEach((extraction, idx) => {
                html += `
                    <div class="card" style="margin-bottom: 15px; background: rgba(16, 185, 129, 0.08);">
                        <h4 style="color: #6ee7b7; margin-bottom: 10px;">
                            <i class="fas fa-list"></i> Extração por lista ${idx + 1}
                        </h4>
                        <p style="color: #94a3b8; margin-bottom: 15px;">
                            ${extraction.total_groups} grupo(s) · ${extraction.total_members || 0} membros
                        </p>
                        ${extraction.index_file ? `
                            <button class="btn btn-primary" onclick="downloadBatchFile('${extraction.index_file}')" style="width: 100%; margin-bottom: 12px;">
                                <i class="fas fa-file-alt"></i> Baixar índice (${extraction.index_file})
                            </button>
                        ` : ''}
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px;">
                            ${(extraction.files || []).map(file => `
                                <button class="btn btn-info" onclick="downloadBatchFile('${file.filename}')" style="font-size: 12px;">
                                    <i class="fas fa-file-download"></i> ${file.group_name || file.filename}
                                    <br><small>${file.total_members || 0} membros · ${file.size_mb || 0} MB</small>
                                </button>
                            `).join('')}
                        </div>
                    </div>
                `;
            });

            (data.extractions || []).forEach((extraction, idx) => {
                const timestamp = extraction.timestamp;
                const date = timestamp.split('_')[0];
                const time = timestamp.split('_')[1];
                const formattedDate = `${date.substring(6,8)}/${date.substring(4,6)}/${date.substring(0,4)}`;
                const formattedTime = `${time.substring(0,2)}:${time.substring(2,4)}:${time.substring(4,6)}`;
                
                html += `
                    <div class="card" style="margin-bottom: 15px; background: rgba(30, 41, 59, 0.5);">
                        <h4 style="color: #3b82f6; margin-bottom: 10px;">
                            <i class="fas fa-calendar"></i> Extração ${idx + 1} - ${formattedDate} às ${formattedTime}
                        </h4>
                        <p style="color: #94a3b8; margin-bottom: 15px;">
                            <i class="fas fa-layer-group"></i> ${extraction.batches.length} lotes criados
                        </p>
                `;
                
                // Arquivo índice
                if (extraction.index_file) {
                    html += `
                        <div style="margin-bottom: 10px;">
                            <button class="btn btn-primary" onclick="downloadBatchFile('${extraction.index_file}')" style="width: 100%;">
                                <i class="fas fa-file-alt"></i> Baixar Arquivo Índice (${extraction.index_file})
                            </button>
                        </div>
                    `;
                }
                
                // Botão para baixar todos
                html += `
                    <div style="margin-bottom: 15px;">
                        <button class="btn btn-success" onclick="downloadAllBatches('${timestamp}')" style="width: 100%;">
                            <i class="fas fa-download"></i> Baixar Todos os Lotes (${extraction.batches.length} arquivos)
                        </button>
                    </div>
                `;
                
                // Lista de lotes individuais
                html += `<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px;">`;
                
                extraction.batches.forEach(batch => {
                    html += `
                        <button class="btn btn-info" onclick="downloadBatchFile('${batch.filename}')" style="font-size: 12px;">
                            <i class="fas fa-file-download"></i> Lote ${batch.batch_number}/${batch.total_batches}
                            <br><small>(${batch.size_mb} MB)</small>
                        </button>
                    `;
                });
                
                html += `</div></div>`;
            });
            
            content.innerHTML = html;
            container.style.display = 'block';
            
            showNotification(`${data.total} extração(ões) com lotes encontrada(s)`, 'success');
        } else {
            showNotification('Nenhum arquivo de lote encontrado. Extraia membros com divisão em lotes primeiro.', 'warning');
        }
    } catch (error) {
        showNotification(`Erro ao listar lotes: ${error.message}`, 'error');
    }
}

// Baixar arquivo de lote específico
function downloadBatchFile(filename) {
    window.location.href = `/api/members/batch/${filename}`;
    showNotification(`Baixando: ${filename}`, 'info', 2000);
}

// Baixar todos os lotes de uma extração
async function downloadAllBatches(timestamp) {
    try {
        const response = await fetch('/api/members/batches');
        const data = await response.json();
        
        if (data.success) {
            const extraction = data.extractions.find(e => e.timestamp === timestamp);
            
            if (extraction) {
                showNotification(`Iniciando download de ${extraction.batches.length} arquivos...`, 'info');
                
                // Baixa o índice primeiro
                if (extraction.index_file) {
                    downloadBatchFile(extraction.index_file);
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
                
                // Baixa cada lote com delay
                for (const batch of extraction.batches) {
                    downloadBatchFile(batch.filename);
                    await new Promise(resolve => setTimeout(resolve, 500)); // Delay de 500ms entre downloads
                }
                
                showNotification(`Download de ${extraction.batches.length} arquivos iniciado!`, 'success');
            }
        }
    } catch (error) {
        showNotification(`Erro ao baixar lotes: ${error.message}`, 'error');
    }
}

// Adição
// Importar membros para adicionar
async function importMembersForAdd() {
    const fileInput = document.getElementById('add-import-file');
    const file = fileInput.files[0];
    
    if (!file) {
        showNotification('Selecione um arquivo JSON!', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/members/import', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(`${data.total} membros importados!`, 'success');
            document.getElementById('add-import-status').innerHTML = `✅ ${data.total} membros importados do grupo: ${data.group_name}`;
            fileInput.value = '';
        } else {
            showNotification(`Erro: ${data.error}`, 'error');
            document.getElementById('add-import-status').innerHTML = `❌ Erro: ${data.error}`;
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
        document.getElementById('add-import-status').innerHTML = `❌ Erro: ${error.message}`;
    }
}

// Importar membros para tarefas
async function importMembersForTasks() {
    const fileInput = document.getElementById('task-import-file');
    const file = fileInput.files[0];
    
    if (!file) {
        showNotification('Selecione um arquivo JSON!', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showNotification('Importando membros...', 'info');
        
        const response = await fetch('/api/members/import', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(`${data.total} membros importados para tarefas!`, 'success');
            document.getElementById('task-import-status').innerHTML = `✅ ${data.total} membros importados do grupo: ${data.group_name}<br>📊 Confirmado: ${data.saved_count} membros salvos no sistema`;
            fileInput.value = '';
        } else {
            showNotification(`Erro: ${data.error}`, 'error');
            document.getElementById('task-import-status').innerHTML = `❌ Erro: ${data.error}`;
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
        document.getElementById('task-import-status').innerHTML = `❌ Erro: ${error.message}`;
    }
}

// Toggle modo de operação
function toggleOperationMode() {
    const mode = document.getElementById('operation-mode').value;
    const loopOptions = document.getElementById('loop-options');
    
    if (mode === 'loop') {
        loopOptions.style.display = 'block';
    } else {
        loopOptions.style.display = 'none';
    }
}

// Carregar sessões ativas na aba de adicionar
async function loadActiveSessions() {
    const response = await fetch('/api/sessions');
    const data = await response.json();
    
    // Pega sessões bloqueadas por tarefas ativas
    const tasksResponse = await fetch('/api/tasks/blocked-sessions');
    const blockedData = await tasksResponse.json();
    const blockedSessions = blockedData.blocked_sessions || [];
    
    const activeSessions = data.sessions.filter(s => s.active);
    const container = document.getElementById('sessions-checkboxes');
    
    if (activeSessions.length === 0) {
        container.innerHTML = '<p style="color: #fca5a5;">⚠️ Nenhuma sessão ativa disponível</p>';
        return;
    }
    
    container.innerHTML = activeSessions.map((s, index) => {
        const isBlocked = blockedSessions.includes(index);
        const isFlood = s.status === 'flood';
        const disabled = isBlocked || isFlood;
        const opacity = disabled ? '0.5' : '1';
        const cursor = disabled ? 'not-allowed' : 'pointer';
        
        let statusBadge = '';
        if (isBlocked) {
            statusBadge = '<span style="color: #f59e0b; font-size: 11px; font-weight: 600;">🔒 EM TAREFA</span>';
        } else if (isFlood) {
            statusBadge = '<span style="color: #ef4444; font-size: 11px; font-weight: 600;">🚫 FLOOD</span>';
        }
        
        return `
        <label style="display: flex; align-items: center; gap: 10px; padding: 10px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; cursor: ${cursor}; transition: all 0.2s; opacity: ${opacity};" ${!disabled ? `onmouseover="this.style.background='rgba(59, 130, 246, 0.2)'" onmouseout="this.style.background='rgba(59, 130, 246, 0.1)'"` : ''}>
            <input type="checkbox" class="session-checkbox" value="${index}" ${disabled ? 'disabled' : 'checked'} style="width: 18px; height: 18px; cursor: ${cursor};">
            <div style="flex: 1;">
                <div style="color: #e2e8f0; font-weight: 600;">${s.first_name} ${statusBadge}</div>
                <div style="color: #94a3b8; font-size: 12px;">@${s.username} • ${s.phone}</div>
            </div>
        </label>
    `;
    }).join('');
    
    // Marca "Selecionar Todas" como checked se houver sessões disponíveis
    const availableSessions = activeSessions.filter((s, i) => !blockedSessions.includes(i) && s.status !== 'flood');
    document.getElementById('select-all-sessions').checked = availableSessions.length > 0;
}

function toggleAllSessions() {
    const selectAll = document.getElementById('select-all-sessions');
    const checkboxes = document.querySelectorAll('.session-checkbox');
    
    checkboxes.forEach(cb => {
        cb.checked = selectAll.checked;
    });
}

let addingProcessActive = false;

function startAddingProcess() {
    const targetGroup = document.getElementById('target-group').value;
    const membersPerSession = parseInt(document.getElementById('members-per-session').value);
    const delayAdds = parseInt(document.getElementById('delay-adds').value);
    const delaySessions = parseInt(document.getElementById('delay-sessions').value);
    const operationMode = document.getElementById('operation-mode').value;
    const delayRounds = parseInt(document.getElementById('delay-rounds').value) || 300;
    
    // Pega sessões selecionadas
    const selectedCheckboxes = document.querySelectorAll('.session-checkbox:checked');
    const selectedIndexes = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));
    
    if (!targetGroup) {
        showNotification('Digite o grupo alvo!', 'warning');
        return;
    }
    
    if (selectedIndexes.length === 0) {
        showNotification('Selecione pelo menos uma sessão!', 'warning');
        return;
    }
    
    document.getElementById('add-logs').innerHTML = '';
    document.getElementById('add-progress').innerHTML = '';
    document.getElementById('stop-btn').style.display = 'inline-flex';
    
    addingProcessActive = true;
    showNotification(`Iniciando processo com ${selectedIndexes.length} sessão(ões)...`, 'info', 3000);
    
    socket.emit('add_members', {
        target_group: targetGroup,
        members_per_session: membersPerSession,
        delay_between_adds: delayAdds,
        delay_between_sessions: delaySessions,
        operation_mode: operationMode,
        delay_between_rounds: delayRounds,
        selected_sessions: selectedIndexes
    });
}

function stopAddingProcess() {
    addingProcessActive = false;
    socket.emit('stop_adding');
    document.getElementById('stop-btn').style.display = 'none';
    addLog('add-logs', '⏹️ Processo interrompido pelo usuário', 'warning');
}

function addMembers() {
    const targetGroup = document.getElementById('target-group').value;
    const membersPerSession = parseInt(document.getElementById('members-per-session').value);
    const delayAdds = parseInt(document.getElementById('delay-adds').value);
    const delaySessions = parseInt(document.getElementById('delay-sessions').value);
    
    if (!targetGroup) {
        showNotification('Digite o grupo alvo!', 'warning');
        return;
    }
    
    document.getElementById('add-logs').innerHTML = '';
    document.getElementById('add-progress').innerHTML = '';
    
    socket.emit('add_members', {
        target_group: targetGroup,
        members_per_session: membersPerSession,
        delay_between_adds: delayAdds,
        delay_between_sessions: delaySessions
    });
}

// Estatísticas
async function loadStats() {
    const response = await fetch(`/api/members/stats?_=${Date.now()}`, {cache: 'no-store'});
    const data = await response.json();
    
    document.getElementById('stat-total').textContent = data.total || 0;
    document.getElementById('stat-added').textContent = data.added || 0;
    document.getElementById('stat-pending').textContent = data.pending || 0;
    const failedEl = document.getElementById('stat-failed');
    const processedEl = document.getElementById('stat-processed');
    const rateEl = document.getElementById('stat-success-rate');
    if (failedEl) failedEl.textContent = data.failed || 0;
    if (processedEl) processedEl.textContent = data.processed || 0;
    if (rateEl) rateEl.textContent = `${data.success_rate || 0}%`;
    
    const sessionsResponse = await fetch(`/api/sessions?_=${Date.now()}`, {cache: 'no-store'});
    const sessionsData = await sessionsResponse.json();
    const activeSessions = sessionsData.sessions.filter(s => s.active).length;
    document.getElementById('stat-sessions').textContent = activeSessions;

    renderStatsTaskBreakdown(data.task_breakdown || []);
}

function renderStatsTaskBreakdown(tasks) {
    const container = document.getElementById('stats-task-breakdown');
    if (!container) return;

    if (!tasks.length) {
        container.innerHTML = '<p style="color:#94a3b8;margin:0;">Nenhuma tarefa registrada ainda.</p>';
        return;
    }

    container.innerHTML = `
        <h3 style="color:#e2e8f0;margin:0 0 12px;">Resumo por tarefa</h3>
        <div style="overflow:auto;border:1px solid rgba(148,163,184,.2);border-radius:8px;">
            <table style="width:100%;border-collapse:collapse;min-width:760px;background:rgba(15,23,42,.65);">
                <thead>
                    <tr style="color:#cbd5e1;background:rgba(30,41,59,.85);">
                        <th style="padding:10px;text-align:left;">Tarefa</th>
                        <th style="padding:10px;text-align:left;">Status</th>
                        <th style="padding:10px;text-align:right;">Meta</th>
                        <th style="padding:10px;text-align:right;">Adicionados</th>
                        <th style="padding:10px;text-align:right;">Falhas</th>
                        <th style="padding:10px;text-align:right;">Processados</th>
                        <th style="padding:10px;text-align:right;">Pendente</th>
                    </tr>
                </thead>
                <tbody>
                    ${tasks.map(task => `
                        <tr style="border-top:1px solid rgba(148,163,184,.16);color:#f8fafc;">
                            <td style="padding:10px;max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(task.group_link || '')}">#${escapeHtml(task.id)} · ${escapeHtml(task.group_link || '')}</td>
                            <td style="padding:10px;">${escapeHtml(task.status || '-')}</td>
                            <td style="padding:10px;text-align:right;">${task.target_members || 0}</td>
                            <td style="padding:10px;text-align:right;color:#22c55e;font-weight:700;">${task.added || 0}</td>
                            <td style="padding:10px;text-align:right;color:#f87171;font-weight:700;">${task.failed || 0}</td>
                            <td style="padding:10px;text-align:right;">${task.processed || 0}</td>
                            <td style="padding:10px;text-align:right;color:#fbbf24;font-weight:700;">${task.pending_goal || 0}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

async function loadDashboard() {
    try {
        const [membersResponse, sessionsResponse, tasksResponse, locksResponse, processesResponse] = await Promise.all([
            fetch('/api/members/stats'),
            fetch(`/api/sessions?_=${Date.now()}`, {cache: 'no-store'}),
            fetch('/api/tasks'),
            fetch('/api/session/locks'),
            fetch('/api/processes')
        ]);

        const members = await membersResponse.json();
        const sessionsData = await sessionsResponse.json();
        const tasksData = await tasksResponse.json();
        const locksData = await locksResponse.json();
        const processesData = await processesResponse.json();

        const sessions = sessionsData.sessions || [];
        const tasks = tasksData.tasks || [];
        const locks = locksData.locks || {};
        renderProcesses(processesData.processes || []);

        const totalSessions = sessions.length;
        const activeSessions = sessions.filter(s => getSessionFilterKey(s) === 'active').length;
        const floodSessions = sessions.filter(s => getSessionFilterKey(s) === 'flood').length;
        const inactiveSessions = sessions.filter(s => getSessionFilterKey(s) === 'paused').length;
        const activeTasks = tasks.filter(t => t.status === 'active').length;
        const runningWork = activeTasks > 0 || locks.extraction || locks.addition || locks.warming;

        setText('dash-total-sessions', totalSessions);
        setText('dash-active-sessions', activeSessions);
        setText('dash-members-added', members.added || 0);
        setText('dash-active-tasks', activeTasks);
        setText('dash-members-total', members.total || 0);
        setText('dash-members-pending', members.pending || 0);
        setText('dash-total-tasks', tasks.length);
        setText('dash-flood-sessions', floodSessions);
        setText('dash-inactive-sessions', inactiveSessions);
        setText('dash-work-status', runningWork ? 'Rodando' : 'Aguardando');
        setText('dash-updated-at', new Date().toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'}));

        const healthText = document.getElementById('dash-health-text');
        if (healthText) {
            if (runningWork) {
                healthText.textContent = 'Existe operação ativa no momento. Acompanhe os logs da aba correspondente.';
            } else if (totalSessions === 0) {
                healthText.textContent = 'Comece importando sessões para liberar as operações do painel.';
            } else {
                healthText.textContent = 'Ambiente pronto para operar. Sessões e dados estão carregados.';
            }
        }
    } catch (error) {
        console.error('Erro ao carregar dashboard:', error);
        const healthText = document.getElementById('dash-health-text');
        if (healthText) healthText.textContent = 'Não consegui carregar os indicadores agora.';
    }
}

async function loadProcesses() {
    try {
        const response = await fetch('/api/processes');
        const data = await response.json();
        if (data.success) renderProcesses(data.processes || []);
    } catch (error) {
        console.error('Erro ao carregar processos:', error);
    }
}

function renderProcesses(processes) {
    const container = document.getElementById('process-list');
    if (!container) return;

    if (!processes.length) {
        container.innerHTML = '<p style="color:#a1a1aa;margin:0;">Nenhum processo em andamento.</p>';
        return;
    }

    container.innerHTML = processes.slice().reverse().map(process => {
        const statusText = {
            running: 'Rodando',
            completed: 'Concluído',
            error: 'Erro'
        }[process.status] || process.status || 'Processo';
        const percent = Math.max(0, Math.min(100, Number(process.percent || 0)));
        const progress = process.total ? `${process.current || 0}/${process.total}` : '--';

        return `
            <div class="process-item" data-process-id="${escapeHtml(process.id)}">
                <div class="process-head">
                    <strong>${escapeHtml(process.title || process.type || 'Processo')}</strong>
                    <span class="process-badge ${escapeHtml(process.status || '')}">${escapeHtml(statusText)}</span>
                </div>
                <div class="process-bar"><div class="process-fill" style="width:${percent}%"></div></div>
                <div class="process-meta">
                    <span>${escapeHtml(process.message || process.detail || '')}</span>
                    <b>${progress} · ${percent}%</b>
                </div>
            </div>
        `;
    }).join('');
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function openDashboardTab(tab) {
    const item = document.querySelector(`.menu-item[data-tab="${tab}"]`);
    if (item) item.click();
}

function openSessionsWithFilter(filter) {
    currentSessionFilter = filter;
    openDashboardTab('sessions');
}

const taskLogsById = {};
const openTaskLogPanels = new Set();

function getTaskLogKey(taskId) {
    return String(taskId || 'geral');
}

function rememberTaskLog(data) {
    const key = getTaskLogKey(data.task_id);
    if (!taskLogsById[key]) taskLogsById[key] = [];
    taskLogsById[key].push({
        message: data.message || '',
        type: data.type || 'info',
        time: data.time || new Date().toLocaleTimeString()
    });
    taskLogsById[key] = taskLogsById[key].slice(-500);
}

function taskLogEntryHtml(entry) {
    const time = entry.time && entry.time.includes('T')
        ? new Date(entry.time).toLocaleTimeString()
        : (entry.time || new Date().toLocaleTimeString());
    return `<div class="log-entry ${entry.type || 'info'}">[${escapeHtml(time)}] ${escapeHtml(entry.message || '')}</div>`;
}

function renderTaskLogBody(taskId) {
    const body = document.getElementById(`task-log-body-${taskId}`);
    if (!body) return;
    const logs = taskLogsById[getTaskLogKey(taskId)] || [];
    body.innerHTML = logs.length
        ? logs.map(taskLogEntryHtml).join('')
        : '<div class="log-entry info">Terminal aguardando eventos desta tarefa.</div>';
    body.scrollTop = body.scrollHeight;
}

function appendTaskLogEntry(taskId, data) {
    const body = document.getElementById(`task-log-body-${taskId}`);
    if (!body) return;
    body.insertAdjacentHTML('beforeend', taskLogEntryHtml({
        message: data.message,
        type: data.type,
        time: data.time || new Date().toLocaleTimeString()
    }));
    body.scrollTop = body.scrollHeight;
}

function toggleTaskLogs(taskId) {
    const panel = document.getElementById(`task-log-panel-${taskId}`);
    if (!panel) return;
    const isHidden = panel.style.display === 'none' || !panel.style.display;
    panel.style.display = isHidden ? 'block' : 'none';
    const key = getTaskLogKey(taskId);
    if (isHidden) {
        openTaskLogPanels.add(key);
        renderTaskLogBody(taskId);
    } else {
        openTaskLogPanels.delete(key);
    }
}

// Socket events - LOGS SEPARADOS POR ABA
socket.on('extract_log', (data) => {
    console.log('[EXTRACT LOG]', data.message);
    addLog('extract-logs', data.message, data.type);
});

socket.on('add_log', (data) => {
    console.log('[ADD LOG]', data.message);
    addLog('add-logs', data.message, data.type);
});

socket.on('task_log', (data) => {
    console.log('[TASK LOG]', data.message);
    if (data.task_id) {
        rememberTaskLog(data);
        appendTaskLogEntry(data.task_id, data);
    } else if (document.getElementById('task-logs')) {
        addLog('task-logs', data.message, data.type);
    }
    
    // Mostra notificação para logs importantes
    if (data.type === 'success' && data.message.includes('Adicionado:')) {
        // Atualiza tarefas quando adiciona membro
        loadTasks();
    } else if (data.type === 'success' && data.message.includes('COMPLETA')) {
        showNotification(data.message, 'success', 10000);
    } else if (data.type === 'error') {
        showNotification(data.message, 'error', 8000);
    }
});

// Atualiza progresso da tarefa em tempo real
socket.on('task_progress', (data) => {
    console.log('[TASK PROGRESS]', data);
    
    // Atualiza o card da tarefa DIRETAMENTE sem recarregar
    const taskCards = document.querySelectorAll('[data-task-id]');
    taskCards.forEach(card => {
        if (card.dataset.taskId == data.task_id) {
            // Atualiza contador de adicionados
            const addedSpan = card.querySelector('.task-added-count');
            if (addedSpan) {
                addedSpan.textContent = data.total_added;
            }
            
            // Atualiza contador de hoje
            const todaySpan = card.querySelector('.task-today-count');
            if (todaySpan) {
                todaySpan.textContent = `${data.added_today}/${data.daily_limit}`;
            }

            const remainingSpan = card.querySelector('.task-remaining-count');
            if (remainingSpan) {
                remainingSpan.textContent = Math.max(0, data.target_members - data.total_added);
            }
            
            // Atualiza barra de progresso
            const progress = (data.total_added / data.target_members * 100).toFixed(1);
            const progressBar = card.querySelector('.task-progress-bar');
            if (progressBar) {
                progressBar.style.width = `${progress}%`;
                progressBar.textContent = `${progress}%`;
            }
        }
    });
    
    // Também recarrega para garantir
    loadTasks();
});

// Mantém compatibilidade com logs genéricos (para aquecimento, etc)
socket.on('log', (data) => {
    console.log('[GENERIC LOG]', data.message);
    // Apenas adiciona em warming-logs para não duplicar
    addLog('warming-logs', data.message, data.type);
});

socket.on('progress', (data) => {
    const progress = (data.session / data.total_sessions) * 100;
    const progressHtml = `
        <div class="progress-bar">
            <div class="progress-fill" style="width: ${progress}%">${Math.round(progress)}%</div>
        </div>
        <p>Sessão ${data.session}/${data.total_sessions} - Adicionados: ${data.total_added}</p>
    `;
    document.getElementById('add-progress').innerHTML = progressHtml;
});

socket.on('extraction_complete', (data) => {
    if (data.split && data.batches > 0) {
        // Extração com divisão em lotes
        addLog('extract-logs', `✅ Extração completa! ${data.count} membros extraídos`, 'success');
        addLog('extract-logs', `📦 Dividido em ${data.batches} lotes:`, 'info');
        
        if (data.files && data.files.length > 0) {
            data.files.forEach(file => {
                addLog('extract-logs', `   📄 Lote ${file.batch_number}: ${file.size} membros (${file.filename})`, 'info');
            });
        }
        
        addLog('extract-logs', `💾 Arquivos salvos na pasta data/`, 'success');
        addLog('extract-logs', `💡 Baixe os arquivos individualmente ou use o arquivo índice`, 'info');
        
        showNotification(`Extração completa! ${data.count} membros divididos em ${data.batches} lotes`, 'success');
    } else {
        // Extração normal (sem divisão)
        addLog('extract-logs', `✅ Extração completa! ${data.count} membros extraídos`, 'success');
        showNotification(`Extração completa! ${data.count} membros extraídos`, 'success');
    }
});

socket.on('addition_complete', (data) => {
    addLog('add-logs', `✅ Processo finalizado! Total: ${data.total_added} membros`, 'success');
    document.getElementById('stop-btn').style.display = 'none';
    addingProcessActive = false;
    showNotification(`Processo finalizado! ${data.total_added} membros adicionados`, 'success');
});

socket.on('round_complete', (data) => {
    addLog('add-logs', `🔄 Rodada ${data.round} completa! Adicionados: ${data.added_this_round}`, 'success');
    showNotification(`Rodada ${data.round} completa! ${data.added_this_round} membros adicionados`, 'info', 3000);
});

socket.on('error', (data) => {
    showNotification(data.message, 'error');
});

// Helpers
function addLog(elementId, message, type = 'info') {
    const logs = document.getElementById(elementId);
    if (!logs) {
        console.warn(`Log element not found: ${elementId}`);
        return;
    }
    
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    logs.appendChild(entry);
    logs.scrollTop = logs.scrollHeight;
    
    // Debug: mostra no console também
    console.log(`[${elementId}] ${message}`);
}

function showStatus(elementId, message, type) {
    const status = document.getElementById(elementId);
    status.className = `status-box ${type}`;
    status.textContent = message;
    status.style.display = 'block';
    
    setTimeout(() => {
        status.style.display = 'none';
    }, 5000);
}

// ========== TAREFAS (MULTI-GRUPOS) ==========

async function loadTaskSessions() {
    const response = await fetch('/api/sessions');
    const data = await response.json();
    
    // Pega sessões reservadas por qualquer tarefa ainda existente.
    const tasksResponse = await fetch('/api/tasks/blocked-sessions');
    const blockedData = await tasksResponse.json();
    const reservedSessions = blockedData.reserved_sessions || blockedData.blocked_sessions || [];
    
    const taskSessions = data.sessions
        .map((session, originalIndex) => ({...session, originalIndex}))
        .filter(s => {
            const isReserved = reservedSessions.includes(s.originalIndex);
            const isUsable = s.active && (s.status || 'active') === 'active';
            return isUsable || isReserved;
        });
    const container = document.getElementById('task-sessions-checkboxes');
    
    if (taskSessions.length === 0) {
        container.innerHTML = '<p style="color: #fca5a5;">⚠️ Nenhuma sessão disponível</p>';
        return;
    }
    
    container.innerHTML = taskSessions.map((s) => {
        const originalIndex = s.originalIndex;
        const isBlocked = reservedSessions.includes(originalIndex);
        const isUsable = s.active && (s.status || 'active') === 'active';
        const isDisabled = isBlocked || !isUsable;
        const opacity = isBlocked ? '0.5' : '1';
        const cursor = isDisabled ? 'not-allowed' : 'pointer';
        
        let statusBadge = '';
        if (isBlocked) {
            statusBadge = '<span style="color: #f59e0b; font-size: 11px; font-weight: 600;">🔒 EM TAREFA</span>';
        } else if (!isUsable) {
            statusBadge = '<span style="color: #fca5a5; font-size: 11px; font-weight: 600;">⚠️ INDISPONÍVEL</span>';
        }
        
        return `
        <label style="display: flex; align-items: center; gap: 10px; padding: 10px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; cursor: ${cursor}; transition: all 0.2s; opacity: ${opacity};" ${!isDisabled ? `onmouseover="this.style.background='rgba(59, 130, 246, 0.2)'" onmouseout="this.style.background='rgba(59, 130, 246, 0.1)'"` : ''}>
            <input type="checkbox" class="task-session-checkbox" value="${originalIndex}" ${isDisabled ? 'disabled' : ''} onchange="updateTaskSessionCounter()" style="width: 18px; height: 18px; cursor: ${cursor};">
            <div style="flex: 1;">
                <div style="color: #e2e8f0; font-weight: 600;">${escapeHtml(s.first_name || s.name || s.session_name || 'Sessão')} ${statusBadge}</div>
                <div style="color: #94a3b8; font-size: 12px;">${s.username ? '@' + escapeHtml(s.username) : escapeHtml(s.session_name || '')} • ${escapeHtml(s.phone || '')}</div>
            </div>
        </label>
    `;
    }).join('');
    updateTaskSessionCounter();
}

function toggleAllTaskSessions() {
    const selectAll = document.getElementById('task-select-all-sessions');
    const checkboxes = document.querySelectorAll('.task-session-checkbox');
    
    checkboxes.forEach(cb => {
        if (!cb.disabled) {
            cb.checked = selectAll.checked;
        }
    });
    updateTaskSessionCounter();
}

function updateTaskSessionCounter() {
    const counter = document.getElementById('task-session-counter');
    const all = Array.from(document.querySelectorAll('.task-session-checkbox')).filter(cb => !cb.disabled);
    const selected = all.filter(cb => cb.checked).length;
    if (counter) counter.textContent = `${selected} de ${all.length} sessão(ões) selecionada(s)`;

    const selectAll = document.getElementById('task-select-all-sessions');
    if (selectAll) {
        selectAll.checked = all.length > 0 && selected === all.length;
        selectAll.indeterminate = selected > 0 && selected < all.length;
    }
}

function enableCheckboxDragSelect(containerId, checkboxSelector, onChange) {
    const container = document.getElementById(containerId);
    if (!container || container.dataset.dragSelectReady === 'true') return;
    container.dataset.dragSelectReady = 'true';
    let dragging = false;
    let targetState = true;
    let dragStartedOnCheckbox = false;

    const applyToTarget = (target) => {
        const label = target.closest('label');
        if (!label || !container.contains(label)) return;
        const checkbox = label.querySelector(checkboxSelector);
        if (!checkbox || checkbox.disabled || checkbox.checked === targetState) return;
        checkbox.checked = targetState;
        checkbox.dispatchEvent(new Event('change', {bubbles: true}));
    };

    container.addEventListener('pointerdown', (event) => {
        if (event.button !== 0) return;
        const checkbox = event.target.closest(checkboxSelector);
        const label = event.target.closest('label');
        if (!checkbox && !label) return;
        const input = checkbox || label.querySelector(checkboxSelector);
        if (!input || input.disabled) return;
        dragging = true;
        dragStartedOnCheckbox = Boolean(checkbox);
        targetState = !input.checked;

        // Clique direto no checkbox deve usar o comportamento nativo do navegador.
        // O toggle manual aqui fazia alguns checkboxes voltarem para o estado anterior.
        if (!dragStartedOnCheckbox) {
            input.checked = targetState;
            input.dispatchEvent(new Event('change', {bubbles: true}));
            event.preventDefault();
        }
    });

    container.addEventListener('pointerover', (event) => {
        if (!dragging || event.buttons !== 1) return;
        applyToTarget(event.target);
    });

    window.addEventListener('pointerup', () => {
        if (!dragging) return;
        dragging = false;
        dragStartedOnCheckbox = false;
        if (typeof onChange === 'function') onChange();
    });
}

function toggleTaskSessionsList() {
    const container = document.getElementById('task-sessions-container');
    const icon = document.getElementById('task-sessions-icon');
    const btnText = document.getElementById('task-sessions-btn-text');
    
    if (container.style.display === 'none') {
        container.style.display = 'block';
        icon.className = 'fas fa-chevron-up';
        btnText.textContent = 'Ocultar Sessões';
    } else {
        container.style.display = 'none';
        icon.className = 'fas fa-chevron-down';
        btnText.textContent = 'Mostrar Sessões Disponíveis';
    }
}

function openTaskFormPanel() {
    const overlay = document.getElementById('task-form-overlay');
    if (!overlay) return;
    overlay.classList.add('open');
    document.getElementById('tasks')?.classList.add('task-form-page');
    loadTaskSessions();
    overlay.scrollIntoView({block: 'start', behavior: 'smooth'});
    setTimeout(() => document.getElementById('task-group-link')?.focus(), 50);
}

function closeTaskFormPanel() {
    const overlay = document.getElementById('task-form-overlay');
    if (!overlay) return;
    overlay.classList.remove('open');
    document.getElementById('tasks')?.classList.remove('task-form-page');
}

async function addGroupTask() {
    const groupLink = document.getElementById('task-group-link').value;
    const targetMembers = parseInt(document.getElementById('task-target').value);
    const dailyLimit = parseInt(document.getElementById('task-daily-limit').value);
    const membersPerSession = parseInt(document.getElementById('task-members-per-session').value);
    const delayAddsMinRaw = parseInt(document.getElementById('task-delay-adds-min').value);
    const delayAddsMaxRaw = parseInt(document.getElementById('task-delay-adds-max').value);
    const delaySessionsMinRaw = parseInt(document.getElementById('task-delay-sessions-min').value);
    const delaySessionsMaxRaw = parseInt(document.getElementById('task-delay-sessions-max').value);
    const delayBetweenAddsMin = Math.min(delayAddsMinRaw, delayAddsMaxRaw);
    const delayBetweenAddsMax = Math.max(delayAddsMinRaw, delayAddsMaxRaw);
    const delayBetweenSessionsMin = Math.min(delaySessionsMinRaw, delaySessionsMaxRaw);
    const delayBetweenSessionsMax = Math.max(delaySessionsMinRaw, delaySessionsMaxRaw);
    const groupInteractionEnabled = document.getElementById('task-group-interaction').checked;
    
    // Pega sessões selecionadas
    const selectedCheckboxes = document.querySelectorAll('.task-session-checkbox:checked');
    const selectedSessions = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));
    
    if (!groupLink || !targetMembers || !dailyLimit || !membersPerSession || !delayAddsMinRaw || !delayAddsMaxRaw || !delaySessionsMinRaw || !delaySessionsMaxRaw) {
        showNotification('Preencha todos os campos!', 'warning');
        return;
    }
    
    if (selectedSessions.length === 0) {
        showNotification('Selecione pelo menos uma sessão para esta tarefa!', 'warning');
        return;
    }

    if (delayBetweenAddsMin < 1 || delayBetweenAddsMax > 300) {
        showNotification('Delay entre adições deve ficar entre 1 e 300 segundos!', 'warning');
        return;
    }

    if (delayBetweenSessionsMin < 10 || delayBetweenSessionsMax > 1800) {
        showNotification('Delay entre sessões deve ficar entre 10 e 1800 segundos!', 'warning');
        return;
    }

    if (membersPerSession < 1) {
        showNotification('Membros por sessão deve ser no mínimo 1!', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                group_link: groupLink,
                target_members: targetMembers,
                daily_limit: dailyLimit,
                members_per_session: membersPerSession,
                delay_between_adds: delayBetweenAddsMin,
                delay_between_sessions: delayBetweenSessionsMin,
                delay_between_adds_min: delayBetweenAddsMin,
                delay_between_adds_max: delayBetweenAddsMax,
                delay_between_sessions_min: delayBetweenSessionsMin,
                delay_between_sessions_max: delayBetweenSessionsMax,
                group_interaction_enabled: groupInteractionEnabled,
                selected_sessions: selectedSessions
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const rejected = data.rejected_sessions?.length || 0;
            const suffix = rejected > 0 ? ` ${rejected} sessão(ões) ignorada(s).` : '';
            showNotification(`${data.created || 1} tarefa(s) criada(s).${suffix}`, 'success');
            document.getElementById('task-group-link').value = '';
            document.getElementById('task-group-interaction').checked = true;
            document.getElementById('task-select-all-sessions').checked = false;
            toggleAllTaskSessions();
            closeTaskFormPanel();
            loadTasks();
        } else {
            showNotification(`Erro: ${data.error}`, 'error');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        const data = await response.json();
        
        const tasksList = document.getElementById('tasks-list');
        
        if (!data.tasks || data.tasks.length === 0) {
            tasksList.innerHTML = '<p style="text-align:center;color:#999;">Nenhuma tarefa na fila</p>';
            return;
        }

        const taskStats = data.tasks.reduce((stats, task) => {
            stats[task.status] = (stats[task.status] || 0) + 1;
            return stats;
        }, {});
        const activeTask = data.tasks.find(task => task.status === 'active');
        const queueNotice = activeTask ? `
            <div class="task-queue-notice">
                <i class="fas fa-server"></i>
                <span>Modo VPS leve: tarefa #${activeTask.id} em execução. As outras aguardam você iniciar quando esta terminar ou pausar.</span>
            </div>
        ` : '';
        const queueHeader = `
            <div class="task-queue-summary">
                <div>
                    <span>Fila de tarefas</span>
                    <strong>${data.tasks.length}</strong>
                </div>
                <div>
                    <span>Pendentes</span>
                    <strong>${taskStats.pending || 0}</strong>
                </div>
                <div>
                    <span>Ativas</span>
                    <strong>${taskStats.active || 0}</strong>
                </div>
                <div>
                    <span>Pausadas</span>
                    <strong>${taskStats.paused || 0}</strong>
                </div>
                <div>
                    <span>Concluídas</span>
                    <strong>${taskStats.completed || 0}</strong>
                </div>
            </div>
        `;
        
        tasksList.innerHTML = queueHeader + queueNotice + data.tasks.map(task => {
            const remainingMembers = Math.max(0, (task.target_members || 0) - (task.total_added || 0));
            const effectiveStatus = task.status === 'completed' && remainingMembers > 0 ? 'paused' : task.status;
            const progress = Math.min(100, (task.total_added / task.target_members * 100)).toFixed(1);
            const statusColors = {
                'pending': '#94a3b8',
                'active': '#10b981',
                'paused': '#f59e0b',
                'completed': '#3b82f6'
            };
            const statusTexts = {
                'pending': 'Pendente',
                'active': 'Ativo',
                'paused': 'Pausado',
                'completed': 'Completo'
            };
            
            const sessionsCount = task.selected_sessions ? task.selected_sessions.length : 0;
            const membersPerSession = Math.max(1, parseInt(task.members_per_session || 1));
            const delayAddsMin = task.delay_between_adds_min || task.delay_between_adds || 5;
            const delayAddsMax = task.delay_between_adds_max || task.delay_between_adds || delayAddsMin;
            const delaySessionsMin = task.delay_between_sessions_min || task.delay_between_sessions || 90;
            const delaySessionsMax = task.delay_between_sessions_max || task.delay_between_sessions || delaySessionsMin;
            const delayAdds = delayAddsMin === delayAddsMax ? `${delayAddsMin}s` : `${delayAddsMin}-${delayAddsMax}s`;
            const delaySessions = delaySessionsMin === delaySessionsMax ? `${delaySessionsMin}s` : `${delaySessionsMin}-${delaySessionsMax}s`;
            const interactionText = task.group_interaction_enabled === false ? 'Desligada' : 'Ligada';
            const interactionColor = task.group_interaction_enabled === false ? '#fca5a5' : '#86efac';
            const membersSource = task.members_source_name || 'members.json';
            const membersTotal = task.members_total ? `${task.members_total} membros` : (task.members_file_exists ? 'arquivo carregado' : 'arquivo padrão');
            taskLogsById[getTaskLogKey(task.id)] = (task.logs || taskLogsById[getTaskLogKey(task.id)] || []).slice(-500);
            const isTerminalOpen = openTaskLogPanels.has(getTaskLogKey(task.id));
            const sessionSummary = task.session_status_summary || {
                available: sessionsCount,
                in_use: 0,
                flood: 0,
                invalid: 0,
                inactive: 0,
                missing: 0,
                total: sessionsCount
            };
            const sessionHealthClass = sessionSummary.flood || sessionSummary.invalid || sessionSummary.missing
                ? 'warning'
                : (sessionSummary.available > 0 || sessionSummary.in_use > 0 ? 'ok' : 'muted');
            const sessionHealthText = sessionSummary.flood || sessionSummary.invalid || sessionSummary.missing
                ? 'Atenção nas sessões'
                : (sessionSummary.available > 0 || sessionSummary.in_use > 0 ? 'Sessões prontas' : 'Sem sessão disponível');
            
            return `
                <div class="task-card-modern status-${effectiveStatus}" data-task-id="${task.id}">
                    <div class="task-card-head">
                        <div class="task-card-title">
                            <span class="task-id-pill">#${task.id}</span>
                            <h4>${escapeHtml(task.group_link || '')}</h4>
                            <p>
                                <span style="color: ${statusColors[effectiveStatus]}">${statusTexts[effectiveStatus]}</span>
                                <span>Sessões: ${sessionsCount}</span>
                                <span>Interação: <strong style="color: ${interactionColor}">${interactionText}</strong></span>
                            </p>
                            ${task.completion_note ? `<p style="color:#fbbf24;font-size:0.85em;margin:6px 0 0;">${escapeHtml(task.completion_note)}</p>` : ''}
                            ${effectiveStatus === 'paused' && task.pause_reason ? `<p style="color:#fca5a5;font-size:0.85em;margin:6px 0 0;"><i class="fas fa-circle-exclamation"></i> Motivo: ${escapeHtml(task.pause_reason)}</p>` : ''}
                        </div>
                        <span class="task-status-chip" style="--task-status-color:${statusColors[effectiveStatus]}">${statusTexts[effectiveStatus]}</span>
                    </div>

                    <div class="task-session-health ${sessionHealthClass}">
                        <div class="task-session-health-title">
                            <i class="fas fa-shield-alt"></i>
                            <span>${sessionHealthText}</span>
                        </div>
                        <div class="task-session-badges">
                            <span class="task-session-badge ok">Disponíveis: ${sessionSummary.available || 0}</span>
                            <span class="task-session-badge busy">Reservadas: ${sessionSummary.in_use || 0}</span>
                            <span class="task-session-badge warn">Flood: ${sessionSummary.flood || 0}</span>
                            <span class="task-session-badge danger">Inválidas: ${sessionSummary.invalid || 0}</span>
                            <span class="task-session-badge muted">Inativas: ${sessionSummary.inactive || 0}</span>
                        </div>
                    </div>
                    
                    <div class="task-progress-modern">
                        <div>
                            <div class="task-progress-bar" style="width: ${progress}%;">
                                ${progress}%
                            </div>
                        </div>
                    </div>
                    
                    <div class="task-metric-grid">
                        <div>
                            <div style="color: #94a3b8;">Meta</div>
                            <div style="font-weight: 600;">${task.target_members}</div>
                        </div>
                        <div>
                            <div style="color: #94a3b8;">Adicionados</div>
                            <div class="task-added-count" style="font-weight: 600;">${task.total_added}</div>
                        </div>
                        <div>
                            <div style="color: #94a3b8;">Faltam</div>
                            <div class="task-remaining-count" style="font-weight: 600;">${remainingMembers}</div>
                        </div>
                        <div>
                            <div style="color: #94a3b8;">Hoje</div>
                            <div class="task-today-count" style="font-weight: 600;">${task.added_today}/${task.daily_limit}</div>
                        </div>
                        <div>
                            <div style="color: #94a3b8;">Por sessão</div>
                            <div class="task-per-session-count" style="font-weight: 600;">${membersPerSession}</div>
                            <small style="color: #64748b;">membro(s) por rodada</small>
                        </div>
                        <div>
                            <div style="color: #94a3b8;">Delay add</div>
                            <div style="font-weight: 600;">${delayAdds}</div>
                        </div>
                        <div>
                            <div style="color: #94a3b8;">Delay sessão</div>
                            <div style="font-weight: 600;">${delaySessions}</div>
                        </div>
                        <div>
                            <div style="color: #94a3b8;">Arquivo</div>
                            <div style="font-weight: 600;">${membersSource}</div>
                            <small style="color: #64748b;">${membersTotal}</small>
                        </div>
                    </div>
                    
                    <div class="task-action-row">
                        ${effectiveStatus === 'pending' || effectiveStatus === 'paused' ? `
                            <button class="btn btn-success" onclick="startTask(${task.id})" style="padding: 10px 20px; font-size: 14px;">
                                <i class="fas fa-play"></i> Iniciar
                            </button>
                        ` : ''}
                        
                        ${effectiveStatus === 'active' ? `
                            <button class="btn btn-danger" onclick="pauseTask(${task.id})" style="padding: 10px 20px; font-size: 14px;">
                                <i class="fas fa-pause"></i> Pausar
                            </button>
                        ` : ''}
                        
                        ${effectiveStatus !== 'active' ? `
                            <button class="btn btn-warning" onclick="editTask(${task.id})" style="padding: 10px 20px; font-size: 14px;">
                                <i class="fas fa-edit"></i> Editar
                            </button>
                            <button class="btn btn-primary" onclick="changeTaskMembersFile(${task.id})" style="padding: 10px 20px; font-size: 14px;">
                                <i class="fas fa-file-import"></i> Trocar arquivo
                            </button>
                            <button class="btn btn-danger" onclick="removeTask(${task.id})" style="padding: 10px 20px; font-size: 14px;">
                                <i class="fas fa-trash"></i> Remover
                            </button>
                        ` : ''}
                        
                        <button class="btn btn-primary" onclick="viewTaskDetails(${task.id})" style="padding: 10px 20px; font-size: 14px;">
                            <i class="fas fa-info-circle"></i> Detalhes
                        </button>
                        <button class="btn btn-primary" onclick="toggleTaskLogs(${task.id})" style="padding: 10px 20px; font-size: 14px;">
                            <i class="fas fa-terminal"></i> Terminal
                        </button>
                    </div>

                    <div id="task-log-panel-${task.id}" class="task-card-terminal" style="display:${isTerminalOpen ? 'block' : 'none'};">
                        <div class="task-card-terminal-header">
                            <span><i class="fas fa-terminal"></i> Terminal da tarefa #${task.id}</span>
                            <button type="button" onclick="toggleTaskLogs(${task.id})" title="Ocultar terminal">
                                <i class="fas fa-chevron-up"></i>
                            </button>
                        </div>
                        <div id="task-log-body-${task.id}" class="logs task-card-terminal-body"></div>
                    </div>
                </div>
            `;
        }).join('');

        data.tasks.forEach(task => {
            if (openTaskLogPanels.has(getTaskLogKey(task.id))) {
                renderTaskLogBody(task.id);
            }
        });
        
    } catch (error) {
        console.error('Erro ao carregar tarefas:', error);
    }
}

async function startTask(taskId) {
    try {
        console.log('🚀 Iniciando tarefa:', taskId);
        showLoading('Solicitando início da tarefa...');
        
        const response = await fetch(`/api/tasks/${taskId}/start`, {
            method: 'POST'
        });
        
        console.log('📡 Response status:', response.status);
        const data = await readJsonResponse(response);
        console.log('📦 Response data:', data);
        
        hideLoading();
        
        if (data.success) {
            showNotification('Solicitação recebida. Verificando status real...', 'info');
            loadTasks();
            await waitForTaskStatus(taskId);
        } else {
            showNotification(`Erro: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('❌ Erro ao iniciar tarefa:', error);
        hideLoading();
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

async function pauseTask(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}/pause`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Tarefa pausada!', 'warning');
            loadTasks();
        } else {
            showNotification(`Erro: ${data.error}`, 'error');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

async function viewTaskDetails(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}`);
        const data = await response.json();
        
        if (data.success) {
            openTaskDetailsModal(data.task);
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

async function waitForTaskStatus(taskId) {
    // A thread é iniciada em segundo plano; consulte o estado persistido
    // para não informar sucesso enquanto a tarefa já foi pausada.
    const delays = [800, 1800, 3500, 6000];
    for (const delay of delays) {
        await new Promise(resolve => setTimeout(resolve, delay));
        try {
            const response = await fetch(`/api/tasks/${taskId}`);
            const data = await readJsonResponse(response);
            const task = data.task || data;
            if (!task || typeof task.status === 'undefined') continue;

            await loadTasks();
            if (task.status === 'active') {
                showNotification('Tarefa ativa e em execução. Acompanhe os logs.', 'success');
                return;
            }
            if (task.status === 'paused') {
                showNotification(`Tarefa pausada: ${task.pause_reason || 'verifique os logs da tarefa.'}`, 'warning');
                return;
            }
            if (task.status === 'completed') {
                showNotification('Tarefa concluída.', 'success');
                return;
            }
        } catch (error) {
            console.warn('Não foi possível consultar o status da tarefa:', error);
        }
    }
    showNotification('A tarefa foi enviada, mas ainda não há um status final. Atualize os logs.', 'info');
}

function taskStatusLabel(status) {
    const labels = {
        adicionado: 'Adicionado',
        falha: 'Falha',
        success: 'Sucesso',
        active: 'Ativa',
        invalid: 'Inválida',
        corrupted: 'Corrompida',
        flood: 'Flood',
        zero_added: 'Sem adição'
    };
    return labels[status] || status || 'Pendente';
}

function openTaskDetailsModal(task) {
    const oldModal = document.getElementById('task-details-modal');
    if (oldModal) oldModal.remove();

    const results = task.member_results || [];
    const sessions = task.sessions_info || [];
    const runs = task.session_runs || [];
    const added = results.filter(r => r.status === 'adicionado').length;
    const failed = results.filter(r => r.status === 'falha').length;
    const pending = Math.max(0, (task.target_members || 0) - (task.total_added || 0));

    const memberRows = results.length ? results.slice().reverse().map((r) => `
        <tr>
            <td>${escapeHtml(r.member_id || '-')}</td>
            <td>${escapeHtml(r.member_name || '-')}<small>${r.member_username ? '@' + escapeHtml(r.member_username) : ''}</small></td>
            <td><span class="task-detail-status ${r.status === 'adicionado' ? 'ok' : 'fail'}">${taskStatusLabel(r.status)}</span></td>
            <td>${escapeHtml(r.account || '-')}<small>${r.phone ? escapeHtml(r.phone) : ''}</small></td>
            <td>${r.time ? escapeHtml(new Date(r.time).toLocaleString()) : '-'}</td>
            <td>${escapeHtml(r.observation || '-')}</td>
        </tr>
    `).join('') : `
        <tr><td colspan="6" class="task-detail-empty">Nenhum membro processado ainda nesta tarefa.</td></tr>
    `;

    const sessionRows = sessions.length ? sessions.map((s) => {
        const sessionRuns = runs.filter(r => r.session_name === s.session_name);
        const sessionResults = results.filter(r =>
            r.session_name === s.session_name ||
            (s.phone && r.phone === s.phone) ||
            (s.first_name && r.account === s.first_name)
        );
        const totalAddedFromResults = sessionResults.filter(r => r.status === 'adicionado').length;
        const totalFailedFromResults = sessionResults.filter(r => r.status === 'falha').length;
        const totalAddedFromRuns = sessionRuns.reduce((sum, r) => sum + (parseInt(r.added) || 0), 0);
        const totalAdded = parseInt(s.added_count || 0) || totalAddedFromResults || totalAddedFromRuns;
        const totalFailed = parseInt(s.failed_count || 0) || totalFailedFromResults;
        const lastRun = sessionRuns[sessionRuns.length - 1] || {};
        const lastResult = sessionResults[sessionResults.length - 1] || {};
        const status = s.flood ? 'flood' : (s.active === false ? 'inactive' : (s.last_status || s.status || 'active'));
        return `
            <tr>
                <td>${escapeHtml(s.index ?? '-')}</td>
                <td>${escapeHtml(s.first_name || s.session_name || '-')}<small>${s.username ? '@' + escapeHtml(s.username) : ''}</small></td>
                <td>${escapeHtml(s.phone || '-')}</td>
                <td><span class="task-detail-status ${status === 'active' ? 'ok' : 'warn'}">${taskStatusLabel(status)}</span></td>
                <td>${totalAdded}</td>
                <td>${totalFailed}</td>
                <td>${escapeHtml(s.last_observation || lastResult.observation || lastRun.reason || (s.flood_until ? 'Flood até ' + s.flood_until : '-'))}</td>
            </tr>
        `;
    }).join('') : `
        <tr><td colspan="7" class="task-detail-empty">Nenhuma conta vinculada a esta tarefa.</td></tr>
    `;

    const modal = document.createElement('div');
    modal.id = 'task-details-modal';
    modal.className = 'task-details-modal';
    modal.innerHTML = `
        <div class="task-details-dialog">
            <div class="task-details-header">
                <div>
                    <h3>Tarefa #${task.id}</h3>
                    <p>${escapeHtml(task.group_link || '')}</p>
                </div>
                <button type="button" onclick="closeTaskDetailsModal()" title="Fechar"><i class="fas fa-times"></i></button>
            </div>
            <div class="task-details-summary">
                <div><span>Meta</span><strong>${task.total_added || 0}/${task.target_members || 0}</strong></div>
                <div><span>Hoje</span><strong>${task.added_today || 0}/${task.daily_limit || 0}</strong></div>
                <div><span>Adicionados</span><strong>${added}</strong></div>
                <div><span>Falhas</span><strong>${failed}</strong></div>
                <div><span>Faltam</span><strong>${pending}</strong></div>
            </div>
            <div class="task-details-tabs">
                <button class="active" onclick="switchTaskDetailsTab('members')">Membros</button>
                <button onclick="switchTaskDetailsTab('accounts')">Contas</button>
                <button onclick="switchTaskDetailsTab('general')">Informações Gerais</button>
            </div>
            <div id="task-details-members" class="task-details-tab active">
                <div class="task-details-filter">
                    <label>Filtro:</label>
                    <select onchange="filterTaskDetailMembers(this.value)">
                        <option value="todos">Todos</option>
                        <option value="adicionado">Adicionados</option>
                        <option value="falha">Falhas</option>
                    </select>
                </div>
                <div class="task-details-table-wrap">
                    <table class="task-details-table" id="task-details-members-table">
                        <thead><tr><th>Membro ID</th><th>Membro</th><th>Status</th><th>Conta</th><th>Data</th><th>Observação</th></tr></thead>
                        <tbody>${memberRows}</tbody>
                    </table>
                </div>
            </div>
            <div id="task-details-accounts" class="task-details-tab">
                <div class="task-details-table-wrap">
                    <table class="task-details-table">
                        <thead><tr><th>#</th><th>Conta</th><th>Telefone</th><th>Status</th><th>Adicionados</th><th>Falhas</th><th>Observação</th></tr></thead>
                        <tbody>${sessionRows}</tbody>
                    </table>
                </div>
            </div>
            <div id="task-details-general" class="task-details-tab">
                <div class="task-details-general">
                    <div><span>Arquivo</span><strong>${escapeHtml(task.members_source_name || 'members.json')}</strong></div>
                    <div><span>Status</span><strong>${taskStatusLabel(task.status)}</strong></div>
                    <div><span>Sessões vinculadas</span><strong>${sessions.length}</strong></div>
                    <div><span>Membros por sessão</span><strong>${Math.max(1, parseInt(task.members_per_session || 1))}</strong></div>
                    <div><span>Delay add</span><strong>${task.delay_between_adds_min || task.delay_between_adds || 0}-${task.delay_between_adds_max || task.delay_between_adds || 0}s</strong></div>
                    <div><span>Delay sessão</span><strong>${task.delay_between_sessions_min || task.delay_between_sessions || 0}-${task.delay_between_sessions_max || task.delay_between_sessions || 0}s</strong></div>
                    <div><span>Interação</span><strong>${task.group_interaction_enabled === false ? 'Desligada' : 'Ligada'}</strong></div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    ensureTaskDetailsStyles();
}

function closeTaskDetailsModal() {
    const modal = document.getElementById('task-details-modal');
    if (modal) modal.remove();
}

function switchTaskDetailsTab(tab) {
    document.querySelectorAll('.task-details-tabs button').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.task-details-tab').forEach(panel => panel.classList.remove('active'));
    const btn = Array.from(document.querySelectorAll('.task-details-tabs button')).find(item => item.textContent.toLowerCase().includes(tab === 'members' ? 'membros' : tab === 'accounts' ? 'contas' : 'informações'));
    if (btn) btn.classList.add('active');
    const panel = document.getElementById(`task-details-${tab}`);
    if (panel) panel.classList.add('active');
}

function filterTaskDetailMembers(filter) {
    document.querySelectorAll('#task-details-members-table tbody tr').forEach(row => {
        if (row.children.length < 6) return;
        const status = row.children[2].textContent.trim().toLowerCase();
        row.style.display = filter === 'todos' || status.includes(filter) ? '' : 'none';
    });
}

function ensureTaskDetailsStyles() {
    if (document.getElementById('task-details-styles')) return;
    const style = document.createElement('style');
    style.id = 'task-details-styles';
    style.textContent = `
        .task-card-terminal { margin-top: 14px; border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; overflow: hidden; background: rgba(2, 6, 23, 0.58); }
        .task-card-terminal-header { display:flex; align-items:center; justify-content:space-between; padding:10px 12px; color:#cbd5e1; background:rgba(15, 23, 42, 0.9); font-weight:700; }
        .task-card-terminal-header button { width:34px; height:30px; border:0; border-radius:6px; cursor:pointer; color:#cbd5e1; background:rgba(59,130,246,0.18); }
        .task-card-terminal-body { min-height:160px; max-height:320px; border-radius:0; margin:0; }
        .task-details-modal { position:fixed; inset:0; z-index:20000; display:flex; align-items:center; justify-content:center; padding:20px; background:rgba(2, 6, 23, 0.78); }
        .task-details-dialog { width:min(1120px, 96vw); max-height:90vh; overflow:hidden; display:flex; flex-direction:column; background:#0f172a; border:1px solid rgba(148,163,184,0.25); border-radius:8px; box-shadow:0 24px 70px rgba(0,0,0,0.45); }
        .task-details-header { display:flex; justify-content:space-between; gap:16px; padding:18px 20px; border-bottom:1px solid rgba(148,163,184,0.18); }
        .task-details-header h3 { margin:0; color:#f8fafc; }
        .task-details-header p { margin:4px 0 0; color:#94a3b8; word-break:break-word; }
        .task-details-header button { width:38px; height:38px; border:0; border-radius:8px; background:rgba(239,68,68,0.16); color:#fecaca; cursor:pointer; }
        .task-details-summary { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:10px; padding:14px 20px; }
        .task-details-summary div, .task-details-general div { padding:12px; border:1px solid rgba(148,163,184,0.15); border-radius:8px; background:rgba(15,23,42,0.7); }
        .task-details-summary span, .task-details-general span { display:block; color:#94a3b8; font-size:12px; }
        .task-details-summary strong, .task-details-general strong { display:block; color:#f8fafc; margin-top:4px; overflow-wrap:anywhere; }
        .task-details-tabs { display:flex; gap:6px; padding:0 20px 12px; border-bottom:1px solid rgba(148,163,184,0.18); }
        .task-details-tabs button { border:0; border-radius:6px; padding:9px 12px; color:#cbd5e1; background:rgba(51,65,85,0.75); cursor:pointer; }
        .task-details-tabs button.active { color:#fff; background:#2563eb; }
        .task-details-tab { display:none; overflow:auto; padding:14px 20px 20px; }
        .task-details-tab.active { display:block; }
        .task-details-filter { display:flex; align-items:center; justify-content:flex-end; gap:8px; margin-bottom:10px; color:#cbd5e1; }
        .task-details-filter select { background:#e5e7eb; color:#111827; border:0; border-radius:4px; padding:6px 10px; }
        .task-details-table-wrap { overflow:auto; border:1px solid rgba(148,163,184,0.18); border-radius:8px; }
        .task-details-table { width:100%; border-collapse:collapse; min-width:760px; background:#e5e7eb; color:#111827; }
        .task-details-table th, .task-details-table td { padding:9px 10px; border-bottom:1px solid #cbd5e1; vertical-align:top; font-size:13px; }
        .task-details-table th { background:#d1d5db; font-weight:800; }
        .task-details-table small { display:block; color:#475569; margin-top:2px; overflow-wrap:anywhere; }
        .task-detail-status { font-weight:800; }
        .task-detail-status.ok { color:#15803d; }
        .task-detail-status.fail { color:#dc2626; }
        .task-detail-status.warn { color:#b45309; }
        .task-detail-empty { text-align:center; color:#64748b; padding:24px !important; }
        .task-details-general { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:10px; }
    `;
    document.head.appendChild(style);
}

async function removeTask(taskId) {
    if (!confirm('Confirma remoção desta tarefa?')) return;
    
    try {
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Tarefa removida!', 'success');
            loadTasks();
        } else {
            showNotification(`Erro: ${data.error}`, 'error');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

function changeTaskMembersFile(taskId) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,application/json';
    input.style.display = 'none';
    input.addEventListener('change', async () => {
        const file = input.files?.[0];
        input.remove();
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            showNotification('Trocando arquivo de membros...', 'info', 2500);
            const response = await fetch(`/api/tasks/${taskId}/members-file`, {
                method: 'POST',
                body: formData
            });
            const data = await readJsonResponse(response);

            if (data.success) {
                showNotification(`Arquivo trocado: ${data.total} membros (${data.pending ?? data.total} pendentes)`, 'success');
                loadTasks();
            } else {
                showNotification(`Erro: ${data.error}`, 'error');
            }
        } catch (error) {
            showNotification(`Erro ao trocar arquivo: ${error.message}`, 'error', 8000);
        }
    });

    document.body.appendChild(input);
    input.click();
}

async function editTask(taskId) {
    try {
        // Busca dados da tarefa
        const response = await fetch(`/api/tasks/${taskId}`);
        const result = await response.json();
        
        if (!result.success) {
            showNotification('Erro ao carregar tarefa', 'error');
            return;
        }
        
        const task = result.task;
        window.currentEditTaskSessions = Array.isArray(task.all_sessions_info) ? task.all_sessions_info : [];
        window.currentEditTaskSelectedSessions = new Set((task.selected_sessions || []).map(index => Number(index)));
        
        // Cria modal de edição
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;
        
        modal.innerHTML = `
            <div style="background:#111827; border:1px solid rgba(148,163,184,0.28); padding:0; border-radius:8px; max-width:1120px; width:94%; max-height:90vh; overflow:hidden; box-shadow:0 24px 70px rgba(0,0,0,.5);">
                <div style="display:flex;justify-content:space-between;align-items:center;padding:18px 22px;background:#374151;border-bottom:1px solid rgba(255,255,255,.12);">
                    <h2 style="color:#fff;margin:0;font-size:22px;">
                        <i class="fas fa-edit"></i> Editar Tarefa #${taskId}
                    </h2>
                    <button type="button" onclick="closeEditModal()" style="border:0;background:transparent;color:#fff;font-size:24px;cursor:pointer;">×</button>
                </div>

                <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(360px,420px);gap:18px;padding:18px;background:#4b5563;max-height:calc(90vh - 150px);overflow:auto;">
                    <section style="display:grid;gap:12px;">
                        <div style="border:1px solid rgba(255,255,255,.35);padding:12px;">
                            <strong style="display:block;color:#fff;margin-bottom:10px;">ORIGEM E DESTINO</strong>
                            <div class="form-group">
                                <label>Link do Grupo</label>
                                <input type="text" id="edit-group-link" value="${escapeHtml(task.group_link)}" class="form-control">
                            </div>
                            <div class="form-group" style="margin-bottom:0;">
                                <label>Trocar Arquivo de Membros</label>
                                <div style="color:#e5e7eb;font-size:12px;margin-bottom:8px;">
                                    Atual: <strong>${escapeHtml(task.members_source_name || 'members.json')}</strong>
                                    ${task.members_total ? ` · ${task.members_total} membros` : ''}
                                </div>
                                <input type="file" id="edit-members-file" accept=".json" class="form-control">
                            </div>
                        </div>

                        <div style="border:1px solid rgba(255,255,255,.35);padding:12px;">
                            <strong style="display:block;color:#fff;margin-bottom:10px;">PROTEÇÃO DE CONTAS</strong>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Meta Total</label>
                                    <input type="number" id="edit-target-members" value="${task.target_members}" min="1" class="form-control">
                                </div>
                                <div class="form-group">
                                    <label>Limite Diário</label>
                                    <input type="number" id="edit-daily-limit" value="${task.daily_limit}" min="1" max="500" class="form-control">
                                </div>
                            </div>
                            <div class="form-group">
                                <label>Membros por Sessão</label>
                                <input type="number" id="edit-members-per-session" value="${task.members_per_session || 25}" min="1" class="form-control">
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Intervalo Inicial (seg.)</label>
                                    <input type="number" id="edit-delay-adds-min" value="${task.delay_between_adds_min || task.delay_between_adds || 5}" min="1" max="300" class="form-control">
                                </div>
                                <div class="form-group">
                                    <label>Intervalo Final (seg.)</label>
                                    <input type="number" id="edit-delay-adds-max" value="${task.delay_between_adds_max || task.delay_between_adds || 5}" min="1" max="300" class="form-control">
                                </div>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Delay Sessão Mín.</label>
                                    <input type="number" id="edit-delay-sessions-min" value="${task.delay_between_sessions_min || task.delay_between_sessions || 90}" min="10" max="1800" class="form-control">
                                </div>
                                <div class="form-group">
                                    <label>Delay Sessão Máx.</label>
                                    <input type="number" id="edit-delay-sessions-max" value="${task.delay_between_sessions_max || task.delay_between_sessions || 90}" min="10" max="1800" class="form-control">
                                </div>
                            </div>
                        </div>

                        <div style="border:1px solid rgba(255,255,255,.35);padding:12px;">
                            <strong style="display:block;color:#fff;margin-bottom:10px;">FILTROS E CONTROLES</strong>
                            <label class="task-toggle-row" style="margin:0;">
                                <input type="checkbox" id="edit-group-interaction" ${task.group_interaction_enabled === false ? '' : 'checked'}>
                                <span>Enviar mensagens de aquecimento/interação</span>
                            </label>
                        </div>
                    </section>

                    <section style="display:flex;flex-direction:column;min-height:520px;">
                        <strong style="color:#fff;margin-bottom:8px;">Selecione as contas para a tarefa:</strong>
                        <input type="text" id="edit-task-session-search" class="form-control" placeholder="Buscar por nome, telefone ou sessão..." oninput="renderEditTaskSessionList()" style="margin-bottom:8px;">
                        <div style="display:flex;gap:8px;margin-bottom:8px;">
                            <button type="button" class="mini-btn" onclick="selectAllEditTaskSessions()">Selecionar visíveis</button>
                            <button type="button" class="mini-btn" onclick="clearEditTaskSessions()">Limpar</button>
                        </div>
                        <div id="edit-task-session-list" style="flex:1;min-height:360px;max-height:520px;overflow-y:auto;background:#0f172a;border:1px solid rgba(148,163,184,.35);color:#f8fafc;border-radius:6px;"></div>
                        <div id="edit-task-session-counter" style="text-align:center;color:#fff;margin-top:16px;font-weight:700;">Contas selecionadas: 0</div>
                    </section>
                </div>

                <div style="display:flex;gap:10px;justify-content:center;padding:16px;background:#4b5563;border-top:1px solid rgba(255,255,255,.12);">
                    <button class="btn btn-success" onclick="saveTaskEdit(${taskId})" style="flex: 1;">
                        <i class="fas fa-save"></i> Salvar
                    </button>
                    <button class="btn btn-danger" onclick="closeEditModal()" style="flex: 1;">
                        <i class="fas fa-times"></i> Cancelar
                    </button>
                </div>
            </div>
        `;
        
        modal.id = 'edit-task-modal';
        document.body.appendChild(modal);
        renderEditTaskSessionList();
        
        // Fecha ao clicar fora
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeEditModal();
            }
        });
        
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

function getEditTaskVisibleSessionIndexes() {
    const query = String(document.getElementById('edit-task-session-search')?.value || '').trim().toLowerCase();
    return (window.currentEditTaskSessions || [])
        .filter(session => {
            const text = [
                session.first_name,
                session.username,
                session.phone,
                session.session_name,
                session.status
            ].filter(Boolean).join(' ').toLowerCase();
            return !query || text.includes(query);
        })
        .map(session => Number(session.index));
}

function renderEditTaskSessionList() {
    const list = document.getElementById('edit-task-session-list');
    if (!list) return;

    const visibleIndexes = new Set(getEditTaskVisibleSessionIndexes());
    const sessions = (window.currentEditTaskSessions || []).filter(session => visibleIndexes.has(Number(session.index)));
    const selected = window.currentEditTaskSelectedSessions || new Set();

    if (!sessions.length) {
        list.innerHTML = '<div style="padding:18px;text-align:center;color:#374151;">Nenhuma conta encontrada.</div>';
        updateEditTaskSessionCounter();
        return;
    }

    list.innerHTML = sessions.map(session => {
        const index = Number(session.index);
        const checked = selected.has(index) ? 'checked' : '';
        const disabled = session.active === false || ['invalid', 'corrupted', 'banned'].includes(String(session.status || '').toLowerCase());
        const statusText = session.flood
            ? 'Flood/quarentena'
            : disabled
                ? (session.active === false ? 'Inativa' : String(session.status || 'indisponível'))
                : 'Disponível';
        const isSelected = selected.has(index);
        const rowBg = isSelected ? 'rgba(37,99,235,.42)' : 'rgba(15,23,42,.92)';
        const borderColor = isSelected ? 'rgba(96,165,250,.75)' : 'rgba(51,65,85,.95)';
        const textColor = disabled ? '#94a3b8' : '#f8fafc';
        const detailColor = disabled ? '#64748b' : '#cbd5e1';
        const opacity = disabled ? '.72' : '1';
        const label = [
            session.phone || session.session_name || `Conta ${index + 1}`,
            session.first_name || '',
            statusText
        ].filter(Boolean).join(' | ');

        return `
            <label style="display:grid;grid-template-columns:22px minmax(0,1fr);gap:8px;align-items:center;padding:10px 9px;border-bottom:1px solid ${borderColor};background:${rowBg};opacity:${opacity};cursor:${disabled ? 'not-allowed' : 'pointer'};">
                <input type="checkbox" class="edit-task-session-checkbox" value="${index}" ${checked} ${disabled ? 'disabled' : ''} onchange="toggleEditTaskSession(${index}, this.checked, this)" style="width:16px;height:16px;">
                <span style="min-width:0;" title="${escapeHtml(label)}">
                    <strong style="display:block;color:${textColor};font:700 13px Consolas, monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                        ${escapeHtml(session.phone || session.session_name || `Conta ${index + 1}`)} | ${escapeHtml(session.first_name || session.username || 'Sem nome')}
                    </strong>
                    <small style="display:block;color:${session.flood ? '#fbbf24' : detailColor};font:12px Consolas, monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px;">
                        ${escapeHtml(session.session_name || '')}${session.username ? ` | @${escapeHtml(session.username)}` : ''}${session.flood ? ' | FLOOD / QUARENTENA' : ` | ${escapeHtml(statusText)}`}
                    </small>
                </span>
            </label>
        `;
    }).join('');

    updateEditTaskSessionCounter();
    enableCheckboxDragSelect('edit-task-session-list', '.edit-task-session-checkbox', updateEditTaskSessionCounter);
}

function toggleEditTaskSession(index, checked, input = null) {
    window.currentEditTaskSelectedSessions = window.currentEditTaskSelectedSessions || new Set();
    if (checked) {
        window.currentEditTaskSelectedSessions.add(Number(index));
    } else {
        window.currentEditTaskSelectedSessions.delete(Number(index));
    }

    const checkbox = input || document.querySelector(`.edit-task-session-checkbox[value="${Number(index)}"]`);
    const row = checkbox?.closest('label');
    if (row && !checkbox.disabled) {
        row.style.background = checked ? 'rgba(37,99,235,.42)' : 'rgba(15,23,42,.92)';
        row.style.borderBottomColor = checked ? 'rgba(96,165,250,.75)' : 'rgba(51,65,85,.95)';
    }
    updateEditTaskSessionCounter();
}

function selectAllEditTaskSessions() {
    window.currentEditTaskSelectedSessions = window.currentEditTaskSelectedSessions || new Set();
    const visible = new Set(getEditTaskVisibleSessionIndexes());
    (window.currentEditTaskSessions || []).forEach(session => {
        const index = Number(session.index);
        const disabled = session.active === false || ['invalid', 'corrupted', 'banned'].includes(String(session.status || '').toLowerCase());
        if (visible.has(index) && !disabled) window.currentEditTaskSelectedSessions.add(index);
    });
    renderEditTaskSessionList();
}

function clearEditTaskSessions() {
    window.currentEditTaskSelectedSessions = new Set();
    renderEditTaskSessionList();
}

function updateEditTaskSessionCounter() {
    const counter = document.getElementById('edit-task-session-counter');
    if (counter) {
        counter.textContent = `Contas selecionadas: ${(window.currentEditTaskSelectedSessions || new Set()).size}`;
    }
}

function closeEditModal() {
    const modal = document.getElementById('edit-task-modal');
    if (modal) {
        modal.remove();
    }
    window.currentEditTaskSessions = [];
    window.currentEditTaskSelectedSessions = new Set();
}

async function saveTaskEdit(taskId) {
    try {
        const groupLink = document.getElementById('edit-group-link').value;
        const targetMembers = parseInt(document.getElementById('edit-target-members').value);
        const dailyLimit = parseInt(document.getElementById('edit-daily-limit').value);
        const membersPerSession = parseInt(document.getElementById('edit-members-per-session').value);
        const delayAddsMinRaw = parseInt(document.getElementById('edit-delay-adds-min').value);
        const delayAddsMaxRaw = parseInt(document.getElementById('edit-delay-adds-max').value);
        const delaySessionsMinRaw = parseInt(document.getElementById('edit-delay-sessions-min').value);
        const delaySessionsMaxRaw = parseInt(document.getElementById('edit-delay-sessions-max').value);
        const delayBetweenAddsMin = Math.min(delayAddsMinRaw, delayAddsMaxRaw);
        const delayBetweenAddsMax = Math.max(delayAddsMinRaw, delayAddsMaxRaw);
        const delayBetweenSessionsMin = Math.min(delaySessionsMinRaw, delaySessionsMaxRaw);
        const delayBetweenSessionsMax = Math.max(delaySessionsMinRaw, delaySessionsMaxRaw);
        const groupInteractionEnabled = document.getElementById('edit-group-interaction').checked;
        const membersFile = document.getElementById('edit-members-file')?.files?.[0] || null;
        const selectedSessions = Array.from(window.currentEditTaskSelectedSessions || []).sort((a, b) => a - b);
        
        if (!groupLink || !targetMembers || !dailyLimit || !membersPerSession || !delayAddsMinRaw || !delayAddsMaxRaw || !delaySessionsMinRaw || !delaySessionsMaxRaw) {
            showNotification('Preencha todos os campos!', 'warning');
            return;
        }
        
        if (targetMembers < 1) {
            showNotification('Meta total deve ser maior que 0!', 'warning');
            return;
        }
        
        if (dailyLimit < 1 || dailyLimit > 500) {
            showNotification('Limite diário deve estar entre 1 e 500!', 'warning');
            return;
        }
        
        if (membersPerSession < 1) {
            showNotification('Membros por sessão deve ser no mínimo 1!', 'warning');
            return;
        }

        if (!selectedSessions.length) {
            showNotification('Selecione ao menos uma sessão para a tarefa!', 'warning');
            return;
        }

        if (delayBetweenAddsMin < 1 || delayBetweenAddsMax > 300) {
            showNotification('Delay entre adições deve ficar entre 1 e 300 segundos!', 'warning');
            return;
        }

        if (delayBetweenSessionsMin < 10 || delayBetweenSessionsMax > 1800) {
            showNotification('Delay entre sessões deve ficar entre 10 e 1800 segundos!', 'warning');
            return;
        }
        
        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                group_link: groupLink,
                target_members: targetMembers,
                daily_limit: dailyLimit,
                members_per_session: membersPerSession,
                delay_between_adds: delayBetweenAddsMin,
                delay_between_sessions: delayBetweenSessionsMin,
                delay_between_adds_min: delayBetweenAddsMin,
                delay_between_adds_max: delayBetweenAddsMax,
                delay_between_sessions_min: delayBetweenSessionsMin,
                delay_between_sessions_max: delayBetweenSessionsMax,
                group_interaction_enabled: groupInteractionEnabled,
                selected_sessions: selectedSessions
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (membersFile) {
                const fileData = new FormData();
                fileData.append('file', membersFile);

                const fileResponse = await fetch(`/api/tasks/${taskId}/members-file`, {
                    method: 'POST',
                    body: fileData
                });
                const fileResult = await fileResponse.json();

                if (!fileResult.success) {
                    showNotification(`Tarefa salva, mas o arquivo não foi trocado: ${fileResult.error}`, 'warning', 8000);
                    loadTasks();
                    return;
                }

                showNotification(`Tarefa atualizada e arquivo trocado: ${fileResult.total} membros`, 'success');
            } else {
                showNotification('Tarefa atualizada com sucesso!', 'success');
            }
            closeEditModal();
            loadTasks();
        } else {
            showNotification(`Erro: ${data.error}`, 'error');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

// ========== AQUECIMENTO ==========

let warmingGroups = [];

async function loadWarmingGroups() {
    try {
        const response = await fetch('/api/warming/groups');
        const data = await response.json();
        
        if (data.success) {
            warmingGroups = data.groups || [];
            updateWarmingGroupsList();
        }
    } catch (error) {
        console.error('Erro ao carregar grupos de aquecimento:', error);
    }
}

function updateWarmingGroupsList() {
    const listDiv = document.getElementById('warming-groups-list');
    
    if (warmingGroups.length === 0) {
        listDiv.innerHTML = '<p style="color: #94a3b8;">Nenhum grupo adicionado</p>';
        return;
    }
    
    listDiv.innerHTML = warmingGroups.map((group, index) => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; margin-bottom: 10px;">
            <div style="color: #e2e8f0;">
                <i class="fas fa-users"></i> ${group}
            </div>
            <button class="btn btn-danger" onclick="removeWarmingGroup(${index})" style="padding: 6px 12px; font-size: 0.85em;">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `).join('');
}

async function addWarmingGroup() {
    const input = document.getElementById('warming-group-input');
    const groupLink = input.value.trim();
    
    if (!groupLink) {
        showNotification('Digite o link do grupo!', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/warming/groups', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ group_link: groupLink })
        });
        
        const data = await response.json();
        
        if (data.success) {
            warmingGroups = data.groups;
            updateWarmingGroupsList();
            input.value = '';
            showNotification('Grupo adicionado!', 'success');
        } else {
            showNotification(`Erro: ${data.error}`, 'error');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

async function removeWarmingGroup(index) {
    if (!confirm('Remover este grupo?')) return;
    
    try {
        const response = await fetch(`/api/warming/groups/${index}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            warmingGroups = data.groups;
            updateWarmingGroupsList();
            showNotification('Grupo removido!', 'success');
        } else {
            showNotification(`Erro: ${data.error}`, 'error');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

async function startWarming() {
    if (warmingGroups.length === 0) {
        showNotification('Adicione pelo menos um grupo primeiro!', 'warning');
        return;
    }
    
    const minInterval = parseInt(document.getElementById('warming-min').value);
    const maxInterval = parseInt(document.getElementById('warming-max').value);
    
    if (minInterval >= maxInterval) {
        showNotification('O intervalo mínimo deve ser menor que o máximo!', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/warming/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                min_interval: minInterval,
                max_interval: maxInterval
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('warming-status').innerHTML = '🟢 Ativo';
            document.getElementById('warming-status').style.color = '#10b981';
            document.querySelector('button[onclick="startWarming()"]').style.display = 'none';
            document.getElementById('stop-warming-btn').style.display = 'inline-flex';
            addLog('warming-logs', '✅ Aquecimento iniciado!', 'success');
            showNotification('Aquecimento iniciado com sucesso!', 'success');
        } else {
            showNotification(`Erro: ${data.error}`, 'error');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

async function stopWarming() {
    try {
        const response = await fetch('/api/warming/stop', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('warming-status').innerHTML = '⭕ Desativado';
            document.getElementById('warming-status').style.color = '#fca5a5';
            document.querySelector('button[onclick="startWarming()"]').style.display = 'inline-flex';
            document.getElementById('stop-warming-btn').style.display = 'none';
            addLog('warming-logs', '⏹️ Aquecimento parado!', 'warning');
            showNotification('Aquecimento parado!', 'warning');
        } else {
            showNotification(`Erro: ${data.error}`, 'error');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

// Socket events para aquecimento
socket.on('warming_log', (data) => {
    addLog('warming-logs', data.message, data.type);
});

// Reações manuais
let reactionAvailableSessions = [];
let customReactions = [];

async function loadReactions() {
    try {
        const response = await fetch('/api/reactions');
        const data = await response.json();
        if (!data.success) {
            showNotification(data.error || 'Erro ao carregar reações', 'error');
            return;
        }

        const selectedSessions = new Set(getSelectedReactionSessions());
        reactionAvailableSessions = data.available_sessions || [];
        renderReactionSessionList(reactionAvailableSessions, selectedSessions);

        const delayInput = document.getElementById('reaction-delay');
        if (delayInput) delayInput.value = data.settings.delay_seconds || 5;

        const disableCheckbox = document.getElementById('reaction-disable-add-interactions');
        if (disableCheckbox) disableCheckbox.checked = !!data.settings.disable_add_group_interactions;

        customReactions = Array.isArray(data.settings.custom_reactions) ? data.settings.custom_reactions : [];
        renderCustomReactions();

        const continuousTask = data.continuous_task || {};
        if (continuousTask.enabled) {
            const linkInput = document.getElementById('reaction-link');
            const savedLinks = Array.isArray(continuousTask.post_links) && continuousTask.post_links.length
                ? continuousTask.post_links
                : [continuousTask.post_link || ''].filter(Boolean);
            if (linkInput && !linkInput.value) linkInput.value = savedLinks.join('\n');
            if (Array.isArray(continuousTask.session_indexes)) {
                setReactionSessionSelection(continuousTask.session_indexes);
            }
            if (Array.isArray(continuousTask.reactions)) {
                document.querySelectorAll('#reaction-picker input[type="checkbox"]').forEach(input => {
                    input.checked = continuousTask.reactions.includes(input.value);
                });
            }
        }

        updateReactionMonitorButtons(!!data.monitor_running);
        renderReactionQueue(data.queue || []);
        renderReactionHistory(data.history || []);
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

function renderReactionSessionList(sessions, selectedSessions = new Set()) {
    const container = document.getElementById('reaction-session-list');
    const countInput = document.getElementById('reaction-session-count');
    if (!container) return;

    if (countInput) {
        countInput.max = Math.max(sessions.length, 1);
        countInput.value = Math.min(parseInt(countInput.value) || 1, Math.max(sessions.length, 1));
    }

    if (!sessions.length) {
        container.innerHTML = '<p style="color:#a1a1aa;margin:0;">Nenhuma sessão disponível.</p>';
        updateReactionSessionCounter();
        return;
    }

    container.innerHTML = sessions.map(session => {
        const details = [
            session.username ? `@${session.username}` : '',
            session.phone || '',
            session.reserved ? 'em tarefa, liberada para reação' : ''
        ].filter(Boolean).join(' • ');

        return `
            <label>
                <input type="checkbox" class="reaction-session-checkbox" value="${session.index}" ${selectedSessions.has(session.index) ? 'checked' : ''} onchange="updateReactionSessionCounter()">
                <span>
                    <strong>${escapeHtml(session.first_name || session.session_name || `Sessão ${session.index}`)}</strong>
                    <span>${escapeHtml(details || session.session_name || '')}</span>
                </span>
            </label>
        `;
    }).join('');

    updateReactionSessionCounter();
    enableCheckboxDragSelect('reaction-session-list', '.reaction-session-checkbox', updateReactionSessionCounter);
}

function renderReactionQueue(queue) {
    const container = document.getElementById('reaction-queue');
    if (!container) return;
    if (!queue.length) {
        container.innerHTML = '<p style="color:#a1a1aa;">Nenhuma reação pendente.</p>';
        return;
    }

    container.innerHTML = queue.map(item => `
        <div class="reaction-row">
            <div class="reaction-chip">${escapeHtml(item.reaction)}</div>
            <div>
                <strong>${escapeHtml(item.post_link)}</strong>
                <span>${escapeHtml(item.session_label)} • ${escapeHtml(item.created_at)}</span>
            </div>
            <span>Pendente</span>
            <a class="btn btn-primary" href="${escapeHtml(item.post_link)}" target="_blank" style="padding:8px 10px;text-decoration:none;">Abrir</a>
        </div>
    `).join('');
}

async function clearReactionQueue() {
    if (!confirm('Limpar todos os itens pendentes da fila?')) return;

    try {
        const response = await fetch('/api/reactions/queue/clear', {method: 'POST'});
        const data = await response.json();
        if (data.success) {
            showNotification(`${data.removed_count || 0} item(ns) removido(s) da fila`, 'success');
            loadReactions();
        } else {
            showNotification(data.error || 'Erro ao limpar fila', 'error');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

function renderReactionHistory(history) {
    const container = document.getElementById('reaction-history');
    if (!container) return;
    if (!history.length) {
        container.innerHTML = '<p style="color:#a1a1aa;">Histórico vazio.</p>';
        return;
    }

    container.innerHTML = history.slice(0, 50).map(item => `
        <div class="reaction-row">
            <div class="reaction-chip">${escapeHtml(item.reaction)}</div>
            <div>
                <strong>${escapeHtml(item.post_link)}</strong>
                <span>${escapeHtml(item.session_label)} • ${escapeHtml(item.executed_at || item.created_at)}</span>
            </div>
            <span>${item.status === 'reacted' ? 'Reagido' : item.status === 'waiting' ? 'Aguardando nova' : item.status === 'error' ? 'Erro' : escapeHtml(item.status)}</span>
            <a class="btn btn-primary" href="${escapeHtml(item.post_link)}" target="_blank" style="padding:8px 10px;text-decoration:none;">Ver</a>
        </div>
    `).join('');
}

function appendReactionLiveLog(item) {
    const container = document.getElementById('reaction-live-log');
    if (!container) return;

    const emptyText = container.querySelector('p');
    if (emptyText) emptyText.remove();

    const status = item.status || 'sending';
    const statusText = {
        sending: 'Enviando',
        reacted: 'Reagido',
        waiting: 'Aguardando',
        error: 'Erro'
    }[status] || status;

    const row = document.createElement('div');
    row.className = 'reaction-live-item';
    row.innerHTML = `
        <div class="reaction-chip">${escapeHtml(item.reaction || '')}</div>
        <div>
            <strong>${escapeHtml(item.session_label || 'Sessão')}</strong>
            <span>${escapeHtml(item.result || item.post_link || '')} • ${escapeHtml(item.time || new Date().toLocaleTimeString())}</span>
        </div>
        <div class="reaction-live-status ${escapeHtml(status)}">${escapeHtml(statusText)}</div>
    `;

    container.prepend(row);

    const rows = container.querySelectorAll('.reaction-live-item');
    rows.forEach((existingRow, index) => {
        if (index >= 80) existingRow.remove();
    });
}

function clearReactionLiveLog() {
    const container = document.getElementById('reaction-live-log');
    if (!container) return;
    container.innerHTML = '<p style="color:#a1a1aa;margin:0;">Aguardando execução.</p>';
}

function updateReactionMonitorButtons(isRunning) {
    const startButton = document.getElementById('start-reaction-monitor-btn');
    const stopButton = document.getElementById('stop-reaction-monitor-btn');
    if (startButton) startButton.style.display = isRunning ? 'none' : 'inline-flex';
    if (stopButton) stopButton.style.display = isRunning ? 'inline-flex' : 'none';
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function getAllReactionValues() {
    return Array.from(document.querySelectorAll('#reaction-picker input[type="checkbox"]'))
        .map(input => input.value)
        .filter(Boolean);
}

function normalizeCustomReaction(value) {
    return String(value || '').trim().slice(0, 16);
}

function renderCustomReactions() {
    const picker = document.getElementById('reaction-picker');
    const list = document.getElementById('custom-reactions-list');
    if (!picker) return;

    picker.querySelectorAll('.custom-reaction-option').forEach(option => option.remove());

    customReactions.forEach(reaction => {
        const label = document.createElement('label');
        label.className = 'custom-reaction-option';
        label.innerHTML = `<input type="checkbox" value="${escapeHtml(reaction)}"> <span>${escapeHtml(reaction)}</span>`;
        picker.appendChild(label);
    });

    if (!list) return;
    if (!customReactions.length) {
        list.innerHTML = '<span style="color:#93a4b8;font-size:12px;">Nenhuma reação personalizada ainda.</span>';
        return;
    }

    list.innerHTML = customReactions.map((reaction, index) => `
        <span class="custom-reaction-chip">
            ${escapeHtml(reaction)}
            <button type="button" onclick="removeCustomReactionAt(${index})" title="Remover reação">×</button>
        </span>
    `).join('');
}

async function persistCustomReactions() {
    await saveReactionSettings();
}

async function addCustomReaction() {
    const valueInput = document.getElementById('custom-reaction-value');
    const reaction = normalizeCustomReaction(valueInput?.value);

    if (!reaction) {
        showNotification('Digite a reação que deseja adicionar', 'warning');
        return;
    }

    if (getAllReactionValues().includes(reaction) || customReactions.includes(reaction)) {
        showNotification('Essa reação já está na lista', 'warning');
        return;
    }

    customReactions.push(reaction);
    renderCustomReactions();
    const addedInput = Array.from(document.querySelectorAll('#reaction-picker input[type="checkbox"]'))
        .find(input => input.value === reaction);
    if (addedInput) addedInput.checked = true;

    if (valueInput) valueInput.value = '';

    try {
        await persistCustomReactions();
        showNotification('Reação personalizada adicionada', 'success');
    } catch (error) {
        showNotification(`Erro ao salvar reação: ${error.message}`, 'error');
    }
}

async function removeCustomReactionAt(index) {
    customReactions.splice(index, 1);
    renderCustomReactions();

    try {
        await persistCustomReactions();
        showNotification('Reação personalizada removida', 'success');
    } catch (error) {
        showNotification(`Erro ao salvar reações: ${error.message}`, 'error');
    }
}

function getSelectedReactions() {
    return Array.from(document.querySelectorAll('#reaction-picker input[type="checkbox"]:checked'))
        .map(input => input.value)
        .filter(Boolean);
}

function getSelectedReactionSessions() {
    return Array.from(document.querySelectorAll('.reaction-session-checkbox:checked'))
        .map(input => parseInt(input.value))
        .filter(index => Number.isInteger(index));
}

function getReactionLinks() {
    const linkInput = document.getElementById('reaction-link');
    return String(linkInput?.value || '')
        .replaceAll(',', '\n')
        .split('\n')
        .map(link => link.trim())
        .filter((link, index, list) => link && list.indexOf(link) === index)
        .slice(0, 50);
}

function updateReactionSessionCounter() {
    const counter = document.getElementById('reaction-session-counter');
    if (!counter) return;

    const selected = getSelectedReactionSessions().length;
    const total = reactionAvailableSessions.length;
    counter.textContent = `${selected} de ${total} sessão(ões) selecionada(s)`;
}

function setReactionSessionSelection(indexes) {
    const selected = new Set(indexes);
    document.querySelectorAll('.reaction-session-checkbox').forEach(input => {
        input.checked = selected.has(parseInt(input.value));
    });
    updateReactionSessionCounter();
}

function applyReactionSessionLimit() {
    const countInput = document.getElementById('reaction-session-count');
    const requestedCount = Math.max(1, parseInt(countInput?.value) || 1);
    const indexes = reactionAvailableSessions
        .slice(0, requestedCount)
        .map(session => session.index);
    setReactionSessionSelection(indexes);
}

function selectAllReactionSessions() {
    setReactionSessionSelection(reactionAvailableSessions.map(session => session.index));
}

function clearReactionSessions() {
    setReactionSessionSelection([]);
}

function selectPositiveReactions() {
    const positives = new Set(['👍', '❤️', '🔥', '👏', '🎉']);
    document.querySelectorAll('#reaction-picker input[type="checkbox"]').forEach(input => {
        input.checked = positives.has(input.value);
    });
}

function clearReactionSelection() {
    document.querySelectorAll('#reaction-picker input[type="checkbox"]').forEach(input => {
        input.checked = false;
    });
}

async function saveReactionSettings() {
    const delaySeconds = parseInt(document.getElementById('reaction-delay').value) || 5;
    const disableAddGroupInteractions = document.getElementById('reaction-disable-add-interactions').checked;
    await fetch('/api/reactions/settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            delay_seconds: delaySeconds,
            disable_add_group_interactions: disableAddGroupInteractions,
            custom_reactions: customReactions
        })
    });
}

async function addReactionToQueue() {
    try {
        await saveReactionSettings();
        const sessionIndexes = getSelectedReactionSessions();
        const postLinks = getReactionLinks();
        const reactions = getSelectedReactions();

        if (!sessionIndexes.length || !postLinks.length || !reactions.length) {
            showNotification('Selecione sessão(ões), ao menos um canal/link e ao menos uma reação', 'warning');
            return;
        }

        const response = await fetch('/api/reactions/queue', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_indexes: sessionIndexes,
                post_links: postLinks,
                reactions
            })
        });
        const data = await response.json();
        if (data.success) {
            document.getElementById('reaction-link').value = '';
            showNotification(`${data.count || (sessionIndexes.length * postLinks.length)} item(ns) criado(s) para ${data.targets_count || postLinks.length} alvo(s). Reagindo automaticamente...`, 'success');
            await executeAllReactions(true);
        } else {
            showNotification(data.error || 'Erro ao adicionar reação', 'error');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

async function executeNextReaction() {
    try {
        clearReactionLiveLog();
        await saveReactionSettings();
        const response = await fetch('/api/reactions/execute-next', {method: 'POST'});
        const data = await response.json();
        if (data.success) {
            showNotification(data.item.status === 'error' ? `Erro: ${data.item.result}` : 'Próxima reação enviada automaticamente', data.item.status === 'error' ? 'error' : 'success');
            loadReactions();
        } else {
            showNotification(data.error || 'Nenhuma reação pendente', 'warning');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

async function executeAllReactions(silent = false) {
    if (!silent && !confirm('Executar todos os itens da fila com delay configurado?')) return;
    try {
        clearReactionLiveLog();
        await saveReactionSettings();
        const delaySeconds = parseInt(document.getElementById('reaction-delay').value) || 5;
        const response = await fetch('/api/reactions/execute-all', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({delay_seconds: delaySeconds})
        });
        const data = await response.json();
        if (data.success) {
            const errors = (data.executed || []).filter(item => item.status === 'error').length;
            const waiting = (data.executed || []).filter(item => item.status === 'waiting').length;
            const reacted = (data.executed || []).filter(item => item.status === 'reacted').length;
            showNotification(
                errors || waiting
                    ? `${reacted} reação(ões) enviadas, ${waiting} aguardando mensagem nova, ${errors} com erro`
                    : `${reacted} reação(ões) enviadas automaticamente`,
                errors ? 'warning' : 'success'
            );
            loadReactions();
        } else {
            showNotification(data.error || 'Erro ao executar fila', 'error');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

async function startContinuousReactions() {
    try {
        await saveReactionSettings();
        clearReactionLiveLog();

        const sessionIndexes = getSelectedReactionSessions();
        const postLinks = getReactionLinks();
        const reactions = getSelectedReactions();
        const pollSeconds = Math.max(15, parseInt(document.getElementById('reaction-delay').value) || 15);

        if (!sessionIndexes.length || !postLinks.length || !reactions.length) {
            showNotification('Selecione sessão(ões), ao menos um canal/link e ao menos uma reação', 'warning');
            return;
        }

        const response = await fetch('/api/reactions/continuous/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_indexes: sessionIndexes,
                post_links: postLinks,
                reactions,
                poll_seconds: pollSeconds
            })
        });
        const data = await response.json();
        if (data.success) {
            updateReactionMonitorButtons(true);
            showNotification('Reações contínuas iniciadas', 'success');
        } else {
            showNotification(data.error || 'Erro ao iniciar reações contínuas', 'error');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

async function stopContinuousReactions() {
    try {
        const response = await fetch('/api/reactions/continuous/stop', {method: 'POST'});
        const data = await response.json();
        if (data.success) {
            updateReactionMonitorButtons(false);
            showNotification('Reações contínuas parando', 'success');
        } else {
            showNotification(data.error || 'Erro ao parar reações contínuas', 'warning');
        }
    } catch (error) {
        showNotification(`Erro: ${error.message}`, 'error');
    }
}

// Visualizar logs do sistema
async function viewSystemLogs() {
    try {
        showLoading('Carregando logs...');
        const response = await fetch('/api/system/logs/view');
        const data = await response.json();
        hideLoading();
        
        if (data.success) {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.innerHTML = `
                <div class="modal" style="max-width: 90%; max-height: 90vh;">
                    <div class="modal-header">
                        <h3>📋 Logs do Sistema (${data.total_lines} linhas)</h3>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                    </div>
                    <div class="modal-body">
                        <pre style="background: #000; color: #0f0; padding: 20px; border-radius: 10px; max-height: 70vh; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 12px;">${data.logs}</pre>
                    </div>
                    <div class="modal-footer">
                        <a href="/api/system/logs" class="btn btn-success" download="system.log">
                            <i class="fas fa-download"></i> Baixar Completo
                        </a>
                        <button class="btn btn-primary" onclick="this.closest('.modal-overlay').remove()">
                            <i class="fas fa-times"></i> Fechar
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.remove();
            });
        } else {
            showNotification('Erro ao carregar logs: ' + data.error, 'error');
        }
    } catch (error) {
        hideLoading();
        showNotification('Erro ao carregar logs: ' + error.message, 'error');
    }
}

// Logs de tarefas já são tratados pelo evento task_log acima

// Init
loadConfig();
loadWarmingGroups();
document.addEventListener('DOMContentLoaded', () => {
    startPanelLiveRefresh();
});

// ========== ADVANCED FEATURES ==========

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K para busca rápida
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        showQuickSearch();
    }
    
    // ESC para fechar modais
    if (e.key === 'Escape') {
        closeTaskFormPanel();
        closeAllModals();
    }
});

// Quick search modal
function showQuickSearch() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal" style="max-width: 500px;">
            <div class="modal-header">
                <h3>🔍 Busca Rápida</h3>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
            </div>
            <div class="modal-body">
                <div class="search-box">
                    <i class="fas fa-search"></i>
                    <input type="text" id="quick-search-input" placeholder="Digite para buscar..." autofocus>
                </div>
                <div id="quick-search-results" style="margin-top: 20px;"></div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    // Click fora fecha
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
    
    // Busca em tempo real
    document.getElementById('quick-search-input').addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const results = document.getElementById('quick-search-results');
        
        if (query.length < 2) {
            results.innerHTML = '<p style="color: #94a3b8; text-align: center;">Digite pelo menos 2 caracteres...</p>';
            return;
        }
        
        // Busca em tabs
        const tabs = ['config', 'sessions', 'tasks', 'extract', 'add', 'warming', 'reactions', 'stats', 'help'];
        const matches = tabs.filter(tab => tab.includes(query));
        
        if (matches.length > 0) {
            results.innerHTML = matches.map(tab => `
                <div style="padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 10px; margin-bottom: 8px; cursor: pointer; transition: all 0.2s;" 
                     onclick="document.querySelector('[data-tab=\\'${tab}\\']').click(); this.closest('.modal-overlay').remove();"
                     onmouseover="this.style.background='rgba(59, 130, 246, 0.2)'"
                     onmouseout="this.style.background='rgba(59, 130, 246, 0.1)'">
                    <i class="fas fa-arrow-right" style="color: #60a5fa; margin-right: 10px;"></i>
                    <strong style="color: #f1f5f9;">${tab.charAt(0).toUpperCase() + tab.slice(1)}</strong>
                </div>
            `).join('');
        } else {
            results.innerHTML = '<p style="color: #94a3b8; text-align: center;">Nenhum resultado encontrado</p>';
        }
    });
}

function closeAllModals() {
    document.querySelectorAll('.modal-overlay').forEach(modal => modal.remove());
}

// Confirmação visual melhorada
function confirmAction(message, onConfirm) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal" style="max-width: 450px;">
            <div class="modal-header">
                <h3>⚠️ Confirmação</h3>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
            </div>
            <div class="modal-body">
                <p style="font-size: 1.1em; color: #cbd5e1;">${message}</p>
            </div>
            <div class="modal-footer">
                <button class="btn btn-primary" onclick="this.closest('.modal-overlay').remove()">
                    <i class="fas fa-times"></i> Cancelar
                </button>
                <button class="btn btn-danger" onclick="confirmActionExecute()">
                    <i class="fas fa-check"></i> Confirmar
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    window.confirmActionExecute = () => {
        modal.remove();
        onConfirm();
    };
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

// Loading overlay
function showLoading(message = 'Processando...') {
    const loading = document.createElement('div');
    loading.className = 'loading-overlay';
    loading.id = 'global-loading';
    loading.innerHTML = `
        <div class="loading-content">
            <div class="loading-spinner"></div>
            <div class="loading-text">${message}</div>
        </div>
    `;
    document.body.appendChild(loading);
}

function hideLoading() {
    const loading = document.getElementById('global-loading');
    if (loading) loading.remove();
}

// Export data
async function exportAllData() {
    showLoading('Exportando dados...');
    
    try {
        const sessions = await fetch('/api/sessions').then(r => r.json());
        const tasks = await fetch('/api/tasks').then(r => r.json());
        const stats = await fetch('/api/members/stats').then(r => r.json());
        
        const exportData = {
            export_date: new Date().toISOString(),
            sessions: sessions.sessions,
            tasks: tasks.tasks,
            stats: stats
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `telegram_automation_backup_${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        
        hideLoading();
        showNotification('Backup exportado com sucesso!', 'success');
    } catch (error) {
        hideLoading();
        showNotification('Erro ao exportar dados: ' + error.message, 'error');
    }
}

// System health check
async function checkSystemHealth() {
    const health = {
        api_configured: false,
        active_sessions: 0,
        pending_tasks: 0,
        warnings: []
    };
    
    try {
        const config = await fetch('/api/config').then(r => r.json());
        health.api_configured = config.configured;
        
        if (!health.api_configured) {
            health.warnings.push('API não configurada');
        }
        
        const sessions = await fetch('/api/sessions').then(r => r.json());
        health.active_sessions = sessions.sessions.filter(s => s.active).length;
        
        if (health.active_sessions === 0) {
            health.warnings.push('Nenhuma sessão ativa');
        }
        
        const tasks = await fetch('/api/tasks').then(r => r.json());
        health.pending_tasks = tasks.tasks.filter(t => t.status === 'pending').length;
        
        return health;
    } catch (error) {
        health.warnings.push('Erro ao verificar sistema');
        return health;
    }
}

// Show system status in header
async function updateSystemStatus() {
    const health = await checkSystemHealth();
    
    let statusHtml = '<div class="quick-stats">';
    
    statusHtml += `
        <div class="quick-stat">
            <i class="fas fa-server"></i>
            <div>
                <div class="quick-stat-value">${health.api_configured ? '🟢' : '🔴'}</div>
                <div class="quick-stat-label">API</div>
            </div>
        </div>
    `;
    
    statusHtml += `
        <div class="quick-stat">
            <i class="fas fa-users"></i>
            <div>
                <div class="quick-stat-value">${health.active_sessions}</div>
                <div class="quick-stat-label">Sessões</div>
            </div>
        </div>
    `;
    
    statusHtml += `
        <div class="quick-stat">
            <i class="fas fa-tasks"></i>
            <div>
                <div class="quick-stat-value">${health.pending_tasks}</div>
                <div class="quick-stat-label">Tarefas</div>
            </div>
        </div>
    `;
    
    statusHtml += '</div>';
    
    // Adiciona ao header se existir
    const header = document.querySelector('header');
    
    if (!header) {
        console.warn('Header não encontrado, pulando atualização de status');
        return;
    }
    
    let statusDiv = document.getElementById('system-status');
    
    if (!statusDiv) {
        statusDiv = document.createElement('div');
        statusDiv.id = 'system-status';
        statusDiv.style.marginTop = '30px';
        header.appendChild(statusDiv);
    }
    
    statusDiv.innerHTML = statusHtml;
}

// Aguarda o DOM estar pronto antes de executar
document.addEventListener('DOMContentLoaded', function() {
    // Update status on load and every minute
    updateSystemStatus();
    setInterval(updateSystemStatus, 60000);

    // Add keyboard shortcut hint
    const shortcutHint = document.createElement('div');
    shortcutHint.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(15, 23, 42, 0.95);
        padding: 12px 18px;
        border-radius: 12px;
        border: 1px solid rgba(59, 130, 246, 0.3);
        color: #94a3b8;
        font-size: 13px;
        z-index: 1000;
        backdrop-filter: blur(10px);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    `;
    shortcutHint.innerHTML = `
        <i class="fas fa-keyboard"></i> 
        <strong style="color: #60a5fa;">Ctrl+K</strong> para busca rápida
    `;
    document.body.appendChild(shortcutHint);

    // Hide hint after 5 seconds
    setTimeout(() => {
        shortcutHint.style.transition = 'opacity 0.5s';
        shortcutHint.style.opacity = '0';
        setTimeout(() => shortcutHint.remove(), 500);
    }, 5000);

    console.log('%c🚀 Telegram Automation System', 'color: #3b82f6; font-size: 20px; font-weight: bold;');
    console.log('%cSistema carregado com sucesso!', 'color: #10b981; font-size: 14px;');
    console.log('%cAtalhos: Ctrl+K (Busca) | ESC (Fechar)', 'color: #94a3b8; font-size: 12px;');

    // Reset automático de locks ao carregar a página
    fetch('/api/system/reset-locks', { method: 'POST' })
        .then(r => r.json())
        .then(data => console.log('Locks resetados:', data.message))
        .catch(e => console.error('Erro ao resetar locks:', e));
});
