-- DETECTOR DE RODÍZIO (Anti-coincidência)
-- Detecta fornecedores que se alternam em padrão suspeito

-- Passo 1: Criar view de contratos mensalizada
DROP VIEW IF EXISTS vw_contratos_mensal;
CREATE VIEW vw_contratos_mensal AS
SELECT
    fornecedor,
    orgao,
    TO_CHAR(TO_DATE(data_assinatura, 'DD/MM/YYYY'), 'YYYY-MM') AS mes,
    COUNT(*) AS qtd_contratos,
    SUM(valor) AS total_valor
FROM sp_contratos
WHERE data_assinatura IS NOT NULL
GROUP BY fornecedor, orgao, TO_CHAR(TO_DATE(data_assinatura, 'DD/MM/YYYY'), 'YYYY-MM');

-- Passo 2: Criar matriz de co-ocorrência esperada vs real
DROP TABLE IF EXISTS matriz_rodizio;
CREATE TABLE matriz_rodizio AS
WITH pares AS (
    SELECT DISTINCT
        LEAST(a.fornecedor, b.fornecedor) AS fornecedor_a,
        GREATEST(a.fornecedor, b.fornecedor) AS fornecedor_b,
        a.orgao
    FROM vw_contratos_mensal a
    JOIN vw_contratos_mensal b ON a.orgao = b.orgao AND a.mes = b.mes
    WHERE a.fornecedor < b.fornecedor
),
co_real AS (
    SELECT
        p.fornecedor_a,
        p.fornecedor_b,
        p.orgao,
        COUNT(DISTINCT a.mes) AS meses_juntos,
        SUM(a.qtd_contratos + b.qtd_contratos) AS contratos_totais
    FROM pares p
    JOIN vw_contratos_mensal a ON p.fornecedor_a = a.fornecedor AND p.orgao = a.orgao
    JOIN vw_contratos_mensal b ON p.fornecedor_b = b.fornecedor AND p.orgao = b.orgao AND a.mes = b.mes
    GROUP BY p.fornecedor_a, p.fornecedor_b, p.orgao
),
co_esperado AS (
    SELECT
        fornecedor_a,
        fornecedor_b,
        orgao,
        -- Probabilidade de co-ocorrência se independentes
        (SELECT COUNT(DISTINCT mes) FROM vw_contratos_mensal WHERE orgao = p.orgao) * 
        (SELECT COUNT(DISTINCT mes) FROM vw_contratos_mensal WHERE fornecedor = p.fornecedor_a AND orgao = p.orgao) / 
        NULLIF((SELECT COUNT(DISTINCT mes) FROM vw_contratos_mensal WHERE orgao = p.orgao), 0) *
        (SELECT COUNT(DISTINCT mes) FROM vw_contratos_mensal WHERE fornecedor = p.fornecedor_b AND orgao = p.orgao) / 
        NULLIF((SELECT COUNT(DISTINCT mes) FROM vw_contratos_mensal WHERE orgao = p.orgao), 0)
        AS esperado
    FROM pares p
)
SELECT
    cr.fornecedor_a,
    cr.fornecedor_b,
    cr.orgao,
    cr.meses_juntos AS co_real,
    COALESCE(ce.esperado, 0) AS co_esperado,
    cr.contratos_totais,
    CASE 
        WHEN COALESCE(ce.esperado, 0) > 5 AND cr.meses_juntos = 0 THEN 1.0  -- Exclusão total
        WHEN COALESCE(ce.esperado, 0) > 0 THEN 
            GREATEST(0, 1 - (cr.meses_juntos / COALESCE(ce.esperado, 1)))
        ELSE 0
    END AS indice_exclusao,
    CASE
        WHEN COALESCE(ce.esperado, 0) > 5 AND cr.meses_juntos = 0 THEN 'RODIZIO_FORTE'
        WHEN COALESCE(ce.esperado, 0) > 5 AND cr.meses_juntos < ce.esperado * 0.3 THEN 'RODIZIO_SUSPEITO'
        WHEN COALESCE(ce.esperado, 0) > 0 AND cr.meses_juntos > ce.esperado * 1.5 THEN 'COINCIDENCIA_ALTA'
        ELSE 'NORMAL'
    END AS classificacao
FROM co_real cr
LEFT JOIN co_esperado ce ON cr.fornecedor_a = ce.fornecedor_a 
    AND cr.fornecedor_b = ce.fornecedor_b 
    AND cr.orgao = ce.orgao;

-- Índices para performance
CREATE INDEX idx_rodizio_a ON matriz_rodizio(fornecedor_a);
CREATE INDEX idx_rodizio_b ON matriz_rodizio(fornecedor_b);
CREATE INDEX idx_rodizio_class ON matriz_rodizio(classificacao);

-- Consultar top suspeitos
SELECT * FROM matriz_rodizio 
WHERE classificacao IN ('RODIZIO_FORTE', 'RODIZIO_SUSPEITO')
ORDER BY indice_exclusao DESC
LIMIT 20;
