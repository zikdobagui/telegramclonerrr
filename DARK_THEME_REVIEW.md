# Tema dark — 15/11/2026

GATE: ERROR — auditoria visual automática não executada: Node não disponível no PATH e o host de acesso ao navegador está indisponível nesta sessão.

Aplicado na apresentação, autenticação e painel existente. Tipo: software. Paleta solicitada: grafite com azul elétrico, mantendo Familjen Grotesk e IBM Plex Mono. A prévia do produto permanece em HTML, com a animação existente word-highlight. Não foram acrescentadas ferramentas ou operações.

O arquivo compartilhado `static/dark.css` define superfícies, navegação, botões, formulários e cartões. O painel ganha destaque azul no resumo, hierarquia tipográfica mais forte e proporção mais ampla para a área principal. A apresentação recebe cartões delimitados, prévia dark e título com destaque. Os dois temas existentes continuam disponíveis.

Verificação em servidor Flask isolado: apresentação e painel retornam HTTP 200; todos os estilos locais carregam; os IDs são únicos nas duas páginas. Nenhum endpoint de produção ou sessão Telegram foi utilizado. Manifesto e cor do navegador atualizados; versão do cache renovada.

Limite: responsividade e contraste foram tratados no CSS, mas não foram conferidos visualmente em navegador. A auditoria anterior em DESIGN_REVIEW.md não representa aprovação desta alteração. Não foram criadas exceções para o verificador.
