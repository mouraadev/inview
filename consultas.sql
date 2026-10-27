SELECT fornecedor, moeda, SUM(total) AS valor_faturado, COUNT(*) AS faturas
FROM faturas GROUP BY fornecedor, moeda ORDER BY moeda, valor_faturado DESC;

SELECT DATE_FORMAT(data_emissao, '%Y-%m') AS mes, moeda, SUM(total) AS valor_faturado
FROM faturas GROUP BY mes, moeda ORDER BY mes, moeda;
SELECT data_vencimento, moeda, COUNT(*) AS faturas, SUM(total) AS valor_faturado
FROM faturas WHERE data_vencimento IS NOT NULL
GROUP BY data_vencimento, moeda ORDER BY data_vencimento;

SELECT chave_negocio, COUNT(*) AS ocorrencias
FROM faturas GROUP BY chave_negocio HAVING COUNT(*) > 1;
