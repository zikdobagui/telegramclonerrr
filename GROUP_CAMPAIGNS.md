# Tarefas de grupos

A aba que antes se chamava **Em breve** agora reúne criação de grupos, aquecimento e distribuição de leads. Salvar uma tarefa não executa ações no Telegram; a execução começa em **Iniciar / continuar**.

## Uso

1. Importe leads em JSON (`members` ou `leads`), CSV com cabeçalhos `id`, `username`, `phone`, `access_hash`, ou TXT com um username por linha. É possível importar novos arquivos enquanto uma tarefa está ativa. A importação soma registros ao banco, sem substituir os anteriores.
2. Crie a tarefa com nome, quantidade de grupos (1 a 30), sessões e limite diário. Os grupos recebem o nome da tarefa com um número sequencial.
3. Escolha se cada lead pode ser usado apenas uma vez na tarefa ou uma vez por grupo. Na segunda opção, a troca de um grupo conserva o histórico daquela posição da tarefa.
4. Se habilitar aquecimento, informe os dias, intervalo em minutos e frases (digitadas ou importadas de TXT, uma por linha). Cada grupo começa a receber leads depois do seu aquecimento.
5. Inicie a tarefa. Sem leads ou após consumir a cota diária, ela aguarda. As cotas renovam à meia-noite de São Paulo; o histórico de deduplicação permanece.
6. Para alterar limites ou substituir um grupo, pause e aguarde a operação em andamento terminar. Informe o link do substituto ou deixe vazio para criar outro ao continuar. O grupo antigo não é apagado do Telegram. Os leads usados e a cota consumida continuam registrados.

## Persistência e execução

- Os dados ficam em `group_campaigns.db` no diretório de dados de cada usuário. Inclua esse banco nos backups. Não remova o banco para reiniciar uma tarefa: ele contém o histórico que impede repetições.
- Uma tarefa de grupos executa por usuário de cada vez. É possível salvar outras tarefas enquanto uma está ativa. As operações anteriores que verificam o bloqueio de sessões aguardam a pausa desta tarefa.
- A execução usa o processo único de `python app.py`, conforme o Procfile atual. O registro de workers e os bloqueios de sessões são locais a esse processo; não executar múltiplos processos de aplicação sobre o mesmo banco.
- Depois de reiniciar o servidor, tarefas ficam pausadas para retomada manual. Criações interrompidas exigem revisar o Telegram e vincular o grupo existente para evitar criar uma cópia.
- A deduplicação utiliza ID, username e telefone disponíveis na importação, além de uma reserva única pelo ID resolvido no Telegram antes do convite. Os hashes numéricos do JSON são lidos no Python, preservando sua precisão.
- Resultados sem confirmação ficam reservados e não são reenviados automaticamente. Eles contam na cota do dia como precaução. Falhas definitivas também permanecem no histórico, sem novas tentativas automáticas.
- Restrições de sessão e FloodWait pausam a tarefa. Erros de acesso a um grupo deixam esse grupo para revisão; os demais podem continuar.
- O grupo substituto precisa ser um supergrupo acessível, com permissão para gerar convite e adicionar participantes. As sessões precisam estar autorizadas. O Telegram pode recusar convites conforme as permissões e a privacidade do usuário; a resposta é verificada antes de contabilizar sucesso. Referência: [API de convite do Telegram](https://core.telegram.org/method/channels.inviteToChannel).

## Validação local

```text
python -m unittest discover -s tests -v
python -m py_compile app.py group_campaigns.py
node --check static/group_campaigns.js
```

O teste opcional `python tests/browser_group_campaigns.py` usa Playwright/Chromium e um banco temporário para conferir os formulários. Os testes não criam grupos nem adicionam pessoas no Telegram.
