# Movimento da interface

As páginas completas `login.html` e `index.html` incluem `interface_assets.html`. Todas as abas, os formulários e os modais do painel herdam a mesma camada visual. As listas de tarefas continuam compactas.

- ReactBits: `ShinyText` nos títulos estáticos e `SpotlightCard` como iluminação decorativa em superfícies. As fontes oficiais e a licença ficam em `frontend/reactbits`; `UPSTREAM.json` registra o commit e cada URL. A consulta ao registry retornou HTTP 403, por isso os arquivos foram obtidos diretamente do repositório oficial, sem reconstrução de memória.
- GSAP: entradas curtas, troca de abas, abertura de detalhes e modais. O conteúdo das tarefas, os valores ao vivo e os logs não são reanimados a cada atualização.
- Lenis: rolagem da página pelo mesmo ticker do GSAP. Toque continua nativo; sidebar, modais, tabelas, logs, selects e textareas são excluídos da suavização.

Os componentes React são ilhas de apresentação. Não gerenciam autenticação, dados, formulários, ações de Telegram ou APIs. Os títulos e controles continuam presentes no HTML original caso o bundle não carregue. Movimento reduzido desativa os efeitos e o Lenis; mudanças dessa preferência em tempo de execução preservam os valores dos campos. Listeners, raízes React, contextos GSAP e o ticker são limpos ao sair da página e restaurados ao voltar pelo cache de navegação.

## Build

```powershell
npm ci --ignore-scripts
npm run build:ui
python tests/browser_interface.py
python tests/browser_group_campaigns.py
```

As versões estão fixadas no `package-lock.json`. `static/ui/` contém o bundle e CSS compilados e as licenças; o servidor Flask não precisa executar Node ou consultar CDN para essa camada. O build minificado tem aproximadamente 377 KB de JavaScript (126 KB com gzip).

O teste da interface renderiza os templates reais em um Flask isolado e substitui as APIs por respostas de teste. Cobre as 16 abas, desktop/celular, navegação por âncoras, teclado, campos preservados e mudança de movimento reduzido, sem conectar contas reais. Capturas e observações ficam em `.runtime/interface/` e não são publicadas no Git.

## Skills instaladas

Foram revisadas e instaladas globalmente no ambiente do usuário:

- [react-bits](https://github.com/Philotheephilix/reactbits.dev-skill/tree/main/react-bits)
- [gsap-web](https://github.com/iart-ai/web-animation-skills/tree/main/skills/gsap-web)
- [lenis-core](https://github.com/saikiranreddy18/Lenis-Agent-Skills/tree/main/lenis-core)
- [lenis-gsap](https://github.com/saikiranreddy18/Lenis-Agent-Skills/tree/main/lenis-gsap)

As instruções dessas skills foram usadas nesta implementação e ficam disponíveis para as próximas conversas.
