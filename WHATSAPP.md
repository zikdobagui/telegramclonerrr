# WhatsApp nos destinos de clonagem

## Uso

1. Abra **WhatsApp** no menu do painel e clique em **Conectar WhatsApp**.
2. No celular, abra **Aparelhos conectados → Conectar aparelho** e leia o QR Code. O QR é privado à conta autenticada e não é salvo em arquivo ou log pelo aplicativo.
3. Clique em **Carregar meus grupos**. Grupos com envio exclusivo de administradores são indicados.
4. Na criação ou edição de uma clonagem, use **Enviar também para o WhatsApp → Carregar meus grupos** e marque até cinco destinos. Salve a clonagem e inicie-a. Sem destinos selecionados, o comportamento anterior do Telegram é preservado.
5. Consulte **WhatsApp → Envios da clonagem** para acompanhar fila, confirmações e problemas.

O destino Telegram continua obrigatório. O conteúdo modificado pela clonagem entra na fila do WhatsApp após o envio ao Telegram. Textos, fotos, vídeos e documentos são suportados, com limite de 16 MB por mídia. A conversão de formatação é básica, não uma reprodução perfeita do layout do Telegram. Os grupos de um álbum são tratados como os posts individuais recebidos pelo monitor existente.

## Biblioteca e ambiente

