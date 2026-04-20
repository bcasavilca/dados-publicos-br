#!/usr/bin/env python3
"""
Cria schema universal via Python (sem psql)
"""

import psycopg2
import os

def criar_schema():
    db_url = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    print("📦 Criando schema universal...")
    
    # Ler e executar SQL
    with open('sql/schema_arestas_universal.sql', 'r') as f:
        sql = f.read()
    
    cur.execute(sql)
    conn.commit()
    
    print("✅ Schema criado com sucesso!")
    print("\nTabelas criadas:")
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    for tabela in cur.fetchall():
        print(f"  - {tabela[0]}")
    
    conn.close()

if __name__ == '__main__':
    criar_schema()
