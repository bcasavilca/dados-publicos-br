#!/usr/bin/env python3
"""
MATCHING CNPJ - Nível 5: Estrutura Empresarial

Resolve: nome sujo (contrato) → CNPJ limpo (Receita Federal)
Técnicas: normalização + fuzzy matching + score de confiança
"""

import psycopg2
import pandas as pd
import numpy as np
from rapidfuzz import fuzz, process
import unicodedata
import re
import os
from typing import List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NormalizadorNomes:
    """Normaliza nomes de empresas para comparação"""
    
    TIPOS_SOCIETARIOS = [
        'ltda', 'limitada', 'sa', 's/a', 's a', 'me', 'epp', 
        'eireli', 'me', 'ei', 'filial', 'matriz'
    ]
    
    @staticmethod
    def normalizar(nome: str) -> str:
        """Pipeline de normalização completa"""
        if not nome:
            return ""
        
        # Lowercase
        nome = nome.lower()
        
        # Remover acentos
        nome = unicodedata.normalize('NFKD', nome)
        nome = nome.encode('ascii', 'ignore').decode('utf-8')
        
        # Remover tipos societários
        for tipo in NormalizadorNomes.TIPOS_SOCIETARIOS:
            nome = re.sub(rf'\s+{tipo}\b', '', nome)
        
        # Remover caracteres especiais, manter apenas alfanuméricos e espaços
        nome = re.sub(r'[^a-z0-9\s]', ' ', nome)
        
        # Remover múltiplos espaços
        nome = re.sub(r'\s+', ' ', nome).strip()
        
        return nome
    
    @staticmethod
    def extrair_sigla(nome: str) -> Optional[str]:
        """Extrai sigla se existir (ex: EMPRESA X LTDA → EX)"""
        palavras = nome.upper().split()
        if len(palavras) >= 2:
            return ''.join([p[0] for p in palavras[:3] if p])
        return None


