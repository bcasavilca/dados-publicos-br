#!/usr/bin/env python3
"""
DETECTOR DE RODÍZIO V1.0
Detecta padrões anti-coincidência entre fornecedores

Uso:
    python detector_rodizio.py --modo calcular
    python detector_rodizio.py --modo analisar --fornecedor "EMPRESA X"
"""

import psycopg2
import pandas as pd
import numpy as np
from scipy.stats import entropy
from collections import defaultdict
import argparse
import os
from datetime import datetime

class DetectorRodizio:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.conn = None
        
    def connect(self):
        """Conecta ao PostgreSQL"""
        self.conn = psycopg2.connect(self.db_url)
        return self
    
    def calcular_matriz_rodizio(self, min_contratos=5, min_valor=10000):
        """
        Calcula matriz de rodízio para todos os pares de fornecedores
        
        Lógica: Detecta fornecedores que NUNCA ou RARAMENTE aparecem
        no mesmo mês, mesmo tendo alta frequência individual.
        Isso sugere possível divisão de mercado (rodízio).
        """
        print("📊 Calculando matriz de rodízio...")
        
        query = """
        WITH fornecedores_ativos AS (
            -- Filtrar fornecedores relevantes
            SELECT fornecedor, orgao
            FROM sp_contratos
            GROUP BY fornecedor, orgao
            HAVING COUNT(*) >= %(min_contratos)s
               AND SUM(valor) >= %(min_valor)s
        ),
        meses_por_fornecedor AS (
            -- Quando cada fornecedor atuou
            SELECT 
                fa.fornecedor,
                fa.orgao,
                TO_CHAR(TO_DATE(c.data_assinatura, 'DD/MM/YYYY'), 'YYYY-MM') AS mes,
                COUNT(*) AS qtd,
                SUM(c.valor) AS valor
            FROM fornecedores_ativos fa
            JOIN sp_contratos c ON fa.fornecedor = c.fornecedor AND fa.orgao = c.orgao
            WHERE c.data_assinatura IS NOT NULL
            GROUP BY fa.fornecedor, fa.orgao, mes
        ),
        pares AS (
            -- Gerar todos os pares possíveis no mesmo órgão
            SELECT DISTINCT
                LEAST(a.fornecedor, b.fornecedor) AS fornecedor_a,
                GREATEST(a.fornecedor, b.fornecedor) AS fornecedor_b,
                a.orgao
            FROM meses_por_fornecedor a
            JOIN meses_por_fornecedor b ON a.orgao = b.orgao
            WHERE a.fornecedor < b.fornecedor
        ),
        co_ocorrencia_real AS (
            -- Meses onde AMBOS estiveram ativos
            SELECT
                p.fornecedor_a,
                p.fornecedor_b,
                p.orgao,
                COUNT(DISTINCT a.mes) AS meses_juntos,
                SUM(a.qtd + b.qtd) AS contratos_juntos
            FROM pares p
            JOIN meses_por_fornecedor a ON p.fornecedor_a = a.fornecedor AND p.orgao = a.orgao
            JOIN meses_por_fornecedor b ON p.fornecedor_b = b.fornecedor AND p.orgao = b.orgao AND a.mes = b.mes
            GROUP BY p.fornecedor_a, p.fornecedor_b, p.orgao
        ),
        stats_individual AS (
            -- Estatísticas individuais
            SELECT
                fornecedor,
                orgao,
                COUNT(DISTINCT mes) AS meses_ativos,
                SUM(qtd) AS total_contratos,
                SUM(valor) AS total_valor
            FROM meses_por_fornecedor
            GROUP BY fornecedor, orgao
        ),
        matriz AS (
            SELECT
                p.fornecedor_a,
                p.fornecedor_b,
                p.orgao,
                COALESCE(cr.meses_juntos, 0) AS meses_juntos,
                COALESCE(cr.contratos_juntos, 0) AS contratos_juntos,
                sa.meses_ativos AS meses_a,
                sb.meses_ativos AS meses_b,
                sa.total_contratos AS contratos_a,
                sb.total_contratos AS contratos_b,
                sa.total_valor AS valor_a,
                sb.total_valor AS valor_b,
                -- Co-ocorrência esperada se independentes
                (sa.meses_ativos::float * sb.meses_ativos::float) / 
                    NULLIF((SELECT COUNT(DISTINCT mes) FROM meses_por_fornecedor WHERE orgao = p.orgao), 0) AS esperado
            FROM pares p
            LEFT JOIN co_ocorrencia_real cr ON p.fornecedor_a = cr.fornecedor_a 
                AND p.fornecedor_b = cr.fornecedor_b AND p.orgao = cr.orgao
            JOIN stats_individual sa ON p.fornecedor_a = sa.fornecedor AND p.orgao = sa.orgao
            JOIN stats_individual sb ON p.fornecedor_b = sb.fornecedor AND p.orgao = sb.orgao
        )
        SELECT
            fornecedor_a,
            fornecedor_b,
            orgao,
            meses_juntos,
            meses_a,
            meses_b,
            contratos_a,
            contratos_b,
            ROUND(esperado::numeric, 2) AS esperado,
            CASE 
                WHEN esperado > 0 THEN ROUND((meses_juntos / esperado)::numeric, 3)
                ELSE 0
            END AS ratio_coocorrencia,
            -- SCORE DE RODÍZIO
            CASE
                -- Exclusão total: ambos ativos mas nunca juntos = score máximo
                WHEN esperado > 5 AND meses_juntos = 0 THEN 1.0
                -- Rodízio forte: co-ocorrência muito abaixo do esperado
                WHEN esperado > 5 AND meses_juntos < esperado * 0.2 THEN 0.9
                -- Rodízio moderado
                WHEN esperado > 5 AND meses_juntos < esperado * 0.5 THEN 0.7
                -- Normal
                WHEN esperado > 0 AND meses_juntos BETWEEN esperado * 0.8 AND esperado * 1.2 THEN 0.3
                -- Coincidência alta (possível conluio)
                WHEN esperado > 0 AND meses_juntos > esperado * 1.5 THEN 0.5
                ELSE 0.4
            END AS score_rodizio
        FROM matriz
        WHERE meses_a >= 3 AND meses_b >= 3  -- Mínimo de atividade
        ORDER BY score_rodizio DESC, esperado DESC
        """
        
        df = pd.read_sql(query, self.conn, params={
            'min_contratos': min_contratos,
            'min_valor': min_valor
        })
        
        print(f"✅ Matriz calculada: {len(df)} pares analisados")
        return df
    
    def detectar_grupos_rodizio(self, min_score=0.7):
        """
        Detecta grupos de fornecedores em rodízio (não só pares)
        Usa clusterização em grafos
        """
        print("🕸️  Detectando grupos de rodízio...")
        
        # Pegar pares com alto score
        df = self.calcular_matriz_rodizio()
        suspeitos = df[df['score_rodizio'] >= min_score]
        
        if len(suspeitos) == 0:
            print("⚠️  Nenhum par com score alto encontrado")
            return None
        
        # Construir grafo de exclusão
        grafo = defaultdict(set)
        for _, row in suspeitos.iterrows():
            grafo[row['fornecedor_a']].add(row['fornecedor_b'])
            grafo[row['fornecedor_b']].add(row['fornecedor_a'])
        
        # Encontrar cliques (grupos totalmente conectados)
        grupos = []
        visitados = set()
        
        def encontrar_clique(node, clique_atual):
            clique = clique_atual | {node}
            for vizinho in grafo[node]:
                if vizinho not in visitados and clique.issubset(grafo[vizinho] | {vizinho}):
                    encontrar_clique(vizinho, clique)
            
            if len(clique) >= 3 and clique not in grupos:
                grupos.append(clique)
        
        for node in grafo:
            if node not in visitados:
                encontrar_clique(node, set())
                visitados.add(node)
        
        print(f"✅ {len(grupos)} grupos de rodízio detectados")
        return grupos
    
    def analisar_fornecedor(self, nome_fornecedor):
        """Análise detalhada de um fornecedor específico"""
        print(f"🔍 Analisando: {nome_fornecedor}")
        
        query = """
        WITH contratos AS (
            SELECT 
                TO_CHAR(TO_DATE(data_assinatura, 'DD/MM/YYYY'), 'YYYY-MM') AS mes,
                COUNT(*) AS qtd,
                SUM(valor) AS valor
            FROM sp_contratos
            WHERE fornecedor = %(fornecedor)s
              AND data_assinatura IS NOT NULL
            GROUP BY mes
            ORDER BY mes
        )
        SELECT 
            mes,
            qtd,
            valor,
            -- Análise temporal
            LAG(valor) OVER (ORDER BY mes) AS valor_anterior,
            -- Entropia local (3 meses)
            AVG(valor) OVER (ORDER BY mes ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS media_movel
        FROM contratos
        """
        
        df = pd.read_sql(query, self.conn, params={'fornecedor': nome_fornecedor})
        
        # Calcular métricas
        if len(df) > 0:
            entropia_valor = entropy(df['valor'].values + 1)
            variacao = df['valor'].std() / df['valor'].mean() if df['valor'].mean() > 0 else 0
            
            print(f"  📊 Contratos: {len(df)} meses")
            print(f"  💰 Valor total: R$ {df['valor'].sum():,.2f}")
            print(f"  📈 Entropia: {entropia_valor:.3f}")
            print(f"  📉 Coef. variação: {variacao:.3f}")
        
        return df
    
    def exportar_alertas(self, min_score=0.8, output_file='alertas_rodizio.csv'):
        """Exporta alertas para análise manual"""
        df = self.calcular_matriz_rodizio()
        alertas = df[df['score_rodizio'] >= min_score].copy()
        
        alertas['data_geracao'] = datetime.now()
        alertas.to_csv(output_file, index=False)
        
        print(f"🚨 {len(alertas)} alertas exportados para {output_file}")
        return alertas

