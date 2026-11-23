# Movimento da interface

As p√°ginas completas `login.html` e `index.html` incluem `interface_assets.html`. Todas as abas, os formul√°rios e os modais do painel herdam a mesma camada visual. As listas de tarefas continuam compactas.

- ReactBits: `ShinyText` nos t√≠tulos est√°ticos e `SpotlightCard` como ilumina√ß√£o decorativa em superf√≠cies. As fontes oficiais e a licen√ßa ficam em `frontend/reactbits`; `UPSTREAM.json` registra o commit e cada URL. A consulta ao registry retornou HTTP 403, por isso os arquivos foram obtidos diretamente do reposit√≥rio oficial, sem reconstru√ß√£o de mem√≥ria.
- GSAP: entradas curtas, troca de abas, abertura de detalhes e modais. O conte√∫do das tarefas, os valores ao vivo e os logs n√£o s√£o reanimados a cada atualiza√ß√£o.
- Lenis: rolagem da p√°gina pelo mesmo ticker do GSAP. Toque continua nativo; sidebar, modais, tabelas, logs, selects e textareas s√£o exclu√≠dos da suaviza√ß√£o.

Os componentes React s√£o ilhas de apresenta√ß√£o. N√£o gerenciam autentica√ß√£o, dados, formul√°rios, a√ß√µes de Telegram ou APIs. Os t√≠tulos e controles continuam presentes no HTML original caso o bundle n√£o carregue. Movimento reduzido desativa os efeitos e o Lenis; mudan√ßas dessa prefer√™ncia em tempo de execu√ß√£o preservam os valores dos campos. Listeners, ra√≠zes React, contextos GSAP e o ticker s√£o limpos ao sair da p√°gina e restaurados ao voltar pelo cache de navega√ß√£o.

## Build

```powershell
npm ci --ignore-scripts
npm run build:ui
python tests/browser_interface.py
python tests/browser_group_campaigns.py
```

As vers√µes est√£o fixadas no `package-lock.json`. `static/ui/` cont√©m o bundle e CSS compilados e as licen√ßas; o servidor Flask n√£o precisa executar Node ou consultar CDN para essa camada. O build minificado tem aproximadamente 377 KB de JavaScript (126 KB com gzip).

O teste da interface renderiza os templates reais em um Flask isolado e substitui as APIs por respostas de teste. Cobre as 16 abas, desktop/celular, navega√ß√£o por √¢ncoras, teclado, campos preservados e mudan√ßa de movimento reduzido, sem conectar contas reais. Capturas e observa√ß√µes ficam em `.runtime/interface/` e n√£o s√£o publicadas no Git.

## Skills instaladas

Foram revisadas e instaladas globalmente no ambiente do usu√°rio:

- [react-bits](https://github.com/Philotheephilix/reactbits.dev-skill/tree/main/react-bits)
- [gsap-web](https://github.com/iart-ai/web-animation-skills/tree/main/skills/gsap-web)
- [lenis-core](https://github.com/saikiranreddy18/Lenis-Agent-Skills/tree/main/lenis-core)
- [lenis-gsap](https://github.com/saikiranreddy18/Lenis-Agent-Skills/tree/main/lenis-gsap)

As instru√ß√µes dessas skills foram usadas nesta implementa√ß√£o e ficam dispon√≠veis para as pr√≥ximas conversas.

## Movimento ampliado no painel

No index, tÌtulos usam brilho recorrente; cabeÁalhos recebem um campo de partÌculas conectadas e gradiente em movimento. O canvas usa o mesmo ticker do GSAP/Lenis e sÛ desenha quando o cabeÁalho est· visÌvel; abas ocultas e a preferÍncia de movimento reduzido n„o mantÍm esse desenho ativo. Brilho e bordas dos cards reagem mais ao mouse; botıes prim·rios tÍm uma faixa de luz, e o menu ativo tem fundo animado. Entradas usam deslocamento de 36 px, duraÁ„o de 700 ms e sequÍncia de 75 ms. As listas compactas, n˙meros de produÁ„o e logs n„o recebem loops de entrada.

A apresentaÁ„o p˙blica tambÈm recebe a constelaÁ„o animada no hero, brilho recorrente do tÌtulo, luz ambiente na prÈvia do produto, entrada em sequÍncia mais ampla, parallax da prÈvia e efeitos de entrada nos recursos, planos e acesso. Os efeitos n„o dependem de autenticaÁ„o.