class MatcherCNPJ:
    """Faz matching entre fornecedores e CNPJs usando fuzzy logic"""
    
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.conn = None
        self.cache_empresas = {}  # Cache de empresas normalizadas
        
    def connect(self):
        self.conn = psycopg2.connect(self.db_url)
        return self
    
    def carregar_empresas(self) -> pd.DataFrame:
        """Carrega todas as empresas para memória (com cache)"""
        logger.info("Carregando empresas...")
        
        query = """
        SELECT 
            cnpj,
            razao_social,
            nome_fantasia,
            NormalizadorNomes.normalizar(razao_social) AS razao_norm
        FROM empresas
        """
        
        df = pd.read_sql(query, self.conn)
        
        # Criar índice de busca
        self.cache_empresas = {
            row['razao_norm']: {
                'cnpj': row['cnpj'],
                'razao': row['razao_social'],
                'fantasia': row['nome_fantasia']
            }
            for _, row in df.iterrows()
        }
        
        logger.info(f"{len(self.cache_empresas)} empresas carregadas")
        return df
    
    def calcular_similaridade(self, nome_fornecedor: str, nome_empresa: str) -> float:
        """Calcula score de similaridade entre dois nomes"""
        
        # Normalizar ambos
        norm_forn = NormalizadorNomes.normalizar(nome_fornecedor)
        norm_emp = NormalizadorNomes.normalizar(nome_empresa)
        
        if not norm_forn or not norm_emp:
            return 0.0
        
        # Múltiplas métricas de similaridade
        scores = []
        
        # 1. Token sort ratio (ordem das palavras não importa)
        scores.append(fuzz.token_sort_ratio(norm_forn, norm_emp))
        
        # 2. Token set ratio (lida com palavras extras)
        scores.append(fuzz.token_set_ratio(norm_forn, norm_emp))
        
        # 3. Partial ratio (substring matching)
        scores.append(fuzz.partial_ratio(norm_forn, norm_emp))
        
        # Score final: média ponderada
        # Token sort mais importante para nomes de empresa
        return (scores[0] * 0.5 + scores[1] * 0.3 + scores[2] * 0.2)
    
    def encontrar_melhor_match(self, nome_fornecedor: str, 
                               limite_score: float = 80.0) -> Optional[Tuple]:
        """
        Encontra o melhor CNPJ para um fornecedor
        
        Returns:
            (cnpj, razao_social, score) ou None
        """
        norm_forn = NormalizadorNomes.normalizar(nome_fornecedor)
        
        if not self.cache_empresas:
            self.carregar_empresas()
        
        # Busca rápida com RapidFuzz
        resultados = process.extract(
            norm_forn,
            self.cache_empresas.keys(),
            scorer=fuzz.token_sort_ratio,
            limit=5
        )
        
        if not resultados:
            return None
        
        # Pegar melhor resultado
        melhor_norm, score_bruto, _ = resultados[0]
        
        # Recalcular com métricas completas
        empresa = self.cache_empresas.get(melhor_norm, {})
        score_final = self.calcular_similaridade(
            nome_fornecedor, 
            empresa.get('razao', '')
        )
        
        if score_final >= limite_score:
            return (
                empresa.get('cnpj'),
                empresa.get('razao'),
                round(score_final, 2)
            )
        
        return None
    
    def match_batch(self, fornecedores: List[str], 
                   limite_score: float = 80.0,
                   auto_confirmar: float = 95.0) -> pd.DataFrame:
        """
        Faz matching em lote para múltiplos fornecedores
        """
        logger.info(f"Processando {len(fornecedores)} fornecedores...")
        
        resultados = []
        
        for nome in fornecedores:
            match = self.encontrar_melhor_match(nome, limite_score)
            
            if match:
                cnpj, razao, score = match
                status = 'CONFIRMADO' if score >= auto_confirmar else 'REVISAR'
                resultados.append({
                    'fornecedor': nome,
                    'cnpj': cnpj,
                    'razao_social_match': razao,
                    'score_match': score,
                    'status': status,
                    'metodo': 'FUZZY'
                })
            else:
                resultados.append({
                    'fornecedor': nome,
                    'cnpj': None,
                    'razao_social_match': None,
                    'score_match': 0,
                    'status': 'PENDENTE',
                    'metodo': None
                })
        
        df = pd.DataFrame(resultados)
        
        # Stats
        confirmados = len(df[df['status'] == 'CONFIRMADO'])
        revisar = len(df[df['status'] == 'REVISAR'])
        pendentes = len(df[df['status'] == 'PENDENTE'])
        
        logger.info(f"Resultados: {confirmados} confirmados, {revisar} revisar, {pendentes} pendentes")
        
        return df
    
    def salvar_matches(self, df: pd.DataFrame):
        """Salva resultados no PostgreSQL"""
        logger.info("Salvando matches...")
        
        cur = self.conn.cursor()
        
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO fornecedor_cnpj 
                (fornecedor, cnpj, razao_social_match, score_match, status, metodo)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (fornecedor) DO UPDATE SET
                    cnpj = EXCLUDED.cnpj,
                    razao_social_match = EXCLUDED.razao_social_match,
                    score_match = EXCLUDED.score_match,
                    status = EXCLUDED.status,
                    metodo = EXCLUDED.metodo,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                row['fornecedor'],
                row['cnpj'],
                row['razao_social_match'],
                row['score_match'],
                row['status'],
                row['metodo']
            ))
        
        self.conn.commit()
        logger.info(f"{len(df)} registros salvos")
    
    def processar_todos_fornecedores(self, limite_score: float = 80.0):
        """Pipeline completo: buscar fornecedores → match → salvar"""
        
        # Buscar fornecedores únicos não processados
        query = """
        SELECT DISTINCT fornecedor 
        FROM sp_contratos
        WHERE fornecedor NOT IN (
            SELECT fornecedor FROM fornecedor_cnpj 
            WHERE status IN ('CONFIRMADO', 'REVISAR')
        )
        """
        
        df_forn = pd.read_sql(query, self.conn)
        
        if len(df_forn) == 0:
            logger.info("Nenhum fornecedor pendente de matching")
            return
        
        logger.info(f"{len(df_forn)} fornecedores para processar")
        
        # Fazer matching
        resultados = self.match_batch(
            df_forn['fornecedor'].tolist(),
            limite_score=limite_score
        )
        
        # Salvar
        self.salvar_matches(resultados)
        
        return resultados


