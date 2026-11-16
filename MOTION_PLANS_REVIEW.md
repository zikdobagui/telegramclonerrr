# Animações e planos — 15/11/2026

## Planos na página pública e login

Incluída a seção pública `#planos` antes do formulário de acesso, com link no menu, os mesmos três cartões animados e prefixos próprios para os detalhes. Adicionados estilos públicos para cartões, botões e superfícies, sem depender das variáveis do painel autenticado. Autenticação e cadastro preservados. Validação isolada: três planos na página pública, seis no painel, IDs únicos, destinos de detalhes, formulários e recursos locais existentes. Conferência visual continua pendente.

## Planos na visão geral

Adicionados os três cartões de planos logo após os indicadores do painel principal. `plan_cards.html` é compartilhado com a aba de planos; cada inclusão recebe um prefixo diferente para os IDs dos detalhes. Adicionados elementos 3D em camadas nos cartões, entrada sequencial na visão geral e botão para abrir a aba completa. Preços, limites e contratação permanecem explicitamente indisponíveis. Corrigido também texto com caracteres corrompidos na apresentação dos planos.

Validação: HTTP 200, seis cartões renderizados, IDs únicos, seis controles de detalhe com destinos existentes, posição dos planos antes dos gráficos, sintaxe JavaScript e CSS. Conferência visual em navegador continua pendente.

## Revisão 3D solicitada

Esta revisão substitui o controle de pausa descrito abaixo: o botão e a leitura da preferência de pausa foram removidos a pedido do usuário. Apenas a preferência de movimento reduzido do sistema permanece. O pedido explícito também orienta a inclinação 3D dos cartões e as animações contínuas sem controle visível, em lugar das restrições padrão da skill.

Adicionada uma cena CSS 3D compartilhada com cubo de seis faces, órbitas e cartões flutuantes na apresentação, no resumo do painel e na aba de planos. Cards de recursos, indicadores e planos respondem ao ponteiro com inclinação limitada e iluminação localizada. Não há bibliotecas novas ou modelos externos. O movimento reduzido mostra uma composição estática.

Verificados novamente: sintaxe JavaScript com Node, CSS com tinycss2, HTTP 200, recursos locais, IDs únicos, inclusão das cenas e ausência do botão. A inspeção visual continua pendente pela indisponibilidade do navegador; estes checks não comprovam a aparência final em dispositivos reais.

## Registro da revisão anterior

GATE: ERROR — conferência visual pendente; o host do navegador não está disponível nesta sessão.

Skill aplicada: design-taste-frontend, com referências de movimento e cartões. Mantidos o tema grafite/azul, a tipografia e a estrutura operacional existentes.

- Transição finita ao abrir abas, entrada sequencial dos indicadores e planos, respostas ao hover/pressionamento e um destaque luminoso por página.
- Controle de pausa persistido no navegador; preferência por movimento reduzido respeitada. A pausa não interfere nas operações do aplicativo.
- Nova aba `#plans`, integrada à navegação existente, com três modelos ilustrativos e detalhes expansíveis. Sem preços presumidos, pagamentos, contratação ou mudança de permissões.
- Verificados: sintaxe JavaScript com Node, sintaxe CSS com tinycss2, resposta HTTP 200 nas duas páginas, carregamento dos recursos locais, IDs únicos e destinos das abas e detalhes. Verificados em ambiente simulado os controles de expansão e de pausa/retomada.

Limites: animações, layout mobile, foco e aparência final ainda precisam de conferência visual em navegador. A prévia Flask é isolada de dados reais e não importa o aplicativo de produção. Nenhuma operação Telegram foi exercitada. Nenhuma exceção foi criada para os verificadores de design.
