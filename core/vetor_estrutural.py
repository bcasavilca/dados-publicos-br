#!/usr/bin/env python3
"""
VETOR ESTRUTURAL PROBABILISTICO V1.0

Features continuas (0-1) da camada estrutural:
- s_laranjas: sigmoid(num_empresas_socio)
- s_grupo_economico: centralidade no grafo
- s_idade_risco: decay exponencial da idade
- s_concentracao: entropia da distribuicao

Nao gera alertas binarios - gera features gradiente.
Alertas sao derivados depois (regras em runtime).
"""

import psycopg2
import pandas as pd
import numpy as np
from scipy.stats import entropy
from typing import Dict, List, Tuple
from dataclasses import dataclass
import os
from datetime import datetime, date


@dataclass
class VetorEstrutural:
    """Vetor de features estruturais (continuo, 0-1)"""
    fornecedor: str
    cnpj: str
    
    # Features
    s_laranjas: float          # 0-1: probabilistico
    s_grupo_economico: float     # 0-1: centralidade
    s_idade_risco: float         # 0-1: empresa nova = alto
    s_concentracao: float        # 0-1: concentracao societaria
    
    # Metadata
    data_geracao: datetime


class MotorFeaturesEstruturais:
    """
    Motor probabilistico de features estruturais
    
    Matematica:
    - Sigmoid: 1 / (1 + e^(-x))
    - Entropia: -sum(p * log(p))
    - Decay: e^(-x/lambda)
    """
    
    # Hyperparameters (tunaveis)
    BASELINE_LARANJAS = 5        # num empresas onde risco = 50%
    STEEPNESS_LARANJAS = 0.5     # quao rapido cresce
    LAMBDA_IDADE = 365           # dias para decay a 1/e
    MAX_CENTRALIDADE = 10        # normalizacao
    
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.conn = psycopg2.connect(self.db_url)
        
        # Cache de estatisticas globais
        self.stats = self._calcular_stats_globais()
    
    def _calcular_stats_globais(self) -> Dict:
        """Calcula estatisticas de referencia para normalizacao"""
        cur = self.conn.cursor()
        
        # Max empresas por socio (para normalizacao)
        cur.execute("""
            SELECT MAX(cnt) FROM (
                SELECT COUNT(DISTINCT cnpj) as cnt
                FROM empresa_socio
                GROUP BY socio_id
            ) t
        """)
        max_empresas_socio = cur.fetchone()[0] or 1
        
        return {
            'max_empresas_socio': max_empresas_socio,
            'max_centralidade': self.MAX_CENTRALIDADE
        }
    
    # ═════════════════════════════════════════════════════════════════════
    # FEATURE 1: s_laranjas (SIGMOID)
    # ═════════════════════════════════════════════════════════════════════
    
    def calcular_s_laranjas(self, cnpj: str) -> float:
        """
        s_laranjas = sigmoid(num_empresas_socio - baseline)
        
        sigmoid(x) = 1 / (1 + e^(-steepness * x))
        
        Output: 0 (poucas empresas) → 1 (muitas empresas)
        """
        cur = self.conn.cursor()
        
        # Numero de empresas que cada socio desta empresa tem
        cur.execute("""
            SELECT 
                s.id,
                COUNT(DISTINCT es2.cnpj) as num_empresas
            FROM empresa_socio es1
            JOIN socios s ON s.id = es1.socio_id
            JOIN empresa_socio es2 ON es2.socio_id = s.id
            WHERE es1.cnpj = %s
            GROUP BY s.id
        """, (cnpj,))
        
        resultados = cur.fetchall()
        
        if not resultados:
            return 0.0
        
        # Pegar maximo (socio com mais empresas)
        max_empresas = max(r[1] for r in resultados)
        
        # Sigmoid centrada no baseline
        x = max_empresas - self.BASELINE_LARANJAS
        s_laranjas = 1 / (1 + np.exp(-self.STEEPNESS_LARANJAS * x))
        
        return round(float(s_laranjas), 4)
    
    # ═════════════════════════════════════════════════════════════════════
    # FEATURE 2: s_grupo_economico (CENTRALIDADE)
    # ═════════════════════════════════════════════════════════════════════
    
    def calcular_s_grupo(self, cnpj: str) -> float:
        """
        s_grupo = centralidade_empresa / max_centralidade
        
        Centralidade = quantos outros CNPJs estao conectados
        via socios em comum
        """
        cur = self.conn.cursor()
        
        # Empresas conectadas via socios
        cur.execute("""
            SELECT COUNT(DISTINCT es2.cnpj)
            FROM empresa_socio es1
            JOIN empresa_socio es2 ON es1.socio_id = es2.socio_id
            WHERE es1.cnpj = %s
              AND es2.cnpj != %s
        """, (cnpj, cnpj))
        
        centralidade = cur.fetchone()[0] or 0
        
        # Normalizar
        s_grupo = min(centralidade / self.stats['max_centralidade'], 1.0)
        
        return round(float(s_grupo), 4)
    
    # ═════════════════════════════════════════════════════════════════════
    # FEATURE 3: s_idade_risco (DECAY EXPONENCIAL)
    # ═════════════════════════════════════════════════════════════════════
    
    def calcular_s_idade(self, cnpj: str) -> float:
        """
        s_idade = exp(-idade_dias / lambda)
        
        Empresa nova (poucos dias) = score alto (risco)
        Empresa antiga (muitos dias) = score baixo
        
        Lambda = 365 dias (1 ano para cair a 37%)
        """
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT data_abertura
            FROM empresas
            WHERE cnpj = %s
        """, (cnpj,))
        
        result = cur.fetchone()
        
        if not result or not result[0]:
            return 0.5  # Neutro se nao souber
        
        data_abertura = result[0]
        if isinstance(data_abertura, str):
            data_abertura = datetime.strptime(data_abertura, '%Y-%m-%d').date()
        
        idade_dias = (date.today() - data_abertura).days
        
        # Decay exponencial
        s_idade = np.exp(-idade_dias / self.LAMBDA_IDADE)
        
        return round(float(s_idade), 4)
    
    # ═════════════════════════════════════════════════════════════════════
    # FEATURE 4: s_concentracao (ENTROPIA)
    # ═════════════════════════════════════════════════════════════════════
    
    def calcular_s_concentracao(self, cnpj: str) -> float:
        """
        s_concentracao = 1 - entropia_normalizada
        
        Se um socio domina (90%), entropia baixa, concentracao alta
        Se socios equilibrados (50/50), entropia alta, concentracao baixa
        """
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT percentual
            FROM empresa_socio
            WHERE cnpj = %s AND percentual IS NOT NULL
        """)
        
        percentuais = [r[0] for r in cur.fetchall() if r[0] is not None]
        
        if len(percentuais) <= 1:
            return 1.0  # Monopolio = concentracao maxima
        
        # Normalizar para somar 1
        total = sum(percentuais)
        if total == 0:
            return 0.5
        
        probs = np.array(percentuais) / total
        
        # Entropia de Shannon (normalizada)
        entropia = entropy(probs, base=2)  # base 2 = bits
        entropia_max = np.log2(len(percentuais))
        
        if entropia_max == 0:
            return 1.0
        
        entropia_norm = entropia / entropia_max
        
        # Concentracao = inverso da entropia
        s_concentracao = 1 - entropia_norm
        
        return round(float(s_concentracao), 4)
    
    # ═════════════════════════════════════════════════════════════════════
    # VETOR COMPLETO
    # ═════════════════════════════════════════════════════════════════════
    
    def calcular_vetor(self, fornecedor: str, cnpj: str) -> VetorEstrutural:
        """Calcula vetor completo de features"""
        
        return VetorEstrutural(
            fornecedor=fornecedor,
            cnpj=cnpj,
            s_laranjas=self.calcular_s_laranjas(cnpj),
            s_grupo_economico=self.calcular_s_grupo(cnpj),
            s_idade_risco=self.calcular_s_idade(cnpj),
            s_concentracao=self.calcular_s_concentracao(cnpj),
            data_geracao=datetime.now()
        )
    
    def processar_todos(self) -> pd.DataFrame:
        """Processa todos os fornecedores com CNPJ confirmado"""
        
        print("🔬 Gerando vetores estruturais probabilisticos...")
        
        query = """
            SELECT fornecedor, cnpj
            FROM fornecedor_cnpj
            WHERE status = 'CONFIRMADO'
              AND score_match >= 90
        """
        
        df_forn = pd.read_sql(query, self.conn)
        
        vetores = []
        for _, row in df_forn.iterrows():
            vetor = self.calcular_vetor(row['fornecedor'], row['cnpj'])
            vetores.append({
                'fornecedor': vetor.fornecedor,
                'cnpj': vetor.cnpj,
                's_laranjas': vetor.s_laranjas,
                's_grupo': vetor.s_grupo_economico,
                's_idade': vetor.s_idade_risco,
                's_concentracao': vetor.s_concentracao,
                'score_estrutural': self._combinar_features(vetor)
            })
        
        df = pd.DataFrame(vetores)
        
        # Salvar no PostgreSQL
        self._salvar_vetores(df)
        
        print(f"✅ {len(df)} vetores gerados")
        print("\n📊 Distribuicao das features:")
        print(df[['s_laranjas', 's_grupo', 's_idade', 's_concentracao']].describe())
        
        return df
    
    def _combinar_features(self, vetor: VetorEstrutural) -> float:
        """
        Combina features em score estrutural unico
        
        Peso: laranjas 40%, grupo 30%, idade 20%, concentracao 10%
        """
        return round(
            vetor.s_laranjas * 0.4 +
            vetor.s_grupo_economico * 0.3 +
            vetor.s_idade_risco * 0.2 +
            vetor.s_concentracao * 0.1,
            4
        )
    
    def _salvar_vetores(self, df: pd.DataFrame):
        """Salva vetores no PostgreSQL"""
        
        cur = self.conn.cursor()
        
        # Criar tabela
        cur.execute("""
            CREATE TABLE IF NOT EXISTS features_estruturais (
                id SERIAL PRIMARY KEY,
                fornecedor TEXT,
                cnpj TEXT,
                s_laranjas NUMERIC(5,4),
                s_grupo_economico NUMERIC(5,4),
                s_idade_risco NUMERIC(5,4),
                s_concentracao NUMERIC(5,4),
                score_estrutural NUMERIC(5,4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(fornecedor)
            )
        """)
        
        # Inserir
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO features_estruturais 
                (fornecedor, cnpj, s_laranjas, s_grupo_economico, 
                 s_idade_risco, s_concentracao, score_estrutural)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fornecedor) DO UPDATE SET
                    s_laranjas = EXCLUDED.s_laranjas,
                    s_grupo_economico = EXCLUDED.s_grupo_economico,
                    s_idade_risco = EXCLUDED.s_idade_risco,
                    s_concentracao = EXCLUDED.s_concentracao,
                    score_estrutural = EXCLUDED.score_estrutural,
                    created_at = CURRENT_TIMESTAMP
            """, (
                row['fornecedor'], row['cnpj'],
                row['s_laranjas'], row['s_grupo'],
                row['s_idade'], row['s_concentracao'],
                row['score_estrutural']
            ))
        
        self.conn.commit()
        print(f"✅ {len(df)} vetores salvos em features_estruturais")


# ═════════════════════════════════════════════════════════════════════
# GERADOR DE ALERTAS DERIVADOS (DEPOIS DO VETOR)
# ═════════════════════════════════════════════════════════════════════

class GeradorAlertasDerivados:
    """Gera alertas a partir das features (regras em runtime)"""
    
    THRESHOLDS = {
        'CRITICO': 0.85,
        'ALTO': 0.70,
        'MEDIO': 0.50
    }
    
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.conn = psycopg2.connect(self.db_url)
    
    def gerar_alertas(self) -> pd.DataFrame:
        """Gera alertas a partir das features estruturais"""
        
        print("\n🚨 Gerando alertas derivados...")
        
        query = """
            SELECT * FROM features_estruturais
            WHERE score_estrutural >= %(min)s
            ORDER BY score_estrutural DESC
        """
        
        df = pd.read_sql(query, self.conn, params={
            'min': self.THRESHOLDS['MEDIO']
        })
        
        alertas = []
        for _, row in df.iterrows():
            score = row['score_estrutural']
            
            # Classificar severidade
            if score >= self.THRESHOLDS['CRITICO']:
                sev = 'CRITICO'
            elif score >= self.THRESHOLDS['ALTO']:
                sev = 'ALTO'
            else:
                sev = 'MEDIO'
            
            # Detalhar componentes
            componentes = []
            if row['s_laranjas'] > 0.7:
                componentes.append(f"laranjas({row['s_laranjas']:.2f})")
            if row['s_grupo_economico'] > 0.7:
                componentes.append(f"grupo({row['s_grupo_economico']:.2f})")
            if row['s_idade_risco'] > 0.7:
                componentes.append(f"idade({row['s_idade_risco']:.2f})")
            if row['s_concentracao'] > 0.7:
                componentes.append(f"concentracao({row['s_concentracao']:.2f})")
            
            alertas.append({
                'fornecedor': row['fornecedor'],
                'cnpj': row['cnpj'],
                'severidade': sev,
                'score_estrutural': score,
                'componentes': ', '.join(componentes) if componentes else 'mix',
                's_laranjas': row['s_laranjas'],
                's_grupo': row['s_grupo_economico'],
                's_idade': row['s_idade_risco'],
                's_concentracao': row['s_concentracao']
            })
        
        df_alertas = pd.DataFrame(alertas)
        
        print(f"✅ {len(alertas)} alertas derivados gerados")
        print(f"   CRITICO: {len([a for a in alertas if a['severidade'] == 'CRITICO'])}")
        print(f"   ALTO: {len([a for a in alertas if a['severidade'] == 'ALTO'])}")
        
        return df_alertas


def main():
    """Pipeline completo"""
    
    print("=" * 80)
    print("VETOR ESTRUTURAL PROBABILISTICO")
    print("=" * 80)
    
    # Fase 1: Gerar features
    motor = MotorFeaturesEstruturais()
    df_vetores = motor.processar_todos()
    
    # Fase 2: Gerar alertas derivados
    gerador = GeradorAlertasDerivados()
    df_alertas = gerador.gerar_alertas()
    
    print("\n" + "=" * 80)
    print("TOP 10 ALERTAS CRITICOS:")
    print("=" * 80)
    
    criticos = df_alertas[df_alertas['severidade'] == 'CRITICO'].head(10)
    for _, row in criticos.iterrows():
        print(f"\n🔴 {row['fornecedor'][:50]}")
        print(f"   Score: {row['score_estrutural']:.3f} | Componentes: {row['componentes']}")
    
    print("\n✅ Pipeline concluido!")


if __name__ == '__main__':
    main()
