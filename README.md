# Inview

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

- Ainda não extrai itens nem inclui OCR, autenticação, dashboard ou IA generativa.
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
  documentos devem ter seu próprio conjunto de campos e validações. Dashboard
  consumirá somente faturas confirmadas, sempre separando moedas.

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
