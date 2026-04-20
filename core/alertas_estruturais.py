#!/usr/bin/env python3
"""
ALERTAS ESTRUTURAIS — Nível 5 (Isolado)

NÃO integra no score final.
Gera alertas específicos da camada estrutural.

Regras:
- Cada alerta é independente
- Thresholds claros
- Auditável
"""

import psycopg2
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import os

@dataclass
class AlertaEstrutural:
    """Estrutura de alerta para auditoria"""
    tipo: str
    severidade: str  # CRITICO, ALTO, MEDIO, BAIXO
    entidade: str
    descricao: str
    evidencias: Dict
    timestamp: datetime

class GeradorAlertasEstruturais:
    """
    Gera alertas baseados em estrutura societária
    Camada isolada - não afeta score comportamental
    """
    
    # THRESHOLDS (tunáveis)
    THRESHOLDS = {
        'SCORE_MATCH_MINIMO': 90,  # Matching CNPJ confiável
        'EMPRESAS_POR_SOCIO_CRITICO': 10,
        'EMPRESAS_POR_SOCIO_ALTO': 5,
        'SCORE_RELACIONAMENTO_ESTRUTURAL': 0.8,
    }
    
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.conn = psycopg2.connect(self.db_url)
        self.alertas = []
        
    def validar_matching(self) -> pd.DataFrame:
        """
        Valida qualidade do matching CNPJ
        Retorna apenas matches confiáveis (score >= 90)
        """
        print(f"🔍 Validando matching (threshold: {self.THRESHOLDS['SCORE_MATCH_MINIMO']})...")
        
        query = """
        SELECT
            fornecedor,
            cnpj,
            razao_social_match,
            score_match,
            status
        FROM fornecedor_cnpj
        WHERE score_match >= %(threshold)s
          AND status = 'CONFIRMADO'
        ORDER BY score_match DESC
        """
        
        df = pd.read_sql(query, self.conn, params={
            'threshold': self.THRESHOLDS['SCORE_MATCH_MINIMO']
        })
        
        print(f"✅ {len(df)} matches válidos ({len(df)/self._total_fornecedores()*100:.1f}%)")
        
        # Registrar alerta se cobertura baixa
        cobertura = len(df) / self._total_fornecedores()
        if cobertura < 0.5:
            self._adicionar_alerta(AlertaEstrutural(
                tipo='COBERTURA_MATCHING_BAIXA',
                severidade='ALTO',
                entidade='SISTEMA',
                descricao=f'Apenas {cobertura*100:.1f}% dos fornecedores com CNPJ confirmado',
                evidencias={'cobertura': cobertura, 'total_validos': len(df)},
                timestamp=datetime.now()
            ))
        
        return df
    
    def _total_fornecedores(self) -> int:
        """Total de fornecedores únicos"""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT fornecedor) FROM sp_contratos")
        return cur.fetchone()[0]
    
    def detectar_laranjas(self) -> List[AlertaEstrutural]:
        """
        Detecta sócios com múltiplas empresas (possíveis laranjas)
        Threshold: 5+ empresas = ALTO, 10+ = CRITICO
        """
        print("🚨 Detectando laranjas...")
        
        query = """
        SELECT
            s.nome,
            s.documento,
            COUNT(DISTINCT es.cnpj) AS qtd_empresas,
            ARRAY_AGG(DISTINCT e.razao_social) AS empresas,
            SUM(c.valor) AS valor_total_contratos
        FROM socios s
        JOIN empresa_socio es ON es.socio_id = s.id
        JOIN empresas e ON e.cnpj = es.cnpj
        LEFT JOIN fornecedor_cnpj fc ON fc.cnpj = e.cnpj
        LEFT JOIN sp_contratos c ON c.fornecedor = fc.fornecedor
        WHERE fc.status = 'CONFIRMADO'
        GROUP BY s.id, s.nome, s.documento
        HAVING COUNT(DISTINCT es.cnpj) >= %(min_alto)s
        ORDER BY qtd_empresas DESC
        """
        
        df = pd.read_sql(query, self.conn, params={
            'min_alto': self.THRESHOLDS['EMPRESAS_POR_SOCIO_ALTO']
        })
        
        alertas = []
        for _, row in df.iterrows():
            if row['qtd_empresas'] >= self.THRESHOLDS['EMPRESAS_POR_SOCIO_CRITICO']:
                severidade = 'CRITICO'
            else:
                severidade = 'ALTO'
            
            alerta = AlertaEstrutural(
                tipo='SOCIO_MULTIPLAS_EMPRESAS',
                severidade=severidade,
                entidade=row['nome'],
                descricao=f"Sócio em {row['qtd_empresas']} empresas, valor total R$ {row['valor_total_contratos']:,.2f}",
                evidencias={
                    'qtd_empresas': row['qtd_empresas'],
                    'empresas': row['empresas'],
                    'documento': row['documento'],
                    'valor_total': row['valor_total_contratos']
                },
                timestamp=datetime.now()
            )
            alertas.append(alerta)
            self._adicionar_alerta(alerta)
        
        print(f"🔴 {len(alertas)} laranjas detectados")
        return alertas
    
    def detectar_grupos_economicos_ocultos(self) -> List[AlertaEstrutural]:
        """
        Detecta grupos de empresas conectadas por sócios
        que atuam no mesmo órgão (possível cartel estrutural)
        """
        print("🕸️  Detectando grupos econômicos ocultos...")
        
        query = """
        WITH grupos_ativos AS (
            SELECT
                ge.grupo_id,
                ge.empresas,
                ge.socios,
                COUNT(DISTINCT c.fornecedor) AS fornecedores_no_grupo,
                SUM(c.valor) AS valor_total,
                COUNT(DISTINCT c.orgao) AS orgaos_distintos
            FROM vw_grupos_economicos ge
            JOIN fornecedor_cnpj fc ON fc.cnpj = ANY(ge.empresas)
            JOIN sp_contratos c ON c.fornecedor = fc.fornecedor
            WHERE fc.status = 'CONFIRMADO'
            GROUP BY ge.grupo_id, ge.empresas, ge.socios
            HAVING COUNT(DISTINCT c.orgao) >= 1  -- Pelo menos 1 órgão
        )
        SELECT *
        FROM grupos_ativos
        WHERE valor_total > 1000000  -- Apenas grupos significativos
        ORDER BY valor_total DESC
        """
        
        df = pd.read_sql(query, self.conn)
        
        alertas = []
        for _, row in df.iterrows():
            # Detalhar empresas do grupo
            empresas_info = self._detalhar_empresas(row['empresas'])
            
            alerta = AlertaEstrutural(
                tipo='GRUPO_ECONOMICO_ATIVO',
                severidade='CRITICO' if row['valor_total'] > 10000000 else 'ALTO',
                entidade=f"Grupo #{row['grupo_id']}",
                descricao=f"{row['fornecedores_no_grupo']} empresas do grupo, "
                         f"R$ {row['valor_total']:,.2f} em contratos",
                evidencias={
                    'empresas': empresas_info,
                    'socios': row['socios'],
                    'valor_total': row['valor_total'],
                    'orgaos': row['orgaos_distintos']
                },
                timestamp=datetime.now()
            )
            alertas.append(alerta)
            self._adicionar_alerta(alerta)
        
        print(f"🔴 {len(alertas)} grupos econômicos ativos detectados")
        return alertas
    
    def _detalhar_empresas(self, cnpjs: List[str]) -> List[Dict]:
        """Busca detalhes das empresas"""
        cur = self.conn.cursor()
        placeholders = ','.join(['%s'] * len(cnpjs))
        cur.execute(f"""
            SELECT cnpj, razao_social, data_abertura
            FROM empresas
            WHERE cnpj IN ({placeholders})
        """, cnpjs)
        
        return [
            {'cnpj': r[0], 'razao_social': r[1], 'data_abertura': r[2]}
            for r in cur.fetchall()
        ]
    
    def detectar_empresas_novas_valor_alto(self) -> List[AlertaEstrutural]:
        """
        Empresas criadas recentemente (< 1 ano) com contratos grandes
        """
        print("🆕 Detectando empresas novas com contratos grandes...")
        
        query = """
        SELECT
            fc.fornecedor,
            fc.cnpj,
            e.razao_social,
            e.data_abertura,
            c.valor,
            c.data_assinatura,
            (TO_DATE(c.data_assinatura, 'DD/MM/YYYY') - e.data_abertura) AS dias_desde_abertura
        FROM fornecedor_cnpj fc
        JOIN empresas e ON e.cnpj = fc.cnpj
        JOIN sp_contratos c ON c.fornecedor = fc.fornecedor
        WHERE fc.status = 'CONFIRMADO'
          AND e.data_abertura IS NOT NULL
          AND c.valor > 500000
          AND (TO_DATE(c.data_assinatura, 'DD/MM/YYYY') - e.data_abertura) < 365
        ORDER BY c.valor DESC
        """
        
        df = pd.read_sql(query, self.conn)
        
        alertas = []
        for _, row in df.iterrows():
            alerta = AlertaEstrutural(
                tipo='EMPRESA_NOVA_VALOR_ALTO',
                severidade='ALTO',
                entidade=row['fornecedor'],
                descricao=f"Empresa aberta há {row['dias_desde_abertura']} dias, "
                         f"contrato de R$ {row['valor']:,.2f}",
                evidencias={
                    'cnpj': row['cnpj'],
                    'data_abertura': row['data_abertura'],
                    'valor_contrato': row['valor'],
                    'dias_desde_abertura': row['dias_desde_abertura']
                },
                timestamp=datetime.now()
            )
            alertas.append(alerta)
            self._adicionar_alerta(alerta)
        
        print(f"🔴 {len(alertas)} empresas novas com contratos grandes")
        return alertas
    
    def _adicionar_alerta(self, alerta: AlertaEstrutural):
        """Adiciona alerta à lista e salva no banco"""
        self.alertas.append(alerta)
        
        # Salvar no PostgreSQL para auditoria
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO alertas_estruturais 
            (tipo, severidade, entidade, descricao, evidencias, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            alerta.tipo,
            alerta.severidade,
            alerta.entidade,
            alerta.descricao,
            str(alerta.evidencias),
            alerta.timestamp
        ))
        self.conn.commit()
    
    def gerar_relatorio(self) -> str:
        """Gera relatório de alertas estruturais"""
        
        if not self.alertas:
            return "✅ Nenhum alerta estrutural gerado"
        
        relatorio = []
        relatorio.append("=" * 80)
        relatorio.append("RELATÓRIO DE ALERTAS ESTRUTURAIS")
        relatorio.append("=" * 80)
        relatorio.append("")
        
        # Agrupar por severidade
        por_severidade = {}
        for a in self.alertas:
            por_severidade.setdefault(a.severidade, []).append(a)
        
        for sev in ['CRITICO', 'ALTO', 'MEDIO', 'BAIXO']:
            if sev in por_severidade:
                relatorio.append(f"\n🔴 {sev} ({len(por_severidade[sev])} alertas)")
                relatorio.append("-" * 80)
                for alerta in por_severidade[sev][:5]:  # Top 5
                    relatorio.append(f"\n  [{alerta.tipo}]")
                    relatorio.append(f"  Entidade: {alerta.entidade}")
                    relatorio.append(f"  {alerta.descricao}")
                    relatorio.append(f"  Evidências: {alerta.evidencias}")
        
        relatorio.append("\n" + "=" * 80)
        
        return "\n".join(relatorio)
    
    def executar_todos(self) -> List[AlertaEstrutural]:
        """Pipeline completo de alertas estruturais"""
        
        print("\n" + "=" * 80)
        print("GERADOR DE ALERTAS ESTRUTURAIS")
        print("=" * 80)
        
        # 1. Validar matching
        self.validar_matching()
        
        # 2. Detectar laranjas
        self.detectar_laranjas()
        
        # 3. Detectar grupos econômicos
        self.detectar_grupos_economicos_ocultos()
        
        # 4. Detectar empresas novas
        self.detectar_empresas_novas_valor_alto()
        
        print("\n" + self.gerar_relatorio())
        
        return self.alertas


def criar_tabela_alertas():
    """Cria tabela de alertas no PostgreSQL"""
    sql = """
    CREATE TABLE IF NOT EXISTS alertas_estruturais (
        id SERIAL PRIMARY KEY,
        tipo TEXT NOT NULL,
        severidade TEXT NOT NULL,
        entidade TEXT NOT NULL,
        descricao TEXT,
        evidencias TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX idx_alertas_tipo ON alertas_estruturais(tipo);
    CREATE INDEX idx_alertas_sev ON alertas_estruturais(severidade);
    CREATE INDEX idx_alertas_data ON alertas_estruturais(created_at);
    """
    
    import psycopg2
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    print("✅ Tabela alertas_estruturais criada")


if __name__ == '__main__':
    # Criar tabela
    criar_tabela_alertas()
    
    # Executar
    gerador = GeradorAlertasEstruturais()
    alertas = gerador.executar_todos()
    
    print(f"\n✅ {len(alertas)} alertas gerados e salvos")