- `neonize==0.10.0`, versão publicada no PyPI e inspecionada diretamente em Python 3.13. Usa o núcleo Go do whatsmeow sem Chromium e sem processo Node adicional.
- [Biblioteca e código](https://github.com/krypton-byte/neonize), [autenticação e reconexão](https://github.com/krypton-byte/neonize/blob/master/docs/getting-started/authentication.md), [plataformas e instalação](https://github.com/krypton-byte/neonize/blob/master/docs/getting-started/installation.md).
- Integração não oficial: alterações do WhatsApp, restrições e revogação do aparelho podem exigir novo QR. Não há garantia de conexão permanente ou de ausência de bloqueios.
- Discloud: Python 3.13 mantido; `APT=tools, ffmpeg` e `BUILD` explícito para instalar os requisitos e a biblioteca de reconhecimento de mídia isolada. [APT na Discloud](https://docs.discloud.com/en/configurations/discloud.config/apt).
- O pareamento não depende mais do libmagic do sistema nem de instalação em `.runtime`. Quando `python-magic` não carrega, `whatsapp_mime.py` oferece as duas funções usadas pela Neonize (`from_buffer` e `from_file`). A identificação usa `filetype==1.2.0`, biblioteca Python sem dependência nativa, com assinaturas básicas de mídia como fallback. O import do detector é tardio: sua ausência não impede gerar o QR. O build voltou à instalação normal de `requirements.txt`.
- A resolução de dependências para Linux x86-64 / Python 3.13 / glibc 2.28 foi conferida, exigindo wheels dos componentes binários principais; pyaes permanece como dependência Python construída a partir de fonte, como no projeto existente. Isso não equivale a um teste executado dentro do container Discloud.

O deploy instala `requirements.txt` e usa o APT de FFmpeg para mídia. Não é necessário instalar um libmagic à parte para conectar a conta. Não apague os dados nem recrie a aplicação. O workflow valida a importação real da Neonize em Linux/Python 3.13, simulando ausência total de libmagic, antes de enviar o pacote à Discloud.

## Persistência e reconexão

Cada usuário tem um diretório `data_dir/whatsapp/`, ignorado pelo Git, com `auth.sqlite`, `connection.json`, `outbox.sqlite` e mídias temporárias. O build e o pacote versionado não incluem esse conteúdo. A hospedagem precisa preservar o diretório de dados durante reinícios e atualizações.

Uma conexão habilitada é restaurada pelo supervisor no início de `python app.py`; as tentativas de reconexão de uma conexão encerrada são espaçadas. Eventos de perda de rede são tratados pela reconexão do cliente. Revogação de aparelho ou substituição por outro processo desabilitam a restauração automática até ação do usuário. **Desconectar** solicita logout do aparelho, invalida imediatamente o pareamento local e remove os arquivos de autenticação anteriores após encerrar o cliente. A próxima conexão usa um banco de autenticação novo e precisa de outro QR Code. Se o WhatsApp estiver inacessível, o logout remoto pode falhar, mas as credenciais locais antigas não voltam a ser utilizadas; confira também Aparelhos conectados no celular. O histórico de envios é preservado.

Use uma única instância do aplicativo contra cada conjunto de sessões. Não execute múltiplos workers compartilhando o mesmo diretório de dados. O identificador nativo de cada conexão é novo a cada inicialização; o pareamento é preservado pelo banco do usuário, evitando que o descarte de um objeto antigo encerre a conexão substituta.

Padrão conservador para o servidor atual de 512 MB: até três conexões simultâneas (`WHATSAPP_MAX_DEVICES` permite ajustar), uma por usuário. O consumo real de RAM, especialmente com vídeos, deve ser acompanhado na Discloud; a cota não foi aumentada automaticamente.

## Fila e limites

- Até 200 entregas pendentes por usuário, com intervalo mínimo de três segundos entre envios de uma conta; cinco grupos significam cinco entregas.
- Até 128 MB em mídias temporárias por usuário. Arquivos compartilhados entre destinos são removidos após o último envio/encerramento que precise deles; órfãos são limpos posteriormente.
- Pendências sobrevivem a reinícios e aguardam a reconexão. Após sete dias sem envio, expiram e ficam registradas como falha; histórico é mantido por 30 dias.
- Chave única por clonagem, canal de origem, mensagem e destino impede uma segunda entrada para o mesmo evento.
- Mensagens com envio iniciado, mas sem confirmação, ficam **Sem confirmação**. Não há repetição automática, pois uma falha de rede pode ocorrer depois de o WhatsApp aceitar o post. Reinício durante envio também produz esse estado.
- Uma falha ao preparar mídia/fila é mostrada na aba WhatsApp; não desfaz nem repete o envio já feito ao Telegram. Isso deixa explícito o limite: não há transação única entre as duas redes, e uma queda entre o aceite do Telegram e a gravação na fila pode exigir revisão manual.
- O usuário só pode selecionar JIDs de grupos previamente carregados por sua própria conexão. Somente destinos `@g.us` são aceitos; não há envio arbitrário a números pessoais, ingresso automático ou importação de sessões externas.

O supervisor restaura a conexão WhatsApp e a fila. O mecanismo anterior de monitoramento Telegram não foi reescrito: depois de um reinício, confira e inicie as clonagens conforme o funcionamento anterior do painel. Novos posts só entram na fila se o monitor Telegram estiver ativo.

## Validação

Execução inicial: **165 testes aprovados** na suíte completa em Python 3.13, incluindo **22 testes específicos** desta integração. A revisão do progresso adiciona testes para timeout, rotação do QR, diagnósticos e imagem autenticada.

Revisão do progresso: **170 testes aprovados**, incluindo **27 específicos** da integração. O teste de interface pode ser repetido com `node tests/test_whatsapp_progress.cjs` a partir da raiz do projeto.

- Testes específicos sem conexões reais: autenticação, isolamento, QR, contrato da Neonize, destinos na criação/edição, fotos, limites de mídia, deduplicação, concorrência, persistência, estados ambíguos e limpeza de arquivos compartilhados.
- Sintaxe Python, JavaScript e CSS, renderização Jinja, IDs únicos, labels e navegação conferidos. JavaScript inline da página renderizada também passa na checagem de sintaxe.
- Compatibilidade sem libmagic exercitada em subprocesso limpo com o núcleo real da Neonize; PNG e JPEG reconhecidos sem biblioteca nativa e sem usar `.runtime`. O mesmo teste faz parte do workflow Linux.
- Na revisão do progresso, uma sessão temporária sem conta vinculada recebeu um QR real do WhatsApp no Windows. O fluxo completo de status e rota autenticada de PNG foi exercitado, a imagem foi validada e a conexão encerrada. Nenhum QR foi lido, aparelho vinculado ou post enviado a grupos reais. Validação visual em navegador e teste real de reconexão na Discloud continuam pendentes.

## Revisão do QR e progresso

Ao clicar em conectar, o painel mostra imediatamente animação, botão ocupado, tempo decorrido e as etapas de preparação do aparelho, obtenção do QR, leitura no celular e conexão concluída. O estado vem das fases reais do backend: carregamento da biblioteca, abertura da sessão e contato com o WhatsApp.

Requisições HTTP têm timeout de 12 segundos. Tentativas nativas que permanecem sem progresso por 75 segundos são interrompidas e exibem diagnóstico, em vez de manter carregamento indefinido. QR expirado é ocultado e aguarda renovação. A captura do QR usa o callback nativo e também o evento QR como fallback, sem repetir a mesma revisão.

`GET /api/whatsapp/qr` serve PNG somente ao usuário autenticado dono da sessão, com cache desabilitado. A imagem usa a própria origem do site, evitando depender de permissão a imagens `data:` no navegador. O POST de conectar retorna a fase atual; respostas antigas de polling não podem sobrescrever uma nova tentativa. Erros de rede, dependência, armazenamento, versão obsoleta e recusa do WhatsApp recebem códigos específicos, sem expor caminhos internos ou tokens.

Verificação frontend em DOM simulado com o JavaScript real: carregamento imediato, etapas, imagem PNG, erro/timeout, corrida de polling e cancelamento de HTTP lento. Isso não substitui revisão visual no navegador nem comprova a causa específica da falha no servidor da Discloud.

## Correção após rebuild

A mensagem anterior `WA_DEPENDENCY_MISSING` agrupava causas diferentes e recomendava rebuild sem evidência de que isso resolveria. Removida a instalação especial de libmagic da inicialização; o caminho de fallback foi testado sem biblioteca nativa, sem diretório `.runtime` e também sem o detector opcional instalado.

Falhas de import agora identificam o nome do módulo ausente quando disponível. Incompatibilidade GLIBC recebe `WA_NATIVE_ABI`, com as versões exigida e existente, em vez da recomendação de reinstalar o mesmo pacote. O binário Linux da wheel Neonize 0.10.0 foi inspecionado e referencia símbolos até GLIBC 2.34, apesar da tag manylinux2014; a resolução do pip por si só não comprova compatibilidade com servidores mais antigos. A versão do Linux efetivamente usada pelo servidor Discloud não foi acessada diretamente.

Ao salvar destinos, uma seleção que não está no cache é confirmada consultando os grupos da conta conectada. A lista é vinculada à geração do pareamento; respostas e eventos atrasados de conexões anteriores não podem restaurar ou apagar os grupos atuais. Destinos não confirmados na conta atual continuam bloqueados.
