# Inview

## Dashboard financeiro — interface principal

O Inview agora reúne saldo disponível, previsão de saldo no fim do mês,
entradas, saídas, contas, categorias e compromissos mensais. A importação de
faturas PDF é uma função dentro desse planejamento.

Para abrir localmente, no PowerShell na pasta do projeto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe dashboard.py
```

Abra **http://127.0.0.1:8000**. Para parar, pressione Ctrl+C no terminal.
Não é necessário iniciar o Streamlit para usar o dashboard.

Clique em **Meu espaço → Meus dados** para começar seu cadastro pessoal sem
dados fictícios. Esse espaço usa `data/dashboard-local.json`, separado da demo,
e funciona sem MySQL. A escolha fica lembrada neste navegador. Nesse mesmo menu
estão a **Lixeira** (restauração) e **Baixar cópia dos dados** (JSON com documentos).
Para iniciar diretamente nesse modo, defina `$env:INVIEW_MODO = 'local'`.

Lançamentos, contas e recorrências possuem **Editar** e **Excluir**. Exclusões
vão para a lixeira e recalculam os saldos; PDFs originais são preservados.
Uma ocorrência recorrente pode ser corrigida ou excluída individualmente sem
alterar os outros meses. Editar a regra mensal altera as ocorrências não
confirmadas; meses já confirmados não são duplicados ao mudar o dia da regra.
Para desfazer uma confirmação, edite o lançamento e mude a situação para Previsto.
A moeda de uma conta não pode ser trocada e uma conta com movimentos ativos não
pode ser excluída. Pendências antigas aparecem em Planejamento e Lançamentos.

Como ainda não há MySQL instalado, o modo padrão é **demonstração**, claramente
identificado na tela. Salário, aluguel e assinaturas têm valores fictícios.
As alterações ficam em `data/dashboard-demo.json`, ignorado pelo Git. Este modo
serve para experimentar; não representa seus dados bancários e não se conecta
a bancos. Use apenas uma instância do servidor local por arquivo de dados.

- **Novo lançamento:** registre uma entrada ou saída, prevista ou realizada.
- **Planejamento:** cadastre recorrências mensais, valor, conta, categoria,
  primeiro mês e dia. Dias 29–31 se ajustam ao último dia de meses menores.
  Pausar remove as ocorrências ainda não realizadas da projeção; pagamentos
  confirmados são preservados. Reativar volta a gerar os meses desde o início.
- **Saldo projetado:** saldo realizado mais entradas previstas menos saídas
  previstas até o fim do mês escolhido. Atrasados são sinalizados e precisam
  de confirmação; não são automaticamente deslocados para uma nova data.
  Confirmar uma ocorrência registra a realização hoje, uma única vez.
- **Documentos:** extraia e revise os campos da fatura, escolha uma conta da
  mesma moeda e a data prevista. A confirmação cria um lançamento **previsto**,
  preserva o PDF original e bloqueia reimportação do mesmo arquivo.
- Filtros por mês, conta e moeda. BRL, USD e EUR nunca são somados entre si.

Interface própria em HTML/CSS/JavaScript, com Flask no Python. O design segue
tipografia de sistema, hierarquia clara, contraste verde/claro, navegação suave,
foco de teclado e preferências de movimento reduzido. Não há serviços pagos.

### Usar MySQL no dashboard

Após instalar/configurar o servidor como explicado abaixo, defina MYSQL_HOST,
MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER e MYSQL_PASSWORD no mesmo terminal:

```powershell
$env:INVIEW_MODO = 'mysql'
.\.venv\Scripts\python.exe dashboard.py --init-db
.\.venv\Scripts\python.exe dashboard.py
```

O banco começa vazio, com uma conta principal. Dados fictícios não são migrados.
Não há fallback silencioso quando a conexão MySQL falha. `financeiro.sql` cria
tabelas `fin_*` separadas do importador antigo. Valores são DECIMAL(18,2), atributos
são JSON; o protótipo serializa gravações com uma linha de controle transacional.
O PDF é armazenado em base64 junto ao registro do documento. `financeiro.py`
calcula valores com Decimal; `repositorio_financeiro.py` controla persistência.
O modo MySQL do dashboard ainda precisa de validação com servidor real.

Esta versão é local, para uma pessoa, sem login, integração bancária ou
transferência entre contas. Recorrências são mensais e
de valor fixo. Previsão é calculada pelos lançamentos cadastrados, sem estimativa
automática de despesas variáveis. O servidor escuta apenas em 127.0.0.1.

## Importador anterior — preservado

Aplicação local em Python para extrair sugestões de campos de faturas PDF,
conferir e corrigir os dados no Streamlit e confirmar registros no MySQL.
Não depende de templates por empresa. As regras reconhecem rótulos e proximidade
espacial; não garantem interpretação correta de qualquer layout.

## Executar a interface

No PowerShell, na pasta deste projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Se `.venv` já existe, não é necessário recriá-lo. A importação e a conferência
funcionam sem MySQL; salvar e consultar exigem conexão. O Streamlit informa o
endereço local, normalmente http://localhost:8501.

## MySQL local

Requer MySQL 8.4 ou Docker Desktop com Compose. Docker e MySQL não foram
instalados automaticamente. Com Docker disponível, configure as variáveis no
mesmo PowerShell usado para iniciar a aplicação:

```powershell
$env:MYSQL_HOST = '127.0.0.1'
$env:MYSQL_PORT = '3306'
$env:MYSQL_DATABASE = 'inview'
$env:MYSQL_USER = 'inview'
$env:MYSQL_PASSWORD = Read-Host 'Senha do usuário inview' -MaskInput
$env:MYSQL_ROOT_PASSWORD = Read-Host 'Senha administrativa do MySQL' -MaskInput
docker compose up -d --wait
.\.venv\Scripts\python.exe banco.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

