-- SCHEMA UNIVERSAL DE ARESTAS
-- Grafo heterogeneo unico + arestas tipadas + tempo desacoplado

-- ================================================================
-- TABELA PRINCIPAL: ARESTAS
-- ================================================================
DROP TABLE IF EXISTS graph_edges CASCADE;
CREATE TABLE graph_edges (
    id SERIAL PRIMARY KEY,
    
    -- Nos (heterogeneos)
    source_id TEXT NOT NULL,        -- ID do no origem
    source_type TEXT NOT NULL,      -- Tipo: 'EMPRESA', 'PESSOA', 'CONTRATO', 'ORGAO'
    
    target_id TEXT NOT NULL,        -- ID do no destino
    target_type TEXT NOT NULL,      -- Tipo: 'EMPRESA', 'PESSOA', 'CONTRATO', 'ORGAO'
    
    -- Semantica da relacao
    edge_type TEXT NOT NULL,        -- Ver EDGE_TYPES abaixo
    weight NUMERIC(5,4) DEFAULT 1.0,  -- Peso da aresta (0-1 ou -1 para negativas)
    
    -- Contexto (desacoplado)
    context JSONB,                  -- {orgao: 'SP', mes: '2024-01', categoria: 'OBRAS'}
    
    -- Temporal (funcao, nao camada)
    first_seen DATE,                -- Primeira observacao
    last_seen DATE,                 -- Ultima observacao
    frequency INT DEFAULT 1,          -- Quantas vezes observada
    
    -- Metadados
    confidence NUMERIC(3,2) DEFAULT 1.0,  -- Confianca da relacao (0-1)
    source_data TEXT,               -- De onde veio: 'RAIS', 'CNPJ', 'CONTRATO'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_weight CHECK (weight >= -1 AND weight <= 1),
    CONSTRAINT chk_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

-- Indices essenciais
CREATE INDEX idx_edges_source ON graph_edges(source_id, source_type);
CREATE INDEX idx_edges_target ON graph_edges(target_id, target_type);
CREATE INDEX idx_edges_type ON graph_edges(edge_type);
CREATE INDEX idx_edges_weight ON graph_edges(weight);
CREATE INDEX idx_edges_context ON graph_edges USING gin(context);
CREATE INDEX idx_edges_temporal ON graph_edges(first_seen, last_seen);

-- ================================================================
-- TIPOS DE ARESTA (ENUMERACAO SEMANTICA)
-- ================================================================
DROP TYPE IF EXISTS edge_type_enum CASCADE;
CREATE TYPE edge_type_enum AS ENUM (
    'SOCIETARIO',           -- Empresa -> Pessoa (socio)
    'VINCULO_EMPREGATICIO', -- Empresa -> Pessoa (emprego)
    'CONTRATO',             -- Fornecedor -> Orgao
    'SUBCONTRATO',          -- Fornecedor -> Fornecedor
    'CO_OCORRENCIA',        -- Fornecedor -> Fornecedor (mesmo contexto)
    'EXCLUSAO',             -- Fornecedor -> Fornecedor (nunca juntos, peso negativo)
    'RELACAO_INDIRETA',     -- Empresa -> Empresa (mesmo endereco, etc)
    'FAMILIAR',             -- Pessoa -> Pessoa (parentesco)
    'GRUPO_ECONOMICO'       -- Empresa -> Empresa (controladora)
);

-- View para facilitar consultas
CREATE OR REPLACE VIEW vw_edges_typed AS
SELECT 
    *,
    CASE 
        WHEN weight < 0 THEN 'NEGATIVA'
        WHEN weight BETWEEN 0 AND 0.3 THEN 'FRACA'
        WHEN weight BETWEEN 0.3 AND 0.7 THEN 'MEDIA'
        ELSE 'FORTE'
    END AS strength
FROM graph_edges;

-- ================================================================
-- FUNCOES TEMPORAIS (DESACOPLADAS)
-- ================================================================

-- Funcao: Evolucao temporal de uma aresta
CREATE OR REPLACE FUNCTION edge_timeline(p_source TEXT, p_target TEXT)
RETURNS TABLE (
    periodo DATE,
    peso NUMERIC,
    contexto JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        first_seen::DATE as periodo,
        weight,
        context
    FROM graph_edges
    WHERE source_id = p_source AND target_id = p_target
    ORDER BY first_seen;
END;
$$ LANGUAGE plpgsql;

-- Funcao: Snapshot do grafo em um momento
CREATE OR REPLACE FUNCTION graph_snapshot(snapshot_date DATE)
RETURNS TABLE (
    source_id TEXT,
    target_id TEXT,
    edge_type TEXT,
    weight NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        g.source_id,
        g.target_id,
        g.edge_type,
        g.weight
    FROM graph_edges g
    WHERE g.first_seen <= snapshot_date 
      AND (g.last_seen IS NULL OR g.last_seen >= snapshot_date);
END;
$$ LANGUAGE plpgsql;

-- Funcao: Detectar mudancas de comunidade
CREATE OR REPLACE FUNCTION detect_community_changes(
    start_date DATE,
    end_date DATE
)
RETURNS TABLE (
    node_id TEXT,
    comunidade_inicial INT,
    comunidade_final INT,
    mudanca BOOLEAN
) AS $$
DECLARE
    snap_inicial TABLE (source TEXT, target TEXT, tipo TEXT, peso NUMERIC);
    snap_final TABLE (source TEXT, target TEXT, tipo TEXT, peso NUMERIC);
BEGIN
    -- Snapshot inicial
    SELECT * INTO snap_inicial FROM graph_snapshot(start_date);
    
    -- Snapshot final
    SELECT * INTO snap_final FROM graph_snapshot(end_date);
    
    -- Calcular mudancas (simplificado)
    RETURN QUERY
    SELECT DISTINCT 
        COALESCE(s1.source, s2.source) as node_id,
        0 as comunidade_inicial,  -- Placeholder para Louvain real
        0 as comunidade_final,
        (s1 IS NULL OR s2 IS NULL) as mudanca
    FROM snap_inicial s1
    FULL OUTER JOIN snap_final s2 ON s1.source = s2.source;
END;
$$ LANGUAGE plpgsql;

-- ================================================================
-- VIEWS ANALITICAS
-- ================================================================

-- Centralidade dinamica (PageRank simplificado)
CREATE OR REPLACE VIEW vw_centrality_dynamic AS
WITH degree_calc AS (
    SELECT 
        source_id as node,
        source_type as node_type,
        SUM(ABS(weight)) as out_degree
    FROM graph_edges
    GROUP BY source_id, source_type
),
total_degree AS (
    SELECT SUM(out_degree) as total FROM degree_calc
)
SELECT 
    d.node,
    d.node_type,
    d.out_degree,
    d.out_degree / NULLIF(t.total, 0) as pagerank_approx
FROM degree_calc d
CROSS JOIN total_degree t;

-- Exclusao estrutural (quem NUNCA esta junto)
CREATE OR REPLACE VIEW vw_exclusao_estrutural AS
SELECT 
    g1.source_id as node_a,
    g2.source_id as node_b,
    g1.context->>'orgao' as orgao,
    1.0 as exclusao_score  -- Peso negativo implicito
FROM graph_edges g1
JOIN graph_edges g2 
    ON g1.context->>'orgao' = g2.context->>'orgao'
    AND g1.source_id < g2.source_id
WHERE g1.edge_type = 'CONTRATO'
  AND g2.edge_type = 'CONTRATO'
  AND NOT EXISTS (
      SELECT 1 FROM graph_edges g3
      WHERE g3.source_id = g1.source_id 
        AND g3.target_id = g2.source_id
        AND g3.edge_type = 'CO_OCORRENCIA'
  );

-- ================================================================
-- PROCEDURES DE MANUTENCAO
-- ================================================================

-- Atualizar peso de aresta baseado em novos dados
CREATE OR REPLACE PROCEDURE update_edge_weight(
    p_source TEXT,
    p_target TEXT,
    p_new_weight NUMERIC
)
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE graph_edges
    SET 
        weight = (weight * frequency + p_new_weight) / (frequency + 1),
        frequency = frequency + 1,
        last_seen = CURRENT_DATE,
        updated_at = CURRENT_TIMESTAMP
    WHERE source_id = p_source AND target_id = p_target;
    
    IF NOT FOUND THEN
        INSERT INTO graph_edges (source_id, target_id, weight, first_seen)
        VALUES (p_source, p_target, p_new_weight, CURRENT_DATE);
    END IF;
END;
$$;

-- Limpar arestas obsoletas
CREATE OR REPLACE PROCEDURE cleanup_old_edges(
    older_than DATE
)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM graph_edges
    WHERE last_seen < older_than
      AND edge_type NOT IN ('SOCIETARIO', 'FAMILIAR');  -- Manter estruturais
END;
$$;

-- ================================================================
-- EXEMPLOS DE USO
-- ================================================================

COMMENT ON TABLE graph_edges IS '
Grafo universal heterogeneo com arestas semanticas tipadas.

Exemplos de insercao:

1. Socio de empresa:
INSERT INTO graph_edges (source_id, source_type, target_id, target_type, edge_type, context)
VALUES ("12345678000190", "EMPRESA", "JOAO SILVA", "PESSOA", "SOCIETARIO", 
        {"percentual": 30});

2. Contrato:
INSERT INTO graph_edges (source_id, source_type, target_id, target_type, edge_type, context)
VALUES ("ABC Ltda", "FORNECEDOR", "PREFEITURA SP", "ORGAO", "CONTRATO",
        {"mes": "2024-01", "valor": 100000, "categoria": "OBRAS"});

3. Exclusao (rodizio):
INSERT INTO graph_edges (source_id, source_type, target_id, target_type, edge_type, weight, context)
VALUES ("ABC Ltda", "FORNECEDOR", "XYZ Ltda", "FORNECEDOR", "EXCLUSAO", -0.8,
        {"orgao": "PREFEITURA SP", "motivo": "nunca_coocorreram"});
';
