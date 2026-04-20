#!/bin/bash
# v3.7.1 - CALIBRACAO (correcao de saturacao e normalizacao)

cat > v371_calibracao.py << 'ENDOFFILE'
import os
import psycopg2
import math
from collections import defaultdict

print("=" * 90)
print("v3.7.1 - CALIBRACAO (Anti-saturacao + Percentil + Shift corrigido)")
print("=" * 90)

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# 1. CARREGAR DADOS
print("\n[1/4] Carregando dados...")

cur.execute("""
    SELECT fornecedor,
           orgao,
           SUBSTRING(data_assinatura FROM 4 FOR 2) as mes,
           COUNT(*) as qtd
    FROM sp_contratos
    WHERE data_assinatura IS NOT NULL
    GROUP BY fornecedor, orgao, SUBSTRING(data_assinatura FROM 4 FOR 2)
""")

data = cur.fetchall()

# Estruturas
forn_org = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
forn_total = defaultdict(int)
org_total = defaultdict(int)
org_monthly = defaultdict(lambda: defaultdict(int))

for f, o, m, c in data:
    forn_org[f][o][m] += c
    forn_total[f] += c
    org_total[o] += c
    org_monthly[o][m] += c

print(f"Fornecedores: {len(forn_org)}, Orgaos: {len(org_total)}")

# 2. BASELINE GLOBAL CORRIGIDO (com smoothing)
print("\n[2/4] Baseline global (smoothing)...")

total_global = sum(org_total.values())
org_share = {}

# Aplicar smoothing Laplace para evitar zeros
alpha = 0.01  # smoothing factor
num_orgs = len(org_total)

for o, total in org_total.items():
    # Laplace smoothing: (count + alpha) / (total + alpha*num_classes)
    org_share[o] = (total + alpha) / (total_global + alpha * num_orgs)

# 3. COLETAR METRICAS BRUTAS
print("\n[3/4] Coletando metricas brutas...")

metricas = []

for f, orgs in forn_org.items():
    total_f = forn_total[f]
    if total_f < 5:  # filtro de volume minimo
        continue

    # Distribuicao por orgao
    dist_org = {o: sum(m.values()) for o, m in orgs.items()}
    sum_org = sum(dist_org.values())
    if sum_org == 0:
        continue

    # 1. SHIFT (divergencia KL-like com smoothing)
    shift = 0
    for o, v in dist_org.items():
        p_f = (v + alpha) / (sum_org + alpha * len(dist_org))
        p_g = org_share.get(o, alpha / (total_global + alpha * num_orgs))
        # KL-like divergence (simetrico)
        if p_f > 0 and p_g > 0:
            shift += p_f * math.log(p_f / p_g)
    
    # Normalizar shift para [0, 1]
    max_shift = math.log(len(dist_org) + 1)
    shift_norm = min(1.0, shift / max_shift) if max_shift > 0 else 0

    # 2. SHOCK (CV anti-saturado)
    monthly = defaultdict(int)
    for o in orgs:
        for m, v in orgs[o].items():
            monthly[m] += v
    
    vals = list(monthly.values())
    if len(vals) >= 2:
        mean = sum(vals) / len(vals)
        var = sum((x - mean) ** 2 for x in vals) / len(vals)
        cv = (var ** 0.5) / (mean + 1e-6)
        # Anti-saturacao: cv / (cv + k)
        shock = cv / (cv + 0.5)
    else:
        shock = 0

    # 3. DEPENDENCIA (concentracao com entropia)
    entropy = 0
    for v in dist_org.values():
        p = v / sum_org
        if p > 0:
            entropy -= p * math.log(p)
    max_ent = math.log(len(dist_org))
    # Concentracao = 1 - normalizacao_entropia
    dep = 1 - (entropy / max_ent if max_ent > 0 else 0)

    metricas.append({
        'forn': f,
        'total': total_f,
        'shift': shift_norm,
        'shock': shock,
        'dep': dep,
        'num_orgs': len(dist_org)
    })

