# Inview — direção visual fintech

Referência principal: captura da OKX enviada pelo usuário. Pesquisa em 27/10/2026.

## Leitura da referência

- Cabeçalho compacto: marca à esquerda, ações à direita.
- Fundo quase preto e textura orgânica de contraste baixo.
- Tipografia grande, poucas palavras e hierarquia clara.
- Verde-lima concentrado na mensagem e na ação principal.
- Botão arredondado com área de toque generosa.
- Números agrupados em cartão escuro com borda fina.

## Referências complementares consultadas

- [Revolut](https://www.revolut.com/): título curto, ação principal e apresentação
  dos usos do produto em seções. Referência para hierarquia de conteúdo.
- [Ramp](https://ramp.com/): proposta de valor curta e agrupamento dos fluxos
  financeiros. Referência para reduzir textos e destacar ações.
- [Mercury Insights](https://mercury.com/insights): métricas, gráficos e tabelas
  com filtros. Referência para manter a utilidade do dashboard.

Essas páginas são referências de produto e estrutura; a direção cromática vem
da captura fornecida. Não foram reproduzidos números comerciais, depoimentos,
alegações de segurança, marcas ou código dessas empresas.

## Aplicação

`web/fintech.css` define a nova camada visual sobre os componentes existentes.
Navegação horizontal, conteúdo em até 1400px, saldo projetado à esquerda e gráfico
à direita, indicadores em faixa única e detalhamento abaixo. No celular, as abas
têm rolagem horizontal e os cartões ficam em coluna.

Grafite #0b0d0b, superfícies #141812, destaque #c2f970. As gravuras originais em
SVG e a marca Inview continuam presentes. Ações secundárias são contornadas;
cores de entrada/saída também têm rótulos e sinais. Mantidos foco de teclado,
movimento reduzido, contraste aumentado e transparência reduzida.

Validação: arquivos servidos com HTTP 200 no cliente de teste Flask; todos os
IDs estáticos usados pelo JavaScript presentes; sintaxe JavaScript verificada;
37 testes passaram, 1 integração MySQL pulada por falta de configuração.
Revisão visual no navegador pendente nesta sessão: nenhum navegador estava
disponível para controle. A abertura da prévia foi solicitada no aplicativo.
