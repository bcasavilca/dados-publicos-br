#!/usr/bin/env python3
"""
FASE 3 — GRAPH ENGINE

Detecta coordenação (não só correlação) entre fornecedores:
- Centralidade (quem é hub)
- Comunidades (Louvain simplificado)
- Exclusão estrutural (quem NUNCA aparece junto)
- Hubs de influência

Matemática:
- Centralidade: PageRank adaptado
- Comunidades: Louvain modularity
- Exclusão: 1 - (co_real / co_esperada) no grafo
"""

import psycopg2
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Set
from collections import defaultdict
import os
from datetime import datetime


class GraphEngine:
    """
    Motor de análise de grafos para detecção de coordenação
    
    Diferença crítica:
    - Correlação: "A e B aparecem juntos"
    - Coordenação: "A e B NUNCA aparecem juntos (suspeito)"
    """
    
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.conn = psycopg2.connect(self.db_url)
        
        # Grafo em memória
        self.nodes = set()
        self.edges = defaultdict(lambda: defaultdict(float))
        self.weights = {}
    
    # ═════════════════════════════════════════════════════════════════
    # CONSTRUÇÃO DO GRAFO
    # ═════════════════════════════════════════════════════════════════
    
    def construir_grafo_temporal(self, min_contratos: int = 3) -> None:
        """
        Constrói grafo de co-ocorrência temporal
        
        Aresta (A,B) existe se A e B aparecem no mesmo (órgão + mês)
        Peso = frequência de co-ocorrência
        """
        print("🕸️  Construindo grafo temporal...")
        
        query = """
            SELECT 
                fornecedor,
                orgao,
                TO_CHAR(TO_DATE(data_assinatura, 'DD/MM/YYYY'), 'YYYY-MM') as mes,
                COUNT(*) as qtd
            FROM sp_contratos
            WHERE data_assinatura IS NOT NULL
            GROUP BY fornecedor, orgao, mes
            HAVING COUNT(*) >= %(min)s
        """
        
        df = pd.read_sql(query, self.conn, params={'min': min_contratos})
        
        if len(df) == 0:
            print("⚠️  Dados insuficientes para grafo")
            return
        
        # Agrupar por (orgao, mes)
        grupos = df.groupby(['orgao', 'mes'])['fornecedor'].apply(list)
        
        # Criar arestas
        for _, fornecedores in grupos.items():
            if len(fornecedores) < 2:
                continue
            
            # Todos os pares nesse (orgao, mes)
            for i, a in enumerate(fornecedores):
                for b in fornecedores[i+1:]:
                    self.nodes.add(a)
                    self.nodes.add(b)
                    # Peso incrementa com cada co-ocorrência
                    self.edges[a][b] += 1
                    self.edges[b][a] += 1
        
        print(f"✅ Grafo construído: {len(self.nodes)} nós, {sum(len(v) for v in self.edges.values())//2} arestas")
    
    # ═════════════════════════════════════════════════════════════════
    # FEATURE 1: CENTRALIDADE (PAGERANK ADAPTADO)
    # ═════════════════════════════════════════════════════════════════
    
    def calcular_centralidade(self, fornecedor: str) -> float:
        """
        Centralidade PageRank adaptada
        
        Quem tem mais conexões (e conexões importantes) = hub
        """
        if fornecedor not in self.edges:
            return 0.0
        
        # Simplificação: grau ponderado / grau máximo
        conexoes = self.edges[fornecedor]
        peso_total = sum(conexoes.values())
        
        # Normalizar
        max_peso = max(sum(v.values()) for v in self.edges.values()) if self.edges else 1
        
        return round(peso_total / max_peso, 4) if max_peso > 0 else 0.0
    
    # ═════════════════════════════════════════════════════════════════
    # FEATURE 2: COMUNIDADES (LOUVAIN SIMPLIFICADO)
    # ═════════════════════════════════════════════════════════════════
    
    def detectar_comunidades(self) -> Dict[str, int]:
        """
        Algoritmo de Louvain simplificado para detecção de comunidades
        
        Comunidade = grupo de fornecedores densamente conectados
        """
        print("🔍 Detectando comunidades...")
        
        if len(self.nodes) == 0:
            return {}
        
        # Inicialização: cada nó é sua própria comunidade
        comunidades = {node: i for i, node in enumerate(self.nodes)}
        
        # Iterações de Louvain simplificado
        melhoria = True
        iteracao = 0
        max_iter = 10
        
        while melhoria and iteracao < max_iter:
            melhoria = False
            iteracao += 1
            
            for node in self.nodes:
                if node not in self.edges:
                    continue
                
                # Calcular ganho de modularidade movendo para vizinhos
                vizinhos = self.edges[node]
                
                if not vizinhos:
                    continue
                
                # Comunidade atual
                comunidade_atual = comunidades[node]
                
                # Contar conexões por comunidade vizinha
                contagem_comunidades = defaultdict(float)
                for vizinho, peso in vizinhos.items():
                    contagem_comunidades[comunidades[vizinho]] += peso
                
                # Melhor comunidade (incluindo a atual)
                contagem_comunidades[comunidade_atual] = 0  # Não mover para mesma
                
                if contagem_comunidades:
                    melhor_com = max(contagem_comunidades, key=contagem_comunidades.get)
                    
                    if melhor_com != comunidade_atual and contagem_comunidades[melhor_com] > 0:
                        comunidades[node] = melhor_com
                        melhoria = True
        
        # Reindexar comunidades para serem contínuas
        com_unicas = sorted(set(comunidades.values()))
        mapa = {c: i for i, c in enumerate(com_unicas)}
        comunidades = {node: mapa[c] for node, c in comunidades.items()}
        
        print(f"✅ {len(set(comunidades.values()))} comunidades detectadas")
        return comunidades
    
    # ═════════════════════════════════════════════════════════════════
    # FEATURE 3: EXCLUSÃO ESTRUTURAL (CRÍTICO)
    # ═════════════════════════════════════════════════════════════════
    
    def calcular_exclusao(self, fornecedor: str) -> float:
        """
        Score de exclusão estrutural
        
        Quanto menor a conectividade com outros fornecedores similares,
        maior a suspeita de coordenação indireta.
        
        Matemática: 1 - (conectividade_real / conectividade_esperada)
        """
        if fornecedor not in self.nodes:
            return 0.0
        
        # Conectividade real
        conexoes_reais = len(self.edges.get(fornecedor, {}))
        
        # Conectividade esperada (média do grafo)
        grau_medio = np.mean([len(v) for v in self.edges.values()]) if self.edges else 0
        
        if grau_medio == 0:
            return 0.0
        
        # Ratio
        ratio = conexoes_reais / grau_medio
        
        # Score de exclusão: isolamento = suspeito
        exclusao = max(0, 1 - ratio)
        
        return round(exclusao, 4)
    
    # ═════════════════════════════════════════════════════════════════
    # FEATURE 4: HUB DE INFLUÊNCIA
    # ═════════════════════════════════════════════════════════════════
    
    def calcular_hub_influencia(self, fornecedor: str) -> float:
        """
        Mede se o fornecedor conecta comunidades diferentes
        
        Hub = conecta clusters que não teriam contato
        """
        if fornecedor not in self.edges or not self.edges[fornecedor]:
            return 0.0
        
        # Detectar comunidades se ainda não feito
        if not hasattr(self, '_comunidades_cache'):
            self._comunidades_cache = self.detectar_comunidades()
        
        comunidades = self._comunidades_cache
        
        # Quantas comunidades diferentes este nó conecta?
        coms_conectadas = set()
        for vizinho in self.edges[fornecedor]:
            if vizinho in comunidades:
                coms_conectadas.add(comunidades[vizinho])
        
        # Score: número de comunidades / número total
        total_coms = len(set(comunidades.values()))
        if total_coms <= 1:
            return 0.0
        
        score = len(coms_conectadas) / total_coms
        
        return round(score, 4)
    
    # ═════════════════════════════════════════════════════════════════
    # VETOR COMPLETO
    # ═════════════════════════════════════════════════════════════════
    
    def calcular_vetor_rede(self, fornecedor: str) -> Dict:
        """Calcula vetor completo de features de rede"""
        
        return {
            'fornecedor': fornecedor,
            's_centralidade': self.calcular_centralidade(fornecedor),
            's_exclusao': self.calcular_exclusao(fornecedor),
            's_hub_influencia': self.calcular_hub_influencia(fornecedor),
            'comunidade': self._comunidades_cache.get(fornecedor, -1) if hasattr(self, '_comunidades_cache') else -1
        }
    
    def processar_todos(self) -> pd.DataFrame:
        """Processa todos os fornecedores do grafo"""
        
        print("=" * 80)
        print("FASE 3 — GRAPH ENGINE")
        print("=" * 80)
        
        # 1. Construir grafo
        self.construir_grafo_temporal()
        
        if len(self.nodes) == 0:
            print("⚠️  Sem dados para processar")
            return pd.DataFrame()
        
        # 2. Detectar comunidades (uma vez)
        self._comunidades_cache = self.detectar_comunidades()
        
        # 3. Calcular features para cada nó
        vetores = []
        for node in self.nodes:
            vetor = self.calcular_vetor_rede(node)
            vetor['score_rede'] = self._combinar_features(vetor)
            vetores.append(vetor)
        
        df = pd.DataFrame(vetores)
        
        # 4. Salvar
        self._salvar_rede(df)
        
        print(f"\n✅ {len(df)} vetores de rede gerados")
        print("\n📊 Distribuição:")
        print(df[['s_centralidade', 's_exclusao', 's_hub_influencia']].describe())
        
        return df
    
    def _combinar_features(self, vetor: Dict) -> float:
        """Combina features de rede"""
        # Pesos: exclusão mais importante (sinal forte de coordenação)
        return round(
            vetor['s_centralidade'] * 0.25 +
            vetor['s_exclusao'] * 0.45 +
            vetor['s_hub_influencia'] * 0.30,
            4
        )
    
    def _salvar_rede(self, df: pd.DataFrame):
        """Salva no PostgreSQL"""
        
        cur = self.conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS features_rede (
                id SERIAL PRIMARY KEY,
                fornecedor TEXT UNIQUE,
                s_centralidade NUMERIC(5,4),
                s_exclusao NUMERIC(5,4),
                s_hub_influencia NUMERIC(5,4),
                comunidade INT,
                score_rede NUMERIC(5,4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO features_rede
                (fornecedor, s_centralidade, s_exclusao, s_hub_influencia, comunidade, score_rede)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (fornecedor) DO UPDATE SET
                    s_centralidade = EXCLUDED.s_centralidade,
                    s_exclusao = EXCLUDED.s_exclusao,
                    s_hub_influencia = EXCLUDED.s_hub_influencia,
                    comunidade = EXCLUDED.comunidade,
                    score_rede = EXCLUDED.score_rede,
                    created_at = CURRENT_TIMESTAMP
            """, (
                row['fornecedor'], row['s_centralidade'], row['s_exclusao'],
                row['s_hub_influencia'], row['comunidade'], row['score_rede']
            ))
        
        self.conn.commit()
        print(f"✅ {len(df)} features de rede salvas")


def main():
    """Pipeline Fase 3"""
    
    print("=" * 80)
    print("FASE 3 — GRAPH ENGINE (COORDENAÇÃO)")
    print("=" * 80)
    
    engine = GraphEngine()
    df = engine.processar_todos()
    
    if len(df) > 0:
        print("\n" + "=" * 80)
        print("TOP 10 EXCLUSÃO ESTRUTURAL (COORDENAÇÃO SUSPEITA):")
        print("=" * 80)
        
        top_exclusao = df.nlargest(10, 's_exclusao')
        for _, row in top_exclusao.iterrows():
            print(f"\n🔴 {row['fornecedor'][:50]}")
            print(f"   Exclusão: {row['s_exclusao']:.3f} | "
                  f"Centralidade: {row['s_centralidade']:.3f} | "
                  f"Comunidade: {row['comunidade']}")
    
    print("\n" + "=" * 80)
    print("FASE 3 CONCLUÍDA")
    print("=" * 80)
    print("\nPróximo: Fase 3.5 (Normalização entre camadas)")


if __name__ == '__main__':
    main()