print(f"Metricas coletadas: {len(metricas)}")

# 4. CALCULAR PERCENTIS (normalizacao robusta)
print("\n[4/4] Calculando percentis...")

if len(metricas) < 10:
    print("ERRO: Poucos dados para percentil")
    conn.close()
    exit()

# Extrair valores para percentil
shifts = [m['shift'] for m in metricas]
shocks = [m['shock'] for m in metricas]
deps = [m['dep'] for m in metricas]

shifts.sort()
shocks.sort()
deps.sort()

def percentile(val, sorted_list):
    """Calcular percentil de um valor"""
    if not sorted_list:
        return 0
    idx = sum(1 for x in sorted_list if x <= val)
    return idx / len(sorted_list)

# Calcular scores finais com percentis
casos = []

for m in metricas:
    # Percentis
    p_shift = percentile(m['shift'], shifts)
    p_shock = percentile(m['shock'], shocks)
    p_dep = percentile(m['dep'], deps)
    
    # Score causal (media ponderada de percentis)
    risk = 0.4 * p_shift + 0.3 * p_shock + 0.3 * p_dep
    
    # Identificar causas principais
    causas = []
    if p_shift > 0.7:
        causas.append(f"SHIFT:{p_shift:.2f}")
    if p_shock > 0.7:
        causas.append(f"SHOCK:{p_shock:.2f}")
    if p_dep > 0.7:
        causas.append(f"DEP:{p_dep:.2f}")
    
    if risk > 0.6:  # threshold ajustado para percentil
        casos.append({
            'forn': m['forn'],
            'total': m['total'],
            'risk': risk,
            'p_shift': p_shift,
            'p_shock': p_shock,
            'p_dep': p_dep,
            'causas': causas
        })

# 5. RANKING
print("\n" + "=" * 90)
print("RANKING v3.7.1 - CALIBRADO (Percentil)")
print("=" * 90)
print(f"{'#':<4} {'Fornecedor':<35} {'Total':<7} {'Risk':<7} {'Shift%':<8} {'Shock%':<8} {'Dep%':<8} {'Causas'}")
print("-" * 90)

casos.sort(key=lambda x: x['risk'], reverse=True)

for i, c in enumerate(casos[:25], 1):
    nivel = "🔴" if c['risk'] > 0.85 else "🟡" if c['risk'] > 0.75 else "⚡"
    causas_str = ", ".join(c['causas']) if c['causas'] else "-"
    print(f"{i:<4} {c['forn'][:33]:<35} {c['total']:<7} {c['risk']:<7.3f} {c['p_shift']:<8.2f} {c['p_shock']:<8.2f} {c['p_dep']:<8.2f} {causas_str}")

print("\n" + "=" * 90)

# Estatisticas
dist_shift = len([c for c in casos if c['p_shift'] > 0.7])
dist_shock = len([c for c in casos if c['p_shock'] > 0.7])
dist_dep = len([c for c in casos if c['p_dep'] > 0.7])

print(f"\nDistribuicao de causas principais (>70%):")
print(f"  SHIFT: {dist_shift}")
print(f"  SHOCK: {dist_shock}")
print(f"  DEP:   {dist_dep}")

altos = len([c for c in casos if c['risk'] > 0.85])
medios = len([c for c in casos if 0.75 < c['risk'] <= 0.85])
atencao = len([c for c in casos if 0.6 < c['risk'] <= 0.75])

print(f"\n🔴 ALTO (>0.85): {altos}")
print(f"🟡 MEDIO (0.75-0.85): {medios}")
print(f"⚡ ATENCAO (0.60-0.75): {atencao}")
print(f"\nTotal casos: {len(casos)}")

conn.close()
print("=" * 90)
print("✓ v3.7.1 Calibracao concluida!")
print("=" * 90)
ENDOFFILE

python v371_calibracao.py
