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
- `python-magic-standalone==0.4.29` é instalado em `.runtime/libmagic`, fora dos requisitos globais. É usado apenas se `python-magic` não conseguir encontrar o libmagic do sistema. A instalação isolada evita sobreposição de arquivos entre os dois pacotes. `.runtime/` fica fora do Git. [Pacote de compatibilidade](https://pypi.org/project/python-magic-standalone/).
- A resolução de dependências para Linux x86-64 / Python 3.13 / glibc 2.28 foi conferida, exigindo wheels dos componentes binários principais; pyaes permanece como dependência Python construída a partir de fonte, como no projeto existente. Isso não equivale a um teste executado dentro do container Discloud.

O deploy precisa executar o novo BUILD e instalar o APT de FFmpeg. Se a atualização de arquivos não refizer o ambiente, execute o rebuild no painel da Discloud. Não apague os dados nem recrie a aplicação para isso.

## Persistência e reconexão

Cada usuário tem um diretório `data_dir/whatsapp/`, ignorado pelo Git, com `auth.sqlite`, `connection.json`, `outbox.sqlite` e mídias temporárias. O build e o pacote versionado não incluem esse conteúdo. A hospedagem precisa preservar o diretório de dados durante reinícios e atualizações.

Uma conexão habilitada é restaurada pelo supervisor no início de `python app.py`; as tentativas de reconexão de uma conexão encerrada são espaçadas. Eventos de perda de rede são tratados pela reconexão do cliente. Revogação de aparelho ou substituição por outro processo desabilitam a restauração automática até ação do usuário. **Desconectar** pausa a conexão local e preserva o pareamento; remover o vínculo de fato é feito no celular.

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

Resultado final: **165 testes aprovados** na suíte completa em Python 3.13, incluindo **22 testes específicos** desta integração.

- Testes específicos sem conexões reais: autenticação, isolamento, QR, contrato da Neonize, destinos na criação/edição, fotos, limites de mídia, deduplicação, concorrência, persistência, estados ambíguos e limpeza de arquivos compartilhados.
- Sintaxe Python, JavaScript e CSS, renderização Jinja, IDs únicos, labels e navegação conferidos. JavaScript inline da página renderizada também passa na checagem de sintaxe.
- Fallback de libmagic exercitado em subprocesso isolado no Windows, simulando ausência da biblioteca de sistema e um loader antigo em cache; MIME e importação da Neonize confirmados sem conectar ao WhatsApp.
- Nenhum QR real foi gerado ou lido, nenhum aparelho foi conectado e nenhum post foi enviado a grupos reais durante os testes. Validação visual em navegador e teste real de reconexão na Discloud continuam pendentes.
