#!/bin/bash
# v3.7 - Causal Shift Model

cat > v37_causal.py << 'ENDOFFILE'
import os
import psycopg2
import math
from collections import defaultdict

print("=" * 90)
print("v3.7 - CAUSAL SHIFT MODEL")
print("Explicando POR QUE o comportamento mudou")
print("=" * 90)

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# 1. Dados temporais ricos
print("\n[1/4] Carregando dados...")

cur.execute("""
    SELECT fornecedor,
           orgao,
           SUBSTRING(data_assinatura FROM 4 FOR 2) as mes,
           COUNT(*)
    FROM sp_contratos
    WHERE data_assinatura IS NOT NULL
    GROUP BY fornecedor, orgao, SUBSTRING(data_assinatura FROM 4 FOR 2)
""")

data = cur.fetchall()

# Estruturas
forn_org = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
forn_total = defaultdict(int)
org_total = defaultdict(int)

for f, o, m, c in data:
    forn_org[f][o][m] += c
    forn_total[f] += c
    org_total[o] += c

print(f"Fornecedores: {len(forn_org)}, Orgaos: {len(org_total)}")

# 2. Detectar baseline global por orgao
print("\n[2/4] Baselines...")

org_share = {}
total_global = sum(org_total.values())
for o, total in org_total.items():
    org_share[o] = total / total_global if total_global > 0 else 0

print(f"Baseline global calculado")

# 3. Causal decomposition
print("\n[3/4] Analise Causal...")

casos = []

for f, orgs in forn_org.items():
    total_f = forn_total[f]
    if total_f < 10:
        continue

    # distribuicao por orgao
    dist_org = {o: sum(m.values()) for o, m in orgs.items()}
    sum_org = sum(dist_org.values())
    if sum_org == 0:
        continue

    # 1. Entropy (concentracao)
    entropy = 0
    for v in dist_org.values():
        p = v / sum_org
        entropy -= p * math.log(p + 1e-9)
    
    max_entropy = math.log(len(dist_org) + 1)
    concentration = 1 - (entropy / max_entropy if max_entropy > 0 else 0)

    # 2. Shift de orgao (diferenca vs baseline global)
    shift_org = 0
    for o, v in dist_org.items():
        p_f = v / sum_org
        p_g = org_share.get(o, 1e-6)
        shift_org += abs(p_f - p_g)
    shift_org = min(1.0, shift_org)

    # 3. Shock temporal (variacao mes a mes)
    monthly = defaultdict(int)
    for o in orgs:
        for m, v in orgs[o].items():
            monthly[m] += v

    vals = list(monthly.values())
    if len(vals) >= 2:
        mean = sum(vals) / len(vals)
        var = sum((x - mean) ** 2 for x in vals) / len(vals)
        cv = (var ** 0.5) / (mean + 1e-6)
    else:
        cv = 0
    shock = min(1.0, cv)

    # 4. Dependencia (concentracao em 1 orgao)
    max_org = max(dist_org.values())
    dependency = max_org / sum_org

    # Score causal final
    risk = (0.4 * shift_org + 0.3 * shock + 0.3 * dependency)

    if risk > 0.5:
        cases = []
        if shift_org > 0.5:
            cases.append(("SHIFT_ORGAO", shift_org))
        if shock > 0.5:
            cases.append(("SHOCK_TEMPORAL", shock))
        if dependency > 0.5:
            cases.append(("DEPENDENCIA", dependency))
        
        casos.append({
            "forn": f,
            "risk": risk,
            "shift": shift_org,
            "shock": shock,
            "dep": dependency,
            "causas": sorted(cases, key=lambda x: x[1], reverse=True)
        })

print(f"Casos detectados: {len(casos)}")

# 4. Ranking Causal
print("\n" + "=" * 90)
print("RANKING CAUSAL v3.7")
print("=" * 90)

casos.sort(key=lambda x: x["risk"], reverse=True)

for i, c in enumerate(casos[:20], 1):
    causas_str = ", ".join([f"{k}:{v:.2f}" for k, v in c["causas"]])
    print(f"{i:2d}. {c['forn'][:35]:<35} Risk={c['risk']:.3f} Shift={c['shift']:.2f} Shock={c['shock']:.2f} Dep={c['dep']:.2f} [{causas_str}]")

print("\n" + "=" * 90)

# Estatisticas de causas
shift_count = len([c for c in casos if c["shift"] > 0.5])
shock_count = len([c for c in casos if c["shock"] > 0.5])
dep_count = len([c for c in casos if c["dep"] > 0.5])

print(f"\nPor tipo de causa:")
print(f"  SHIFT_ORGAO: {shift_count}")
print(f"  SHOCK_TEMPORAL: {shock_count}")
print(f"  DEPENDENCIA: {dep_count}")
print(f"\nTotal casos causais: {len(casos)}")

conn.close()
print("=" * 90)
print("✓ v3.7 Causal Shift Model concluido!")
ENDOFFILE

python v37_causal.py
