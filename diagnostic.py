#!/usr/bin/env python3
"""FASE 1: Data Diagnostic for Railway PostgreSQL"""

import psycopg2
import os
import sys

def run_diagnostic():
    print("=" * 60)
    print("🔍 FASE 1: DATA DIAGNOSTIC")
    print("=" * 60)
    print()
    
    # Get DATABASE_URL from environment
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print("❌ ERROR: DATABASE_URL not found in environment!")
        print("Available vars:", [k for k in os.environ.keys() if 'DB' in k or 'DATABASE' in k])
        sys.exit(1)
    
    print("✅ DATABASE_URL found")
    print(f"   URL (masked): {db_url[:30]}...")
    print()
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'sp_contratos'
            )
        """)
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            print("❌ ERROR: Table 'sp_contratos' does not exist!")
            print("\nAvailable tables:")
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cur.fetchall()
            for t in tables:
                print(f"   - {t[0]}")
            conn.close()
            sys.exit(1)
        
        print("✅ Table 'sp_contratos' exists")
        print()
        
        # 1. Total contracts
        cur.execute('SELECT COUNT(*) FROM sp_contratos')
        total = cur.fetchone()[0]
        print(f"📊 TOTAL CONTRACTS: {total:,}")
        
        # 2. Unique organs
        cur.execute('SELECT COUNT(DISTINCT orgao) FROM sp_contratos')
        num_orgs = cur.fetchone()[0]
        print(f"🏛️  UNIQUE ORGANS: {num_orgs}")
        
        # 3. Unique suppliers
        cur.execute('SELECT COUNT(DISTINCT fornecedor) FROM sp_contratos')
        num_suppliers = cur.fetchone()[0]
        print(f"🏢 UNIQUE SUPPLIERS: {num_suppliers:,}")
        
        # 4. Sample organs
        cur.execute("""
            SELECT orgao, COUNT(*) as contracts 
            FROM sp_contratos 
            GROUP BY orgao 
            ORDER BY contracts DESC 
            LIMIT 10
        """)
        top_orgs = cur.fetchall()
        
        print()
        print("📈 TOP 10 ORGANS:")
        print("-" * 60)
        for org, count in top_orgs:
            print(f"   {count:>6,} | {org[:50]}")
        
        conn.close()
        
        # ANALYSIS
        print()
        print("=" * 60)
        print("🧠 ANALYSIS:")
        print("=" * 60)
        
        if num_orgs <= 2:
            print("🚨 FLAG: DATA COLLAPSE CONFIRMED")
            print(f"   Only {num_orgs} org detected - insufficient for structural analysis")
            print("   Required: minimum 5, ideal 20+")
            return "COLLAPSE"
        elif num_orgs < 5:
            print("⚠️  WARNING: LOW ORGAN DIVERSITY")
            print(f"   Only {num_orgs} orgs - limited analysis possible")
            return "LOW"
        else:
            print(f"✅ DATA VALID FOR ANALYSIS")
            print(f"   {num_orgs} orgs detected - system ready")
            return "VALID"
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    result = run_diagnostic()
    
    # Write result for next phase
    with open('/tmp/diagnostic_result.txt', 'w') as f:
        f.write(result)
    
    print()
    print(f"✅ Result written to /tmp/diagnostic_result.txt: {result}")
