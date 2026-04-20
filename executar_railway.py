#!/usr/bin/env python3
"""
Executa schema no Railway PostgreSQL
"""

import psycopg2
import os

# Usar DATABASE_URL do Railway
DB_URL = "postgresql://postgres:xxaXaEfxd1dDb2dDgF2BGe3fF4dD36E@autorack.proxy.rlwy.net:46940/railway"

def executar():
    print("Conectando ao Railway PostgreSQL...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Ler SQL
    with open('sql/schema_arestas_universal.sql', 'r') as f:
        sql = f.read()
    
    print("Executando schema...")
    cur.execute(sql)
    
    # Verificar
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    print("\n✅ Tabelas criadas:")
    for tabela in cur.fetchall():
        print(f"  - {tabela[0]}")
    
    conn.close()
    print("\n✅ Schema universal criado com sucesso!")

if __name__ == '__main__':
    executar()
