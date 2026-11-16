# Verificar membros visíveis

Aba **Membros visíveis** no painel e atalho **Verificar grupos** na visão geral.

1. Cole a lista exportada ou importe um arquivo `.txt`/`.csv`, com um grupo por linha. Links escapados como `https\://t.me/grupo\` são normalizados. Nome, contagem e ID na linha são preservados para exportação; a consulta usa o link, não esses metadados.
2. Clique em **Analisar lista** para conferir links únicos, repetidos e linhas inválidas.
3. Selecione sessões da própria conta e a quantidade **total** de grupos. Em branco: todos os links únicos, até 500 por execução. Até 20 sessões selecionadas, distribuição sequencial e intervalo de 2 segundos entre grupos.
4. Inicie. A visualização padrão mostra somente os grupos confirmados como visíveis. Outros filtros mostram ocultos, sem acesso e erros/inconclusivos.
5. **Copiar grupos e membros** e **Baixar visíveis (.txt)** usam o mesmo formato: `Nome do grupo | Membros: 2113 | https://t.me/grupo`. A quantidade vem da consulta ao Telegram; quando ausente, aparece `não informado`. Somente grupos confirmados como visíveis entram na cópia e no arquivo. Uma nova execução substitui a anterior.

## Critério

O verificador consulta metadados do grupo. Se `participants_hidden` estiver ativo, classifica como oculto; permissão negada fica separada. Nos supergrupos, confirma a consulta com uma solicitação limitada a um participante, sem salvar informações pessoais. Retorno vazio é inconclusivo. Canais de transmissão não são classificados como grupos. Grupos básicos usam os metadados de participantes disponíveis; grupos migrados exigem o link atual.

Referências oficiais: [channelFull](https://core.telegram.org/constructor/channelFull) e [channels.getParticipants](https://core.telegram.org/method/channels.getParticipants).

O resultado é relativo à sessão usada e ao momento da consulta, e não garante que todas as contas vejam todos os membros. Não entra em grupos, não solicita participação e não envia mensagens. Convites privados são verificados somente se a sessão já participa. Nenhum dado de participante é persistido.

## Execução e isolamento

Rotas autenticadas em `/api/group-visibility`: status, preview, start, cancel e export. Os nomes selecionados são confrontados com o cadastro do usuário e os arquivos são restritos ao diretório de sessões dele, com ou sem a extensão `.session` no cadastro.

Processamento em background; uma verificação por usuário, integrada aos bloqueios existentes. O cancelamento aguarda a consulta atual e a desconexão. FloodWait interrompe toda a execução e registra o prazo no arquivo de flood existente, sem continuar em outra sessão. Último resultado salvo em `data_dir/group_visibility.json`; após reinício, uma execução incompleta fica interrompida, mantendo resultados parciais. Não há retomada automática.

## Validação — 15/11/2026

- 16 testes específicos aprovados: parser, duplicados, autenticação, isolamento, exportação, recuperação, nomes de sessão, consultas mínimas, ocultos, permissão negada, canais, convites privados, flood e encerramento do worker.
- Suíte completa: 141 testes aprovados na execução de regressão; os dois últimos ajustes também foram conferidos pela suíte específica de 16 testes.
- Bloqueios de operações exercitados isoladamente, nos dois sentidos, com isolamento por usuário.
- Sintaxe Python, JavaScript e CSS conferida; painel em Flask isolado retorna HTTP 200, IDs únicos e destinos válidos de labels e navegação.
- O primeiro teste geral falhou por ausência de `tzdata` no ambiente temporário; repetido com a dependência já declarada no projeto e aprovado.

Não foram acessadas sessões reais nem realizadas consultas aos grupos fornecidos. Validação com Telegram usa mocks. Revisão visual em navegador pendente pela indisponibilidade do host de acesso ao navegador nesta sessão.

Atualização: corrigido o rótulo `Membros visíveis` no menu, que continha um `?` literal no lugar do acento. Cópia e download agora compartilham a formatação produzida no servidor, inclusive para resultados já salvos. Testes verificam correspondência entre o texto da cópia e o arquivo, contagem zero, quantidade ausente e exclusão de ocultos.
