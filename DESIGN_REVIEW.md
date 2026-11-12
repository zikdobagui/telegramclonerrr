# Revisão de design — 12/11/2026

`GATE: OPEN 18 (rounds used up)` — a auditoria automática de composição não passou integralmente.

Aplicadas as skills [Taste Skill](https://github.com/Leonxlnx/taste-skill) e
[Web Design Guidelines](https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines).
As diretrizes da Vercel foram consultadas na fonte durante esta revisão.

## Alterações

- Apresentação refeita com o tema sorteado `teal-on-paper`, fontes Familjen Grotesk / IBM Plex Mono,
  composição centralizada e prévia do produto em HTML. Não foram inventados clientes, depoimentos ou resultados.
- Login e cadastro mantêm os endpoints existentes; adicionados controles de visibilidade da senha,
  indicação de envio, bloqueio de envio duplicado e semântica de abas e mensagens.
- Dashboard e abas recebem cores, tipografia, campos, cartões e botões consistentes.
- Menu mobile tem Escape, contenção de foco e atualização de `aria-expanded`.
  O menu fechado ou recolhido fica `inert`, sem links invisíveis na sequência de Tab.
- Seções do painel passam a ter links com fragmentos reais e estado na URL.
- Notificações têm títulos em português, anúncios para leitores de tela e botão de fechar de 44 px.
- Mantidas animações de entrada e interação; o efeito sorteado `word-highlight` marca a sequência de trabalho.
  Preferência por movimento reduzido é respeitada. Sem WebGL, carrossel ou reprodução automática.
- Apenas os recursos usados do kit são distribuídos: aproximadamente 224 KB.

## Verificações realizadas

- Apresentação e painel retornam HTTP 200 em servidor Flask isolado.
- Sintaxe JavaScript dos scripts inline, de `experience.js` e de `script.js` conferida com Node.
- Identificadores anteriores do dashboard preservados; endpoints `/api/auth/login` e `/api/auth/register` preservados.
- Campos de acesso conferidos: rótulos associados, nomes, autocomplete, IDs únicos e atributos sem duplicação.
- Capturas em Chrome headless pelas ferramentas da Taste Skill; desktop, tablet e celular.
- Verificador de layout executado nas resoluções 1440×900, 1024×768, 820×1180, 768×1024 e 390×844.
- Três rodadas do gate; a primeira rodada identificou sobreposição do login com o rodapé, já corrigida.

## Limites e decisões

A prévia usa dados vazios e um nome de demonstração. Não importa a aplicação de produção,
não lê sessões de usuários e recusa requisições que alterem dados. Autenticação real, operações
do Telegram e conexões de produção não foram exercitadas. As capturas do painel mostram o aviso
esperado de ausência de conexão com os logs nesse servidor de prévia.

O verificador da Taste Skill aplica uma grade editorial rígida, exige imagens em seções de formulário
e um rodapé de tela inteira, e usa heurísticas de texto que não reconhecem todos os títulos em português.
O site mantém um rodapé compacto e um formulário sem imagem decorativa, em função do pedido de uso simples.
Há também apontamentos de alinhamento e ritmo que permanecem abertos; não foram declarados como aprovados.
Não foram criadas exceções no arquivo de waivers nem alterados os verificadores.

Após a última rodada, o espaço da prévia mobile foi aumentado para evitar o corte de uma linha,
e o contraste inicial do texto animado foi reforçado. Essas duas correções foram verificadas nas
capturas finais; o gate completo não foi repetido além das três rodadas previstas pela skill.

## Backups

- Versão original completa: `../telegram-site-backup-20261112-193758.zip`.
- Templates e arquivos estáticos antes desta aplicação das skills:
  `../telegram-design-before-skills-20261112-200742/`.

As capturas e os resultados brutos dos verificadores ficam em `.taste-skill/`, excluída do versionamento.
Os apontamentos completos da última rodada estão abaixo.

## GATE: OPEN — apontamentos brutos

- **no-visual** — `main#top > section.hero.hero--centred "Automação para seu Telegram."`: no picture, effect or mock in this section; a feature section needs a visual
- **no-visual** — `section#recursos "Recursos para sua rotina."`: no picture, effect or mock in this section; a feature section needs a visual
- **no-visual** — `section#acesso "Tudo pronto para sua próxima tarefa."`: no picture, effect or mock in this section; a feature section needs a visual
- **copy-headings** — `h2#resources-title "Recursos para sua rotina."`: "Recursos para sua rotina." names no product, part, place or section (5 headings like it; at most one brand line per page) (and 4 more like it: "Extraia com filtros", "Consulte os resultados", "Defina a operação", "Veja o andamento")
- **section-height** — `footer.marketing-footer "TG AutoTelegram AutomationVer recursos ↑"`: the section is 109px tall (0.1 screens), 791px short of one screen (900px): every section after the hero is one screen or two, 2px either way (SR-2)
- **one-section** — `footer.marketing-footer "TG AutoTelegram AutomationVer recursos ↑"`: the screen at scroll 2809px (the top of section 5) shows 109px of section 5 and the content of 2 sections, over 24px each beside section 4: a screen shows one section (another may peek 8px, 24px WARN) (SR-4)
- **container-edges** — `footer.marketing-footer "TG AutoTelegram AutomationVer recursos ↑"`: a <footer> at the top of the page, outside header.nav, main, footer.closing and nav.actionbar (SR-6)
- **container-edges** — `div.product-main > div.product-title > div > p.product-heading "Sua central de operações."`: 1 text block starts on a left line at x 399, 319px from the container's left: text starts on the container's left, or on one split line (x 623, 732, 841) (SR-6)
- **row-lines** — `div.product-window.app-frame > div.product-body > div.product-main > div.product-steps "Conecte suas sessõesContas organizadas p"`: a row of 3 items: its first item starts at 399px, the container's left line at 80px; its last item ends at 1225px, the container's right line at 1360px (2px either way) (SR-7)
- **split-pair** — `section#acesso > div.wrap.access-grid "Seu espaço de trabalhoTudo pronto parasu"`: the split's columns are off the page's one pair of lines: its right column starts at x 880, on none of the split lines 623 (k=5), 732 (k=6), 841 (k=7) (SR-8)
- **cut-text** — `div.product-main > div.product-steps > div.preview-step:nth-of-type(3) > strong "Acompanhe resultados"`: cut 6px at the bottom by the overflow of section.hero.hero--centred > div.wrap > div.hero-text > div.hero__window.product-ground
- **no-visual** — `section#acesso "Tudo pronto parasua próxima tarefa."`: no picture, effect or mock in this section; a feature section needs a visual
- **off-grid** — `div.resource-grid > article.resource-card:nth-of-type(4) > div.resource-tags > span:nth-of-type(2) "Registros"`: left edge at 105.5px, 21.5px off a common edge of its section at 84px (3 elements, like span:nth-of-type(2))
- **edge-left** — `#recursos p "Da organização das contas ao aco"`: starts at x 972.4; the lines are 80 and the column starts
- **edge-left** — `#acesso aside.auth-card.login-card "Acesso seguro Acessar seu painel"`: starts at x 880; the lines are 80 and the column starts
- **edge-left** — `footer.marketing-footer span "Telegram Automation"`: starts at x 643.4; the lines are 80 and the column starts
- **edge-left** — `footer.marketing-footer a "Ver recursos ↑"`: starts at x 1261.3; the lines are 80 and the column starts
- **neighbour** — `#recursos section.section.resources "As ferramentas da sua rotinaRecu"`: framed, 124px of #fluxo section.section.workflow-section "Como funcionaConecte suas contas" shows

## Avisos mantidos

- **scroll-reveal** — `h2#flow-title "Conecte suas contas. Prepare suas tarefa"`: starts "color" (0.2 s) the moment it is scrolled into view (an IntersectionObserver) on span.mo-w:nth-of-type(6) (inside a dealt moment's section, [data-moment]: an enter moment is expected on every kind; its still is judged under reduced motion)
- **copy-buttons** — `header.nav > div.wrap.nav__bar > div.nav__actions > a.btn.btn--primary "Acessar painel ↗"`: "Acessar painel ↗" does not start with a verb (book, buy, try, start, get, see...) (and 1 more like it: "Entrar")
- **copy-actions** — `(the page)`: the main action "Acessar painel" does not read word for word the same in the closing section
- **stagger** — `div.hero__window.product-ground > div.product-window.app-frame > div.product-body > div.product-sidebar "Visão geral Sessões Tarefas Estatísticas"`: 4 rows start at 2 different left offsets (+30, +0, +0, +0px)
- **nav-labels** — `div.wrap.nav__bar > nav.nav__links > div.nav__item:nth-of-type(2) > a.nav__link "Como funciona"`: "Como funciona" opens a section headed "Conecte suas contas. Prepare suas tarefas. Acompan"
- **label-centre** — `form#loginForm > button.btn.btn--primary "Entrar"`: its label sits 24px off-centre (197px of room at the left, 173px at the right)
- **copy-length** — `section#recursos "Recursos para sua rotina."`: 1 section over 90 words a screen outside the UI mocks ("Recursos para sua rotina" 102); 70 words a screen across the page (279 words in 4 screens): a tech page says it in about 80 or fewer
- **grounds** — `section.hero.hero--centred > div.wrap > div.hero-text > div.hero__window.product-ground "TG Auto Seu espaço de trabalho ● ● ● Vis"`: 4 flat grounds across the page (#f7f9f8 section x2, #dfece7 band, #edf2ef section, #06525c section): three at most (the base, a surface, an inverse)
- **skip-link** — `header.nav > div.wrap.nav__bar > a.skip-link:nth-of-type(1) "Pular para o conteúdo"`: the first Tab stop is "Pular para o conteúdo", not a skip link: a keyboard user tabs through the whole nav on every visit
- **share-meta** — `head`: the head lacks og:image, twitter:card: a shared link shows no picture or title of its own
- **action-repeat** — `header.nav > div.wrap.nav__bar > div.nav__actions > a.btn.btn--primary "acessar painel"`: "acessar painel" shows 2 times on the first screen at 1440px (nav, hero): the nav's button and the hero's; nothing else on the screen may repeat it
- **form-fields** — `form#loginForm`: the form has no status line (role="status"): sending, sent and errors are never read out
- **section-air** — `section#recursos "As ferramentas da sua rotinaRecursos par"`: the content fills 51.6% of the section's height (464 of 900px): 55% or more (40% WARN) (SR-3)
- **cta** — `section#recursos "Recursos para sua rotina."`: a section over 1.5 screens long with no link or button in it
- **heading-scale** — `h3#authTitle "Acessar seu painel"`: h3 headings in 2 sizes, 22px ("Organize suas sessões") to 26px (x1.18)
- **grounds** — `section.hero.hero--centred > div.wrap > div.hero-text > div.hero__window.product-ground "TG Auto ● ● ● Visão geral Sua central de"`: 4 flat grounds across the page (#f7f9f8 section x3, #dfece7 band, #edf2ef section, #06525c section): three at most (the base, a surface, an inverse)
- **fold-cut** — `div.product-main > div.product-title > div > p.product-heading "Sua central de operações."`: a line of the hero text is sliced by the bottom of the first screen
- **copy-rhythm** — `(the copy)`: every sentence about 10 words long (spread 3.5)

Waivers: nenhum. Preços, endereços, domínio canônico e dados de clientes não foram presumidos. Fotografias não foram necessárias para este produto operacional.

## Desempenho final da pagina real

Resultado do perf.mjs: 0 FAIL, 4 WARN, nas larguras 1440 e 390.
Sem requisicoes quebradas, sem tarefas longas e CLS 0.000 nas medicoes locais.
Na apresentacao, icones foram convertidos para SVGs locais: ficaram duas familias tipograficas, com cerca de 33 KiB de fontes.
Avisos mantidos: peso do CSS completo do kit e carregamento imediato de um SVG de 2 KiB usado como logo.
Estes numeros foram medidos em Chrome local e nao representam dados de usuarios em producao.
Depois do gate, tambem foram removidas as fontes de icones da apresentacao e o botao de menu desnecessario; em tablets os links ficam visiveis.
A auditoria de composicao continua registrada como OPEN; desempenho nao substitui essa auditoria.