`-MaskInput` requer PowerShell 7.1+. Em terminais anteriores, configure as senhas
nas variáveis de ambiente pela interface do Windows. Não coloque senhas no código
nem as publique. O Compose recebe as variáveis do terminal; a aplicação também.
Se já houver MySQL, configure as mesmas variáveis, crie um banco vazio e um usuário
com acesso a ele e execute `banco.py`; não precisa do Compose.

O volume `mysql_data` mantém os dados entre reinicializações. `docker compose stop`
para o serviço sem apagar o volume. As tabelas são criadas por `schema.sql`.
Executar `banco.py` novamente não apaga dados e não é um mecanismo de migração.

## Uso

1. Envie um PDF com texto selecionável, até 10 MB. PDF ilegível, sem texto ou com
   senha recebe uma mensagem de falha. OCR ainda não está disponível.
2. Confira o texto por página e baixe/abra o PDF original para conferir a aparência.
   O painel de evidências mostra todos os candidatos, rótulos e coordenadas.
3. Escolha explicitamente o formato monetário (`pt-BR`: `3.325,00`; `en-US`:
   `2,181.60`) e a ordem das datas com barras (`DMY` ou `MDY`). Datas ISO são aceitas.
   Esses formatos não são inferidos da moeda. Corrija campos e complete ausências.
4. Clique em **Validar e verificar duplicidade**. Campos com candidatos conflitantes
   começam vazios. Uma sugestão única também precisa de conferência humana.
5. Confirme que é uma fatura e, se necessário, reconheça os avisos ou a duplicidade.
   Clique em **Confirmar e salvar no MySQL**.
6. Em **Faturas confirmadas**, consulte as 200 confirmações mais recentes, baixe o
   PDF original e examine a extração e o histórico de correções.

Campos obrigatórios adotados para este recorte: fornecedor, número, emissão,
moeda e total. Identificador fiscal, vencimento, subtotal, descontos, tributos
adicionais e pedido de compra são opcionais. Um ID de teste não é identificador
fiscal. Ausência é `NULL`, não zero. Nenhum status de pagamento é inferido.

## Organização e decisões

- `inspecionar_pdf.py`: exercício original de leitura e inspeção, preservado.
- `extracao.py`: leitura de bytes, reconhecimento de rótulos compostos e busca de
  candidatos à direita/abaixo. Reutiliza `ler_pdf` do exercício. Limites espaciais
  são heurísticas em pontos do PDF, não percentuais de confiança.
- `validacao.py`: dinheiro em `Decimal`, datas em `date`, campos obrigatórios e
  avisos de consistência. Valores monetários aceitam até duas casas; casas extras
  são rejeitadas, sem arredondamento silencioso. Conversão nunca passa por `float`.
  Datas ambíguas exigem escolha explícita de DMY/MDY. Moedas: BRL, USD e EUR.
- `banco.py`: SQL direto parametrizado, para tornar consultas e transações
  explícitas. A confirmação insere documento e fatura em uma transação InnoDB;
  qualquer falha anterior ao commit executa rollback.
- `app.py`: interface de conferência, sem frontend separado ou serviços pagos.
- `consultas.sql`: total por fornecedor/moeda, evolução mensal, vencimentos e
  suspeitas de duplicidade. Os indicadores representam valor faturado, não pago.

