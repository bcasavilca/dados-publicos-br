#!/usr/bin/env python3
"""
FASE 2 — FEATURES COMPORTAMENTAIS

Camada temporal de comportamento de fornecedores:
- s_rodizio: anti-coincidencia (nao aparecem juntos)
- s_entropia_temporal: distribuicao uniforme vs concentrada
- s_burst: picos anomalos de contratos
- s_persistencia: presenca continua vs esporadica

Tudo continuo (0-1), sem binarios.
"""

import psycopg2
import pandas as pd
import numpy as np
from scipy.stats import entropy, zscore
from typing import Dict, List
from datetime import datetime
import os


class FeaturesComportamentais:
    """
    Extrai padroes comportamentais temporais de fornecedores
    
    Matematica:
    - Rodizio: 1 - (co_real / co_esperada)
    - Entropia: -sum(p * log(p)) normalizada
    - Burst: z-score de contratos por mes
    - Persistencia: meses ativos / total meses
    """
    
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.conn = psycopg2.connect(self.db_url)
        
    # ═════════════════════════════════════════════════════════════════
    # FEATURE 1: s_rodizio (ANTI-COINCIDENCIA)
    # ═════════════════════════════════════════════════════════════════
    
    def calcular_s_rodizio(self, fornecedor: str, top_n: int = 10) -> float:
        """
        Calcula score de rodizio (anti-coincidencia) com outros fornecedores
        
        Logica:
        - Se fornecedor A e B nunca aparecem juntos mas deveriam
        - Isso sugere alternancia de mercado (possivel cartel)
        
        Matematica:
        s_rodizio = 1 - (co_ocorrencia_real / co_ocorrencia_esperada)
        
        Retorna: 0 (sempre juntos) -> 1 (nunca juntos)
        """
        cur = self.conn.cursor()
        
        # Buscar meses onde este fornecedor atuou
        cur.execute("""
            SELECT DISTINCT 
                TO_CHAR(TO_DATE(data_assinatura, 'DD/MM/YYYY'), 'YYYY-MM') as mes
            FROM sp_contratos
            WHERE fornecedor = %s
              AND data_assinatura IS NOT NULL
            ORDER BY mes
        """, (fornecedor,))
        
        meses_a = [r[0] for r in cur.fetchall()]
        
        if len(meses_a) < 3:
            return 0.0  # Pouca atividade para analisar
        
        # Buscar fornecedores similares (mesma categoria)
        cur.execute("""
            SELECT categoria_final
            FROM vw_categoria_final vcf
            JOIN sp_contratos c ON c.fornecedor = vcf.fornecedor
            WHERE c.fornecedor = %s
            LIMIT 1
        """, (fornecedor,))
        
        result = cur.fetchone()
        categoria = result[0] if result else None
        
        # Buscar outros fornecedores da mesma categoria
        if categoria:
            cur.execute("""
                SELECT DISTINCT c.fornecedor
                FROM sp_contratos c
                JOIN vw_categoria_final vcf ON vcf.fornecedor = c.fornecedor
                WHERE vcf.categoria_final = %s
                  AND c.fornecedor != %s
                  AND c.data_assinatura IS NOT NULL
                LIMIT %s
            """, (categoria, fornecedor, top_n))
        else:
            cur.execute("""
                SELECT DISTINCT fornecedor
                FROM sp_contratos
                WHERE fornecedor != %s
                  AND data_assinatura IS NOT NULL
                LIMIT %s
            """, (fornecedor, top_n))
        
        outros_fornecedores = [r[0] for r in cur.fetchall()]
        
        if not outros_fornecedores:
            return 0.0
        
        # Calcular rodizio para cada par
        rodizios = []
        for forn_b in outros_fornecedores:
            # Meses de B
            cur.execute("""
                SELECT DISTINCT 
                    TO_CHAR(TO_DATE(data_assinatura, 'DD/MM/YYYY'), 'YYYY-MM') as mes
                FROM sp_contratos
                WHERE fornecedor = %s
                  AND data_assinatura IS NOT NULL
            """, (forn_b,))
            
            meses_b = [r[0] for r in cur.fetchall()]
            
            if len(meses_b) < 2:
                continue
            
            # Co-ocorrencia real
            meses_juntos = len(set(meses_a) & set(meses_b))
            
            # Co-ocorrencia esperada (se independentes)
            total_meses = len(set(meses_a) | set(meses_b))
            p_a = len(meses_a) / total_meses
            p_b = len(meses_b) / total_meses
            esperado = p_a * p_b * total_meses
            
            if esperado > 0:
                ratio = meses_juntos / esperado
                # Score: 1 = nunca juntos (suspeito), 0 = sempre juntos
                rodizio = max(0, 1 - ratio)
                rodizios.append(rodizio)
        
        if not rodizios:
            return 0.0
        
        # Retorna maximo (pior caso)
        return round(max(rodizios), 4)
    
    # ═════════════════════════════════════════════════════════════════
    # FEATURE 2: s_entropia_temporal
    # ═════════════════════════════════════════════════════════════════
    
    def calcular_s_entropia(self, fornecedor: str) -> float:
        """
        Entropia da distribuicao temporal de contratos
        
        Baixa entropia = concentrado (poucos meses com muitos contratos)
        Alta entropia = distribuido uniformemente
        
        Matematica:
        H = -sum(p_i * log(p_i)) / log(n)
        s_entropia = H (normalizada 0-1)
        """
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT 
                TO_CHAR(TO_DATE(data_assinatura, 'DD/MM/YYYY'), 'YYYY-MM') as mes,
                COUNT(*) as qtd
            FROM sp_contratos
            WHERE fornecedor = %s
              AND data_assinatura IS NOT NULL
            GROUP BY mes
            ORDER BY mes
        """, (fornecedor,))
        
        resultados = cur.fetchall()
        
        if len(resultados) <= 1:
            return 0.5  # Neutro
        
        counts = np.array([r[1] for r in resultados])
        
        # Probabilidades
        probs = counts / counts.sum()
        
        # Entropia de Shannon
        H = entropy(probs, base=2)
        H_max = np.log2(len(probs))
        
        if H_max == 0:
            return 0.0
        
        # Normalizar
        return round(H / H_max, 4)
    
    # ═════════════════════════════════════════════════════════════════
    # FEATURE 3: s_burst (PICO ANOMALO)
    # ═════════════════════════════════════════════════════════════════
    
    def calcular_s_burst(self, fornecedor: str) -> float:
        """
        Detecta picos anomalos (bursts) na serie temporal
        
        Matematica:
        z = (x - media) / desvio
        s_burst = sigmoid(z) se z > 2, senao 0
        """
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT 
                TO_CHAR(TO_DATE(data_assinatura, 'DD/MM/YYYY'), 'YYYY-MM') as mes,
                COUNT(*) as qtd,
                SUM(valor) as valor
            FROM sp_contratos
            WHERE fornecedor = %s
              AND data_assinatura IS NOT NULL
            GROUP BY mes
            ORDER BY mes
        """, (fornecedor,))
        
        resultados = cur.fetchall()
        
        if len(resultados) < 4:
            return 0.0
        
        # Usar valor ou quantidade? Usar valor (mais relevante)
        valores = np.array([r[2] if r[2] else 0 for r in resultados], dtype=float)
        
        if valores.std() == 0:
            return 0.0
        
        # Z-score
        z_scores = np.abs(zscore(valores))
        z_max = z_scores.max()
        
        # Score burst: so ativa se z > 2
        if z_max > 2:
            # Sigmoid para suavizar
            s_burst = 1 / (1 + np.exp(-(z_max - 2)))
            return round(s_burst, 4)
        
        return 0.0
    
    # ═════════════════════════════════════════════════════════════════
    # FEATURE 4: s_persistencia
    # ═════════════════════════════════════════════════════════════════
    
    def calcular_s_persistencia(self, fornecedor: str) -> float:
        """
        Mede continuidade da presenca do fornecedor
        
        Persistencia alta = meses consecutivos (servico continuo)
        Persistencia baixa = meses esporadicos (possivel rodizio)
        
        Matematica:
        meses_ativos / (max_mes - min_mes + 1)
        """
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT 
                MIN(TO_DATE(data_assinatura, 'DD/MM/YYYY')),
                MAX(TO_DATE(data_assinatura, 'DD/MM/YYYY')),
                COUNT(DISTINCT TO_CHAR(TO_DATE(data_assinatura, 'DD/MM/YYYY'), 'YYYY-MM'))
            FROM sp_contratos
            WHERE fornecedor = %s
              AND data_assinatura IS NOT NULL
        """, (fornecedor,))
        
        result = cur.fetchone()
        
        if not result or not result[0] or not result[1]:
            return 0.5
        
        data_min, data_max, meses_ativos = result
        
        # Periodo total em meses
        periodo_meses = (data_max.year - data_min.year) * 12 + (data_max.month - data_min.month) + 1
        
        if periodo_meses <= 1:
            return 0.5
        
        # Persistencia = meses ativos / periodo total
        persistencia = meses_ativos / periodo_meses
        
        # Inverter: persistencia BAIXA (esporadico) = score ALTO (suspeito)
        # Usar 1 - persistencia
        return round(1 - persistencia, 4)
    
    # ═════════════════════════════════════════════════════════════════
    # VETOR COMPLETO
    # ═════════════════════════════════════════════════════════════════
    
    def calcular_vetor(self, fornecedor: str) -> Dict:
        """Calcula vetor completo de features comportamentais"""
        
        return {
            'fornecedor': fornecedor,
            's_rodizio': self.calcular_s_rodizio(fornecedor),
            's_entropia': self.calcular_s_entropia(fornecedor),
            's_burst': self.calcular_s_burst(fornecedor),
            's_persistencia': self.calcular_s_persistencia(fornecedor)
        }
    
    def processar_todos(self) -> pd.DataFrame:
        """Processa todos os fornecedores"""
        
        print("📊 Calculando features comportamentais...")
        
        # Fornecedores com CNPJ confirmado
        query = """
            SELECT DISTINCT fornecedor
            FROM fornecedor_cnpj
            WHERE status = 'CONFIRMADO'
              AND score_match >= 90
        """
        
        df_forn = pd.read_sql(query, self.conn)
        
        vetores = []
        for fornecedor in df_forn['fornecedor']:
            vetor = self.calcular_vetor(fornecedor)
            vetor['score_comportamental'] = self._combinar_features(vetor)
            vetores.append(vetor)
        
        df = pd.DataFrame(vetores)
        
        # Salvar
        self._salvar_features(df)
        
        print(f"✅ {len(df)} vetores comportamentais gerados")
        print("\n📈 Distribuicao:")
        print(df[['s_rodizio', 's_entropia', 's_burst', 's_persistencia']].describe())
        
        return df
    
    def _combinar_features(self, vetor: Dict) -> float:
        """Combina features em score comportamental"""
        # Pesos: rodizio mais importante
        return round(
            vetor['s_rodizio'] * 0.40 +
            vetor['s_entropia'] * 0.20 +
            vetor['s_burst'] * 0.25 +
            vetor['s_persistencia'] * 0.15,
            4
        )
    
    def _salvar_features(self, df: pd.DataFrame):
        """Salva no PostgreSQL"""
        
        cur = self.conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS features_comportamentais (
                id SERIAL PRIMARY KEY,
                fornecedor TEXT UNIQUE,
                s_rodizio NUMERIC(5,4),
                s_entropia NUMERIC(5,4),
                s_burst NUMERIC(5,4),
                s_persistencia NUMERIC(5,4),
                score_comportamental NUMERIC(5,4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO features_comportamentais
                (fornecedor, s_rodizio, s_entropia, s_burst, s_persistencia, score_comportamental)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (fornecedor) DO UPDATE SET
                    s_rodizio = EXCLUDED.s_rodizio,
                    s_entropia = EXCLUDED.s_entropia,
                    s_burst = EXCLUDED.s_burst,
                    s_persistencia = EXCLUDED.s_persistencia,
                    score_comportamental = EXCLUDED.score_comportamental,
                    created_at = CURRENT_TIMESTAMP
            """, (
                row['fornecedor'], row['s_rodizio'], row['s_entropia'],
                row['s_burst'], row['s_persistencia'], row['score_comportamental']
            ))
        
        self.conn.commit()
        print(f"✅ {len(df)} features comportamentais salvas")


def main():
    """Pipeline Fase 2"""
    
    print("=" * 80)
    print("FASE 2 — FEATURES COMPORTAMENTAIS")
    print("=" * 80)
    
    motor = FeaturesComportamentais()
    df = motor.processar_todos()
    
    print("\n" + "=" * 80)
    print("FASE 2 CONCLUIDA")
    print("=" * 80)
    print("\nProximo: Fase 3 (Rede/Graph) ou Fase Final (Score Unificado)")


if __name__ == '__main__':
    main()
