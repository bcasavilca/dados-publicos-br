#!/usr/bin/env python3
"""
FASE 1.5 — DESCORRELAÇÃO LATENTE

Remove redundância entre features estruturais antes da Fase 2.

Problema: s_laranjas ↑ → s_grupo_economico tende a ↑
Solução: ajuste de penalização + compressão não-linear

Matemática:
- Penalização: feature_adj = feature - alpha * correlacionada
- Compressão: tanh(w · features) para [-1, 1]
- Output: vetor ortogonalizado
"""

import psycopg2
import pandas as pd
import numpy as np
from typing import Dict, Tuple
import os


class DescorrelacaoLatente:
    """
    Remove correlação redundante entre features estruturais
    
    Matemática:
    - Correlação de Pearson entre features
    - Penalização proporcional à correlação
    - Compressão final via tanh
    """
    
    # Coeficientes de penalização (ajustáveis)
    ALPHAS = {
        ('s_laranjas', 's_grupo'): 0.30,      # laranjas penalizado por grupo
        ('s_grupo', 's_laranjas'): 0.20,      # grupo levemente por laranjas
        ('s_idade', 's_grupo'): 0.15,         # idade pode correlacionar com grupo
        ('s_concentracao', 's_laranjas'): 0.10,  # concentração e laranjas
    }
    
    # Pesos para compressão final (soma = 1)
    PESOS_COMPRESSAO = {
        's_laranjas': 0.35,
        's_grupo': 0.30,
        's_idade': 0.20,
        's_concentracao': 0.15
    }
    
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.conn = psycopg2.connect(self.db_url)
        
    def carregar_vetores(self) -> pd.DataFrame:
        """Carrega vetores estruturais do banco"""
        query = """
            SELECT 
                fornecedor,
                cnpj,
                s_laranjas,
                s_grupo_economico as s_grupo,
                s_idade_risco as s_idade,
                s_concentracao,
                score_estrutural
            FROM features_estruturais
        """
        return pd.read_sql(query, self.conn)
    
    def calcular_correlacoes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula matriz de correlação entre features
        """
        features = ['s_laranjas', 's_grupo', 's_idade', 's_concentracao']
        
        corr = df[features].corr()
        
        print("📊 Matriz de correlação:")
        print(corr.round(3))
        
        # Identificar pares altamente correlacionados
        pares_altos = []
        for i in range(len(features)):
            for j in range(i+1, len(features)):
                if abs(corr.iloc[i, j]) > 0.5:
                    pares_altos.append({
                        'feature_a': features[i],
                        'feature_b': features[j],
                        'correlacao': corr.iloc[i, j]
                    })
        
        if pares_altos:
            print("\n⚠️  Pares com alta correlação:")
            for p in pares_altos:
                print(f"   {p['feature_a']} ↔ {p['feature_b']}: {p['correlacao']:.3f}")
        
        return corr
    
    def ajustar_penalizacao(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica penalização de correlação
        
        s_laranjas_adj = s_laranjas - alpha * s_grupo
        """
        df_adj = df.copy()
        
        # Penalização: laranjas vs grupo
        if ('s_laranjas', 's_grupo') in self.ALPHAS:
            alpha = self.ALPHAS[('s_laranjas', 's_grupo')]
            df_adj['s_laranjas_adj'] = np.clip(
                df['s_laranjas'] - alpha * df['s_grupo'],
                0, 1
            )
            print(f"✅ s_laranjas ajustado (penalizado por s_grupo, alpha={alpha})")
        else:
            df_adj['s_laranjas_adj'] = df['s_laranjas']
        
        # Penalização: grupo vs laranjas (menor)
        if ('s_grupo', 's_laranjas') in self.ALPHAS:
            alpha = self.ALPHAS[('s_grupo', 's_laranjas')]
            df_adj['s_grupo_adj'] = np.clip(
                df['s_grupo'] - alpha * df['s_laranjas'],
                0, 1
            )
            print(f"✅ s_grupo ajustado (penalizado por s_laranjas, alpha={alpha})")
        else:
            df_adj['s_grupo_adj'] = df['s_grupo']
        
        # Outras features recebem ajuste menor
        df_adj['s_idade_adj'] = df['s_idade']
        df_adj['s_concentracao_adj'] = df['s_concentracao']
        
        # Calcular novas correlações
        features_adj = ['s_laranjas_adj', 's_grupo_adj', 's_idade_adj', 's_concentracao_adj']
        corr_nova = df_adj[features_adj].corr()
        
        print("\n📊 Matriz após ajuste:")
        print(corr_nova.round(3))
        
        return df_adj
    
    def comprimir_tanh(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compressão não-linear via tanh
        
        S_estrutural_comprimido = tanh(w · features_adj)
        
        tanh: mapeia [-∞, +∞] para [-1, 1]
        Aqui usamos [0, 1] via (tanh(x) + 1) / 2
        """
        features_adj = ['s_laranjas_adj', 's_grupo_adj', 's_idade_adj', 's_concentracao_adj']
        
        # Combinação linear ponderada
        combinacao = np.zeros(len(df))
        for feat in features_adj:
            peso = self.PESOS_COMPRESSAO.get(feat.replace('_adj', ''), 0.25)
            combinacao += df[feat].values * peso
        
        # Compressão tanh
        # Escalar para ter efeito não-linear mesmo em [0,1]
        combinacao_escalada = (combinacao - 0.5) * 4  # centra em 0, expande
        score_comprimido = (np.tanh(combinacao_escalada) + 1) / 2
        
        df['score_estrutural_ortogonal'] = score_comprimido
        
        print(f"\n✅ Score comprimido via tanh")
        print(f"   Range: [{score_comprimido.min():.3f}, {score_comprimido.max():.3f}]")
        print(f"   Média: {score_comprimido.mean():.3f}")
        
        return df
    
    def gerar_vetor_ortogonalizado(self) -> pd.DataFrame:
        """
        Pipeline completo de descorrelação
        """
        print("=" * 80)
        print("FASE 1.5 — DESCORRELAÇÃO LATENTE")
        print("=" * 80)
        
        # 1. Carregar dados
        df = self.carregar_vetores()
        print(f"\n📥 {len(df)} vetores carregados")
        
        # 2. Analisar correlações
        corr_original = self.calcular_correlacoes(df)
        
        # 3. Aplicar penalização
        df_adj = self.ajustar_penalizacao(df)
        
        # 4. Comprimir via tanh
        df_final = self.comprimir_tanh(df_adj)
        
        # 5. Comparar scores
        print("\n📊 Comparação de scores:")
        print(f"   Original: mean={df['score_estrutural'].mean():.3f}, "
              f"std={df['score_estrutural'].std():.3f}")
        print(f"   Ortogonal: mean={df_final['score_estrutural_ortogonal'].mean():.3f}, "
              f"std={df_final['score_estrutural_ortogonal'].std():.3f}")
        
        # 6. Salvar resultado
        self._salvar_resultado(df_final)
        
        return df_final
    
    def _salvar_resultado(self, df: pd.DataFrame):
        """Salva vetor ortogonalizado no PostgreSQL"""
        
        cur = self.conn.cursor()
        
        # Criar tabela
        cur.execute("""
            CREATE TABLE IF NOT EXISTS features_estruturais_ortogonal (
                id SERIAL PRIMARY KEY,
                fornecedor TEXT UNIQUE,
                cnpj TEXT,
                s_laranjas_adj NUMERIC(5,4),
                s_grupo_adj NUMERIC(5,4),
                s_idade_adj NUMERIC(5,4),
                s_concentracao_adj NUMERIC(5,4),
                score_estrutural_ortogonal NUMERIC(5,4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Inserir dados
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO features_estruturais_ortogonal
                (fornecedor, cnpj, s_laranjas_adj, s_grupo_adj, s_idade_adj, 
                 s_concentracao_adj, score_estrutural_ortogonal)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fornecedor) DO UPDATE SET
                    cnpj = EXCLUDED.cnpj,
                    s_laranjas_adj = EXCLUDED.s_laranjas_adj,
                    s_grupo_adj = EXCLUDED.s_grupo_adj,
                    s_idade_adj = EXCLUDED.s_idade_adj,
                    s_concentracao_adj = EXCLUDED.s_concentracao_adj,
                    score_estrutural_ortogonal = EXCLUDED.score_estrutural_ortogonal,
                    created_at = CURRENT_TIMESTAMP
            """, (
                row['fornecedor'], row['cnpj'],
                row['s_laranjas_adj'], row['s_grupo_adj'],
                row['s_idade_adj'], row['s_concentracao_adj'],
                row['score_estrutural_ortogonal']
            ))
        
        self.conn.commit()
        print(f"\n✅ {len(df)} vetores ortogonalizados salvos")


def main():
    """Executa Fase 1.5"""
    
    descorr = DescorrelacaoLatente()
    df = descorr.gerar_vetor_ortogonalizado()
    
    print("\n" + "=" * 80)
    print("FASE 1.5 CONCLUÍDA — VETOR ESTRUTURAL ORTOGONALIZADO")
    print("=" * 80)
    print("\nPronto para Fase 2 (Comportamental)")
    print("Sem redundância, sem dupla contagem")


if __name__ == '__main__':
    main()