`documentos` guarda o PDF original como BLOB, SHA-256 único e extração JSON imutável.
`faturas` tem relação 1:1 por `documento_id` (FK e UNIQUE), campos aprovados em tipos
SQL próprios e JSON de revisão com entradas, normalizados, alterações e decisões.
Guardar o PDF no banco simplifica a atomicidade neste recorte local de até 10 MB.

O hash bloqueia confirmação do mesmo arquivo, inclusive em concorrência. Uma chave
de negócio baseada em fornecedor normalizado e número sinaliza arquivos diferentes
que podem representar a mesma fatura. Ela não é única, pois duplicidade pode ser
aceita explicitamente. Um lock nomeado do MySQL serializa confirmações dessa chave.
Variações do nome do fornecedor ainda podem escapar da detecção; não há cadastro
de fornecedores ou deduplicação aproximada.

Há índices de emissão/moeda, vencimento e chave de negócio. Fornecedores permanecem
como texto neste recorte; um cadastro separado pode ser introduzido quando houver
regras de identificação estáveis. Antes da confirmação, a revisão fica na sessão
do navegador e pode se perder ao recarregar/fechar. Falhas de extração ainda não
ficam registradas de forma durável para estatísticas.

## Testes e amostras

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Testes verificam dinheiro, datas, ausências, associação espacial, resultados por
campo nos dois PDFs sintéticos, correções, reimportação e comportamento de transação
com conexão simulada. A interface é exercitada com o AppTest do Streamlit.
Os PDFs `inview_invoice_01_brl.pdf` e `inview_invoice_02_usd.pdf` são procurados em
Downloads ou na pasta indicada por `INVIEW_PDFS_TESTE`; se ausentes, somente esses
casos são pulados. PDFs não foram copiados nem versionados.

Para testar SQL e integridade em servidor real, configure as variáveis MYSQL_*
apontando **para um banco de teste separado** e execute:

```powershell
$env:INVIEW_TEST_MYSQL = '1'
.\.venv\Scripts\python.exe -m pytest tests/test_mysql_integracao.py -q
Remove-Item Env:INVIEW_TEST_MYSQL
```

O teste cria as tabelas se necessário, usa uma chave aleatória e remove somente os
registros que criou. Sem MySQL configurado esse teste é pulado; testes simulados
não substituem a execução contra MySQL.

## Limites e evolução

- O importador ainda não extrai itens nem inclui OCR, autenticação ou IA generativa.
- Fornecedor é sugerido pela primeira linha abaixo de rótulos como EMISSOR/FROM;
  layouts com nome à direita ou sem rótulo podem exigir preenchimento manual.
- Valores monetários sugeridos exigem duas casas decimais no texto. Campos fiscais
  são candidatos perto de rótulos explícitos, sem validar dígitos fiscais por país.
- Datas com mês escrito, texto rotacionado, valores divididos em palavras e rótulos
  em outros idiomas podem exigir preenchimento manual. Não há promessa de extração
  universal. Documentos sem a palavra FATURA/INVOICE recebem aviso de tipo.
- Total versus subtotal usa contexto de rótulos, excluindo cabeçalhos conhecidos da
  tabela de itens. Novos layouts devem entrar como casos de teste, sem mudar regras
  silenciosamente para favorecer só uma amostra.
- Tributos são tratados como adicionais na conferência aritmética. Diferença gera
  aviso, pois alguns documentos já os incluem no subtotal.
- Futuro OCR pode produzir a mesma estrutura de palavras e coordenadas. Outros
  documentos devem ter seu próprio conjunto de campos e validações. O dashboard
  usa faturas revisadas para gerar previsões, sempre separando moedas.

## Referências e dependências

- [pdfplumber](https://github.com/jsvine/pdfplumber): leitura e coordenadas; licença MIT.
- [Streamlit](https://docs.streamlit.io/develop/api-reference/execution-flow/st.form):
  formulários e revisão; licença Apache 2.0.
- [PyMySQL](https://pymysql.readthedocs.io/en/latest/user/examples.html): SQL
  parametrizado e transações; licença MIT. `cryptography` suporta autenticação moderna.
- [pytest](https://docs.pytest.org/): testes; licença MIT.
- [MySQL](https://dev.mysql.com/doc/refman/8.4/en/): banco obrigatório, executado
  separadamente. Distribuição Community sob GPLv2; consulte as licenças da imagem.
- [invoice2data](https://github.com/invoice-x/invoice2data): referência conceitual
  avaliada, licença MIT. Não é usado pelo fluxo atual, que dispensa templates por
  emissor. Não foram copiados seus templates, testes ou estrutura de projeto.

As referências informam a implementação; resultados esperados vêm dos PDFs
sintéticos. Não há métricas de precisão ou benefícios financeiros estimados.