class DetectorRelacionamentos:
    """Detecta relacionamentos societários suspeitos"""
    
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.conn = psycopg2.connect(self.db_url)
    
    def detectar_empresas_irmaas(self, cnpj: str) -> pd.DataFrame:
        """Encontra empresas com sócios em comum"""
        
        query = """
        SELECT
            e2.cnpj,
            e2.razao_social,
            s.nome AS socio_comum,
            es2.percentual,
            r.tipo_relacionamento
        FROM vw_relacionamentos_societarios r
        JOIN empresas e2 ON e2.cnpj = r.cnpj_b
        JOIN socios s ON s.nome = r.socio_nome
        JOIN empresa_socio es2 ON es2.cnpj = e2.cnpj AND es2.socio_id = s.id
        WHERE r.cnpj_a = %(cnpj)s
        ORDER BY es2.percentual DESC
        """
        
        return pd.read_sql(query, self.conn, params={'cnpj': cnpj})
    
    def detectar_laranjas(self, min_empresas: int = 5) -> pd.DataFrame:
        """Sócios com muitas empresas (possível laranja)"""
        
        query = """
        SELECT
            s.nome,
            s.documento,
            COUNT(DISTINCT es.cnpj) AS qtd_empresas,
            ARRAY_AGG(DISTINCT e.razao_social) AS empresas
        FROM socios s
        JOIN empresa_socio es ON es.socio_id = s.id
        JOIN empresas e ON e.cnpj = es.cnpj
        GROUP BY s.id, s.nome, s.documento
        HAVING COUNT(DISTINCT es.cnpj) >= %(min_emp)s
        ORDER BY qtd_empresas DESC
        """
        
        return pd.read_sql(query, self.conn, params={'min_emp': min_empresas})
    
    def analisar_grupo_economico(self, grupo_id: int) -> dict:
        """Análise detalhada de um grupo econômico"""
        
        query = """
        SELECT empresas
        FROM vw_grupos_economicos
        WHERE grupo_id = %(grupo_id)s
        """
        
        df = pd.read_sql(query, self.conn, params={'grupo_id': grupo_id})
        
        if len(df) == 0:
            return None
        
        empresas = df.iloc[0]['empresas']
        
        # Buscar contratos dessas empresas
        query_contratos = """
        SELECT 
            c.*,
            fc.cnpj
        FROM sp_contratos c
        JOIN fornecedor_cnpj fc ON fc.fornecedor = c.fornecedor
        WHERE fc.cnpj = ANY(%(empresas)s)
        ORDER BY c.valor DESC
        """
        
        df_contratos = pd.read_sql(
            query_contratos, 
            self.conn, 
            params={'empresas': empresas}
        )
        
        return {
            'grupo_id': grupo_id,
            'qtd_empresas': len(empresas),
            'empresas': empresas,
            'qtd_contratos': len(df_contratos),
            'valor_total': df_contratos['valor'].sum(),
            'contratos': df_contratos.to_dict('records')
        }


def main():
    """Pipeline completo de matching"""
    
    print("🚀 NÍVEL 5: ESTRUTURA EMPRESARIAL")
    print("=" * 60)
    
    # 1. Matching
    matcher = MatcherCNPJ().connect()
    resultados = matcher.processar_todos_fornecedores(limite_score=80.0)
    
    if resultados is not None:
        print(f"\n✅ {len(resultados)} fornecedores processados")
        print(f"   - Confirmados: {len(resultados[resultados['status'] == 'CONFIRMADO'])}")
        print(f"   - Revisar: {len(resultados[resultados['status'] == 'REVISAR'])}")
        print(f"   - Pendentes: {len(resultados[resultados['status'] == 'PENDENTE'])}")
    
    # 2. Análise de relacionamentos
    detector = DetectorRelacionamentos()
    
    # Exemplo: detectar laranjas
    laranjas = detector.detectar_laranjas(min_empresas=5)
    if len(laranjas) > 0:
        print(f"\n🚨 {len(laranjas)} sócios com múltiplas empresas detectados")
        print(laranjas[['nome', 'qtd_empresas']].head())
    
    print("\n✅ Pipeline concluído!")


if __name__ == '__main__':
    main()
