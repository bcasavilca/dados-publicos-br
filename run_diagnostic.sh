#!/bin/bash
# Execute diagnostic on Railway

echo "🔍 Executing FASE 1 Diagnostic..."
echo ""

python3 -c "
import psycopg2
import os

print('=' * 60)
print('🔍 FASE 1: DATA DIAGNOSTIC (Inline)')
print('=' * 60)
print()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    # Check table
    cur.execute(\"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'sp_contratos')\")
    exists = cur.fetchone()[0]
    
    if not exists:
        print('❌ Table sp_contratos does not exist!')
        exit(1)
    
    # Metrics
    cur.execute('SELECT COUNT(*) FROM sp_contratos')
    total = cur.fetchone()[0]
    print(f'📊 TOTAL CONTRACTS: {total:,}')
    
    cur.execute('SELECT COUNT(DISTINCT orgao) FROM sp_contratos')
    num_orgs = cur.fetchone()[0]
    print(f'🏛️  UNIQUE ORGANS: {num_orgs}')
    
    cur.execute('SELECT COUNT(DISTINCT fornecedor) FROM sp_contratos')
    num_supp = cur.fetchone()[0]
    print(f'🏢 UNIQUE SUPPLIERS: {num_supp:,}')
    
    # Sample
    cur.execute(\"SELECT orgao, COUNT(*) FROM sp_contratos GROUP BY orgao ORDER BY COUNT(*) DESC LIMIT 5\")
    print()
    print('📈 TOP 5 ORGANS:')
    for org, cnt in cur.fetchall():
        print(f'   {cnt:>6,} | {org[:40]}')
    
    conn.close()
    
    # Analysis
    print()
    print('=' * 60)
    if num_orgs <= 2:
        print('🚨 DATA COLLAPSE: Only', num_orgs, 'org(s)')
    elif num_orgs < 5:
        print('⚠️  LOW DIVERSITY:', num_orgs, 'orgs')
    else:
        print('✅ VALID:', num_orgs, 'orgs')
        
except Exception as e:
    print(f'❌ ERROR: {e}')
    exit(1)
"
