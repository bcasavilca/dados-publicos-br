-- CATEGORIZAÇÃO HÍBRIDA V1.0
-- Classificação por regras com pesos + confiança

-- 1. TABELA DE REGRAS (versionada)
DROP TABLE IF EXISTS categoria_regras CASCADE;
CREATE TABLE categoria_regras (
    id SERIAL PRIMARY KEY,
    versao INT NOT NULL DEFAULT 1,
    categoria TEXT NOT NULL,
    keyword TEXT NOT NULL,
    peso INT NOT NULL CHECK (peso > 0),
    ativa BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para performance
CREATE INDEX idx_regras_versao ON categoria_regras(versao);
CREATE INDEX idx_regras_categoria ON categoria_regras(categoria);

-- 2. CONJUNTO INICIAL DE REGRAS (calibrado para contratos públicos BR)
INSERT INTO categoria_regras (versao, categoria, keyword, peso) VALUES
-- OBRAS (alta prioridade)
(1, 'OBRAS', 'construcao', 3),
(1, 'OBRAS', 'reforma', 2),
(1, 'OBRAS', 'obra', 3),
(1, 'OBRAS', 'edificacao', 3),
(1, 'OBRAS', 'pavimentacao', 3),
(1, 'OBRAS', 'infraestrutura', 2),
(1, 'OBRAS', 'civil', 2),
(1, 'OBRAS', 'predial', 2),

-- TECNOLOGIA (alta prioridade)
(1, 'TECNOLOGIA', 'software', 3),
(1, 'TECNOLOGIA', 'sistema', 2),
(1, 'TECNOLOGIA', 'ti', 3),
(1, 'TECNOLOGIA', 'informatica', 3),
(1, 'TECNOLOGIA', 'licenca', 2),
(1, 'TECNOLOGIA', 'manutencao de equipamentos', 2),
(1, 'TECNOLOGIA', 'desenvolvimento', 2),
(1, 'TECNOLOGIA', 'implantacao', 2),
(1, 'TECNOLOGIA', 'suporte tecnico', 2),

-- EVENTOS (alta prioridade)
(1, 'EVENTOS', 'evento', 3),
(1, 'EVENTOS', 'festa', 2),
(1, 'EVENTOS', 'show', 2),
(1, 'EVENTOS', 'exposicao', 2),
(1, 'EVENTOS', 'feira', 2),
(1, 'EVENTOS', 'cerimonia', 2),
(1, 'EVENTOS', 'congresso', 3),
(1, 'EVENTOS', 'palestra', 2),

-- SAÚDE (alta prioridade)
(1, 'SAUDE', 'saude', 3),
(1, 'SAUDE', 'hospital', 3),
(1, 'SAUDE', 'medicamento', 3),
(1, 'SAUDE', 'material medico', 3),
(1, 'SAUDE', 'equipamento medico', 3),
(1, 'SAUDE', 'consulta', 2),
(1, 'SAUDE', 'exame', 2),
(1, 'SAUDE', 'vacina', 2),

-- SERVIÇOS CONTÍNUOS (média prioridade)
(1, 'SERVICOS_CONTINUOS', 'limpeza', 2),
(1, 'SERVICOS_CONTINUOS', 'conservacao', 2),
(1, 'SERVICOS_CONTINUOS', 'manutencao predial', 2),
(1, 'SERVICOS_CONTINUOS', 'seguranca', 2),
(1, 'SERVICOS_CONTINUOS', 'vigilancia', 2),
(1, 'SERVICOS_CONTINUOS', 'transporte', 2),
(1, 'SERVICOS_CONTINUOS', 'alimentacao', 2),
(1, 'SERVICOS_CONTINUOS', 'copiar', 1),

-- VEÍCULOS (média prioridade)
(1, 'VEICULOS', 'veiculo', 3),
(1, 'VEICULOS', 'carro', 2),
(1, 'VEICULOS', 'caminhao', 2),
(1, 'VEICULOS', 'onibus', 2),
(1, 'VEICULOS', 'frota', 2),
(1, 'VEICULOS', 'combustivel', 2),
(1, 'VEICULOS', 'locacao', 1),

-- MATERIAL DE ESCRITÓRIO (baixa prioridade)
(1, 'MATERIAL_ESCRITORIO', 'material de escritorio', 3),
(1, 'MATERIAL_ESCRITORIO', 'papel', 2),
(1, 'MATERIAL_ESCRITORIO', 'toner', 2),
(1, 'MATERIAL_ESCRITORIO', 'impressora', 1),
(1, 'MATERIAL_ESCRITORIO', 'suprimento', 1),

-- CONSULTORIAS (específico)
(1, 'CONSULTORIA', 'consultoria', 3),
(1, 'CONSULTORIA', 'assessoria', 2),
(1, 'CONSULTORIA', 'estudo', 2),
(1, 'CONSULTORIA', 'pesquisa', 2),
(1, 'CONSULTORIA', 'elaboracao de projeto', 2),
(1, 'CONSULTORIA', 'engenharia', 2),

-- PUBLICIDADE (específico)
(1, 'PUBLICIDADE', 'publicidade', 3),
(1, 'PUBLICIDADE', 'propaganda', 3),
(1, 'PUBLICIDADE', 'marketing', 3),
(1, 'PUBLICIDADE', 'divulgacao', 2),
(1, 'PUBLICIDADE', 'midia', 2),
(1, 'PUBLICIDADE', 'imprensa', 2);

-- 3. VIEW COM SCORES POR CATEGORIA
DROP MATERIALIZED VIEW IF EXISTS vw_score_categoria CASCADE;
CREATE MATERIALIZED VIEW vw_score_categoria AS
WITH matching AS (
    SELECT
        c.id,
        r.categoria,
        r.peso,
        r.keyword
    FROM sp_contratos c
    JOIN categoria_regras r 
        ON LOWER(c.descricao || ' ' || COALESCE(c.objeto, '')) 
           ILIKE '%' || r.keyword || '%'
    WHERE r.ativa = TRUE
      AND r.versao = (SELECT MAX(versao) FROM categoria_regras)
),
scores AS (
    SELECT
        id,
        categoria,
        SUM(peso) AS score_categoria
    FROM matching
    GROUP BY id, categoria
),
scores_totais AS (
    SELECT
        id,
        SUM(score_categoria) AS score_total
    FROM scores
    GROUP BY id
)
SELECT
    s.id,
    s.categoria,
    s.score_categoria,
    st.score_total,
    -- SCORE DE CONFIANÇA (quão dominante é essa categoria)
    CASE 
        WHEN st.score_total > 0 THEN 
            ROUND((s.score_categoria::numeric / st.score_total), 3)
        ELSE 0
    END AS confianca
FROM scores s
JOIN scores_totais st ON s.id = st.id;

CREATE INDEX idx_score_categoria_id ON vw_score_categoria(id);
CREATE INDEX idx_score_categoria_cat ON vw_score_categoria(categoria);

-- 4. VIEW COM CATEGORIA FINAL
DROP MATERIALIZED VIEW IF EXISTS vw_categoria_final CASCADE;
CREATE MATERIALIZED VIEW vw_categoria_final AS
WITH melhor_categoria AS (
    SELECT DISTINCT ON (id)
        id,
        categoria,
        score_categoria,
        confianca
    FROM vw_score_categoria
    ORDER BY id, score_categoria DESC, confianca DESC
)
SELECT
    mc.*,
    -- CATEGORIA FINAL (com fallback para OUTROS)
    CASE 
        WHEN mc.score_categoria >= 2 AND mc.confianca >= 0.5 THEN mc.categoria
        WHEN mc.score_categoria >= 1 THEN 'INCERTO_' || mc.categoria
        ELSE 'OUTROS'
    END AS categoria_final,
    -- FLAG DE QUALIDADE DA CLASSIFICAÇÃO
    CASE
        WHEN mc.score_categoria >= 5 AND mc.confianca >= 0.8 THEN 'ALTA'
        WHEN mc.score_categoria >= 2 AND mc.confianca >= 0.5 THEN 'MEDIA'
        WHEN mc.score_categoria >= 1 THEN 'BAIXA'
        ELSE 'SEM_CLASSIFICACAO'
    END AS qualidade_classificacao
FROM melhor_categoria mc;

CREATE INDEX idx_categoria_final ON vw_categoria_final(categoria_final);
CREATE INDEX idx_categoria_final_id ON vw_categoria_final(id);

-- 5. ESTATÍSTICAS DE CLASSIFICAÇÃO
DROP VIEW IF EXISTS vw_stats_categorias CASCADE;
CREATE VIEW vw_stats_categorias AS
SELECT
    categoria_final,
    COUNT(*) AS qtd_contratos,
    ROUND(AVG(score_categoria)::numeric, 2) AS score_medio,
    ROUND(AVG(confianca)::numeric, 3) AS confianca_media,
    MIN(confianca) AS confianca_min,
    MAX(confianca) AS confianca_max
FROM vw_categoria_final
GROUP BY categoria_final
ORDER BY qtd_contratos DESC;

-- 6. BASELINE POR CATEGORIA (para detecção de anomalias)
DROP MATERIALIZED VIEW IF EXISTS vw_baseline_categoria CASCADE;
CREATE MATERIALIZED VIEW vw_baseline_categoria AS
WITH contratos_com_categoria AS (
    SELECT
        c.*,
        cf.categoria_final,
        cf.qualidade_classificacao
    FROM sp_contratos c
    JOIN vw_categoria_final cf ON c.id = cf.id
)
SELECT
    categoria_final,
    COUNT(*) AS n_contratos,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor) AS mediana_valor,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY valor) AS p25_valor,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY valor) AS p75_valor,
    AVG(valor) AS media_valor,
    STDDEV(valor) AS desvio_valor,
    MIN(valor) AS min_valor,
    MAX(valor) AS max_valor,
    -- Z-score thresholds
    AVG(valor) + 2 * STDDEV(valor) AS z2_superior,
    AVG(valor) - 2 * STDDEV(valor) AS z2_inferior
FROM contratos_com_categoria
GROUP BY categoria_final;

-- Refresh das views
REFRESH MATERIALIZED VIEW vw_score_categoria;
REFRESH MATERIALIZED VIEW vw_categoria_final;
REFRESH MATERIALIZED VIEW vw_baseline_categoria;

-- Relatório inicial
SELECT * FROM vw_stats_categorias;