def main():
    parser = argparse.ArgumentParser(description='Detector de Rodízio')
    parser.add_argument('--modo', choices=['calcular', 'analisar', 'grupos'], 
                       default='calcular')
    parser.add_argument('--fornecedor', help='Nome do fornecedor para análise')
    parser.add_argument('--min-score', type=float, default=0.7)
    
    args = parser.parse_args()
    
    detector = DetectorRodizio().connect()
    
    if args.modo == 'calcular':
        df = detector.calcular_matriz_rodizio()
        print("\n🔴 TOP 10 ALERTAS DE RODÍZIO:")
        print(df[df['score_rodizio'] >= 0.7].head(10).to_string())
        
        # Exportar
        detector.exportar_alertas(min_score=0.7)
        
    elif args.modo == 'analisar' and args.fornecedor:
        detector.analisar_fornecedor(args.fornecedor)
        
    elif args.modo == 'grupos':
        grupos = detector.detectar_grupos_rodizio(min_score=args.min_score)
        if grupos:
            print("\n🕸️  GRUPOS DETECTADOS:")
            for i, grupo in enumerate(grupos[:10], 1):
                print(f"\n  Grupo {i}: {len(grupo)} fornecedores")
                for f in list(grupo)[:5]:
                    print(f"    - {f[:50]}")

if __name__ == '__main__':
    main()
