#!/bin/bash
# v3.2 simplificado

cat > v32_simples.py << 'EOF'
import os
import psycopg2
import math

print("=" * 80)
print("v3.2 - Detector Simplificado")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# 1. Contextos
print("\n[1/3] Contextos...")
cur.execute("""
    SELECT orgao, SUBSTRING(data_assinatura FROM 4 FOR 2),
           COUNT(DISTINCT fornecedor), COUNT(*)
    FROM sp_contratos WHERE data_assinatura IS NOT NULL
    GROUP BY orgao, SUBSTRING(data_assinatura FROM 4 FOR 2)
""")
contextos = cur.fetchall()
print(f"Total: {len(contextos)}")

# Raridade
raridade = {}
for org, mes, num_forn, num_contr in contextos:
    raridade[f"{org}__{mes}"] = 1.0 / math.log(1 + num_forn) if num_forn > 0 else 0

# 2. Fornecedores por contexto
print("\n[2/3] Analisando dominio...")
cur.execute("""
    SELECT fornecedor, orgao, SUBSTRING(data_assinatura FROM 4 FOR 2), COUNT(*)
    FROM sp_contratos WHERE data_assinatura IS NOT NULL
    GROUP BY fornecedor, orgao, SUBSTRING(data_assinatura FROM 4 FOR 2)
""")

forn_contexto = {}
for forn, org, mes, qtd in cur.fetchall():
    chave = f"{org}__{mes}"
    if forn not in forn_contexto:
        forn_contexto[forn] = {}
    forn_contexto[forn][chave] = qtd

# 3. Detectar dominio anomalo
print("\n[3/3] Detectando anomalias...")
casos = []

for forn, contextos in forn_contexto.items():
    for ctx, qtd in contextos.items():
        rar = raridade.get(ctx, 0)
        # Fornecedor dominante em contexto raro
        if rar > 0.5 and qtd >= 5:
            score = 0.4 + (rar * 0.3) + (min(qtd, 20) / 20 * 0.3)
            casos.append({
                'forn': forn,
                'ctx': ctx,
                'qtd': qtd,
                'rar': rar,
                'score': min(score, 1.0)
            })

casos.sort(key=lambda x: x['score'], reverse=True)

print("\n" + "=" * 80)
print("TOP 20 CASOS")
print("=" * 80)

for i, c in enumerate(casos[:20], 1):
    nivel = "🔴" if c['score'] >= 0.70 else "🟡" if c['score'] >= 0.50 else "⚡"
    print(f"{i:2d}. {c['forn'][:35]:<37} Ctx: {c['ctx'][:20]:<22} Qtd: {c['qtd']:>3} Rar: {c['rar']:.2f} Score: {c['score']:.3f} {nivel}")

altos = len([c for c in casos if c['score'] >= 0.70])
print(f"\n{'='*80}")
print(f"🔴 Alto: {altos} | 🟡 Medio: {len([c for c in casos if 0.50 <= c['score'] < 0.70])} | Total: {len(casos)}")

conn.close()
print("=" * 80)
EOF

python v32_simples.py
