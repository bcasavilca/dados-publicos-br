#!/usr/bin/env python3
"""
CATEGORIZAÇÃO HÍBRIDA V1.0
Classificação por regras com pesos + confiança

Integra com:
- PostgreSQL (materialized views)
- Motor de regras existente
- Score final de anomalia
"""

import psycopg2
import pandas as pd
from typing import List, Dict, Tuple
import os

class CategorizadorHibrido:
    """
    Categoriza contratos usando regras com pesos
    Versão leve, pronta para produção
    """
    
    # Regras default (se não quiser usar SQL)
    REGRAS_DEFAULT = [
        # (categoria, keyword, peso)
        ('OBRAS', 'construcao', 3), ('OBRAS', 'reforma', 2),
        ('OBRAS', 'obra', 3), ('OBRAS', 'edificacao', 3),
        
        ('TECNOLOGIA', 'software', 3), ('TECNOLOGIA', 'ti', 3),
        ('TECNOLOGIA', 'informatica', 3), ('TECNOLOGIA', 'sistema', 2),
        
        ('EVENTOS', 'evento', 3), ('EVENTOS', 'festa', 2),
        ('EVENTOS', 'show', 2), ('EVENTOS', 'congresso', 3),
        
        ('SAUDE', 'saude', 3), ('SAUDE', 'hospital', 3),
        ('SAUDE', 'medicamento', 3), ('SAUDE', 'medico', 2),
        
        ('SERVICOS_CONTINUOS', 'limpeza', 2), ('SERVICOS_CONTINUOS', 'manutencao predial', 2),
        ('SERVICOS_CONTINUOS', 'seguranca', 2), ('SERVICOS_CONTINUOS', 'transporte', 2),
        
        ('CONSULTORIA', 'consultoria', 3), ('CONSULTORIA', 'assessoria', 2),
        ('CONSULTORIA', 'estudo', 2), ('CONSULTORIA', 'engenharia', 2),
        
        ('PUBLICIDADE', 'publicidade', 3), ('PUBLICIDADE', 'propaganda', 3),
        ('PUBLICIDADE', 'marketing', 3),
    ]
    
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.conn = None
        
    def connect(self):
        self.conn = psycopg2.connect(self.db_url)
        return self
    
    def inicializar_bd(self):
        """Cria tabelas e views no PostgreSQL"""
        print("📦 Inicializando estrutura de categorização...")
        
        with open('sql/categorizacao_hibrida.sql', 'r') as f:
            sql = f.read()
        
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()
        print("✅ Estrutura criada")
        
    def classificar_texto(self, texto: str) -> Tuple[str, float, float]:
        """
        Classifica um texto livre
        
        Returns:
            (categoria, score, confianca)
        """
        texto_lower = texto.lower()
        scores = {}
        
        for categoria, keyword, peso in self.REGRAS_DEFAULT:
            if keyword in texto_lower:
                scores[categoria] = scores.get(categoria, 0) + peso
        
        if not scores:
            return 'OUTROS', 0.0, 0.0
        
        # Categoria vencedora
        categoria_vencedora = max(scores, key=scores.get)
        score_vencedor = scores[categoria_vencedora]
        score_total = sum(scores.values())
        
        # Confiança = proporção do vencedor no total
        confianca = score_vencedor / score_total if score_total > 0 else 0
        
        return categoria_vencedora, float(score_vencedor), round(confianca, 3)
    
    def categorizar_contratos(self, min_conf=0.5, min_score=2):
        """
        Categoriza todos os contratos usando SQL (mais rápido)
        
        Args:
            min_conf: Confiança mínima (0-1)
            min_score: Score mínimo para considerar válido
        """
        print(f"📊 Categorizando contratos (conf>={min_conf}, score>={min_score})...")
        
        query = """
        SELECT
            id,
            fornecedor,
            orgao,
            valor,
            categoria_final,
            score_categoria,
            confianca,
            qualidade_classificacao
        FROM vw_categoria_final
        WHERE confianca >= %(min_conf)s
          AND score_categoria >= %(min_score)s
        ORDER BY valor DESC
        """
        
        df = pd.read_sql(query, self.conn, params={
            'min_conf': min_conf,
            'min_score': min_score
        })
        
        print(f"✅ {len(df)} contratos categorizados")
        
        # Stats por categoria
        stats = df.groupby('categoria_final').agg({
            'id': 'count',
            'valor': ['sum', 'mean'],
            'confianca': 'mean'
        }).round(2)
        
        print("\n📈 Distribuição por categoria:")
        print(stats)
        
        return df
    
    def detectar_anomalias_por_categoria(self, z_threshold=2.0):
        """
        Detecta contratos anômalos dentro de cada categoria
        Usando z-score (desvio em relação à média da categoria)
        """
        print(f"🚨 Detectando anomalias (z > {z_threshold})...")
        
        query = f"""
        WITH contratos_categorizados AS (
            SELECT
                c.id,
                c.fornecedor,
                c.orgao,
                c.valor,
                cf.categoria_final,
                bl.media_valor,
                bl.desvio_valor,
                bl.mediana_valor
            FROM sp_contratos c
            JOIN vw_categoria_final cf ON c.id = cf.id
            JOIN vw_baseline_categoria bl ON cf.categoria_final = bl.categoria_final
            WHERE cf.qualidade_classificacao IN ('ALTA', 'MEDIA')
        ),
        anomalias AS (
            SELECT
                *,
                (valor - media_valor) / NULLIF(desvio_valor, 0) AS z_score,
                CASE
                    WHEN valor > media_valor + {z_threshold} * desvio_valor THEN 'ACIMA'
                    WHEN valor < media_valor - {z_threshold} * desvio_valor THEN 'ABAIXO'
                    ELSE 'NORMAL'
                END AS tipo_anomalia
            FROM contratos_categorizados
            WHERE desvio_valor > 0
        )
        SELECT *
        FROM anomalias
        WHERE tipo_anomalia != 'NORMAL'
        ORDER BY ABS(z_score) DESC
        """
        
        df = pd.read_sql(query, self.conn)
        
        print(f"🔴 {len(df)} anomalias detectadas")
        
        if len(df) > 0:
            print("\nTop 10 anomalias:")
            print(df[['fornecedor', 'categoria_final', 'valor', 'z_score']].head(10))
        
        return df
    
    def calcular_score_categoria_final(self, fornecedor: str) -> Dict:
        """
        Calcula score de especialização do fornecedor
        Fornecedor concentrado em 1 categoria = possível especialista
        Fornecedor espalhado em tudo = possível "puxa-saco" ou cartel
        """
        query = """
        SELECT
            cf.categoria_final,
            COUNT(*) AS qtd,
            SUM(c.valor) AS total_valor
        FROM sp_contratos c
        JOIN vw_categoria_final cf ON c.id = cf.id
        WHERE c.fornecedor = %(fornecedor)s
          AND cf.qualidade_classificacao IN ('ALTA', 'MEDIA')
        GROUP BY cf.categoria_final
        """
        
        df = pd.read_sql(query, self.conn, params={'fornecedor': fornecedor})
        
        if len(df) == 0:
            return {'especializacao': 'INDEFINIDO', 'score': 0.0}
        
        # Calcular entropia de categoria (quanto mais baixa, mais especializado)
        total = df['qtd'].sum()
        proporcoes = df['qtd'] / total
        entropia = -sum(p * (p ** 0.5) for p in proporcoes if p > 0)
        
        # Categoria dominante
        cat_dominante = df.loc[df['qtd'].idxmax(), 'categoria_final']
        prop_dominante = df['qtd'].max() / total
        
        return {
            'categoria_dominante': cat_dominante,
            'proporcao_dominante': round(prop_dominante, 3),
            'entropia': round(entropia, 3),
            'especializacao': 'ALTA' if prop_dominante > 0.8 else ('MEDIA' if prop_dominante > 0.5 else 'BAIXA'),
            'categorias': df.to_dict('records')
        }
    
    def exportar_para_motor(self, output_table='contratos_categorizados'):
        """
        Exporta resultados para uso no motor de regras
        """
        print(f"📤 Exportando para {output_table}...")
        
        query = f"""
        DROP TABLE IF EXISTS {output_table};
        CREATE TABLE {output_table} AS
        SELECT
            c.id,
            c.fornecedor,
            c.orgao,
            c.valor,
            c.data_assinatura,
            cf.categoria_final,
            cf.score_categoria,
            cf.confianca,
            cf.qualidade_classificacao
        FROM sp_contratos c
        JOIN vw_categoria_final cf ON c.id = cf.id;
        
        CREATE INDEX idx_{output_table}_cat ON {output_table}(categoria_final);
        CREATE INDEX idx_{output_table}_forn ON {output_table}(fornecedor);
        """
        
        cur = self.conn.cursor()
        cur.execute(query)
        self.conn.commit()
        
        print(f"✅ Tabela {output_table} criada")

def main():
    """Demo de uso"""
    cat = CategorizadorHibrido().connect()
    
    # Inicializar (rodar uma vez)
    # cat.inicializar_bd()
    
    # Categorizar
    df = cat.categorizar_contratos(min_conf=0.5, min_score=2)
    
    # Detectar anomalias
    anomalias = cat.detectar_anomalias_por_categoria(z_threshold=2.0)
    
    # Exportar
    cat.exportar_para_motor()
    
    print("\n✅ Categorização completa!")

if __name__ == '__main__':
    main()
