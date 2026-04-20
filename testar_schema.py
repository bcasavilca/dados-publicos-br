#!/usr/bin/env python3
"""
TESTE DO SCHEMA UNIVERSAL DE ARESTAS
"""

import psycopg2
import pandas as pd
import os

class TesteSchemaArestas:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.conn = psycopg2.connect(self.db_url)
        
    def testar_conexao(self):
        """Testa conexao basica"""
        print("✅ Conexao OK")
        cur = self.conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()
        print(f"PostgreSQL: {version[0][:50]}...")
        
    def verificar_tabelas(self):
        """Verifica se tabelas existem"""
        print("\n📋 Verificando tabelas...")
        
        cur = self.conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name = 'graph_edges'
        """)
        
        if cur.fetchone():
            print("✅ Tabela graph_edges existe")
            
            # Contar registros
            cur.execute("SELECT COUNT(*) FROM graph_edges")
            total = cur.fetchone()[0]
            print(f"   Total de arestas: {total}")
            
            # Tipos
            cur.execute("SELECT edge_type, COUNT(*) FROM graph_edges GROUP BY edge_type")
            print("   Por tipo:")
            for tipo, qtd in cur.fetchall():
                print(f"      {tipo}: {qtd}")
        else:
            print("❌ Tabela graph_edges NAO existe")
            print("   Execute: psql -f sql/schema_arestas_universal.sql")
    
    def testar_view_centralidade(self):
        """Testa view de centralidade"""
        print("\n🎯 Testando vw_centrality_dynamic...")
        
        try:
            df = pd.read_sql("""
                SELECT node, node_type, out_degree, pagerank_approx
                FROM vw_centrality_dynamic
                ORDER BY pagerank_approx DESC NULLS LAST
                LIMIT 5
            """, self.conn)
            
            if len(df) > 0:
                print(f"✅ View funciona ({len(df)} registros)")
                print("   Top central:")
                for _, row in df.iterrows():
                    print(f"      {row['node'][:30]}... | pagerank={row['pagerank_approx']:.4f}")
            else:
                print("⚠️  View vazia (sem dados)")
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    def testar_view_exclusao(self):
        """Testa view de exclusao"""
        print("\n🚫 Testando vw_exclusao_estrutural...")
        
        try:
            df = pd.read_sql("SELECT * FROM vw_exclusao_estrutural LIMIT 5", self.conn)
            print(f"✅ View funciona ({len(df)} registros)")
        except Exception as e:
            print(f"❌ Erro: {e}")


def main():
    print("=" * 60)
    print("TESTE RAPIDO DO SCHEMA")
    print("=" * 60)
    
    teste = TesteSchemaArestas()
    teste.testar_conexao()
    teste.verificar_tabelas()
    teste.testar_view_centralidade()
    teste.testar_view_exclusao()
    
    print("\n" + "=" * 60)
    print("Execute no PostgreSQL para criar:")
    print("  psql -f sql/schema_arestas_universal.sql")
    print("=" * 60)

if __name__ == '__main__':
    main()
