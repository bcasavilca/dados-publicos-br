#!/bin/bash
# Motor v2.4 - Integrado: Estatico + Temporal + Rede

cat > motor_v24.py << 'PYEND'
import os
import psycopg2
import math

print("=" * 80)
print("MOTOR v2.4 - INTEGRADO (Estatico + Temporal + Rede)")
print("Pesos: Est=0.3, Temp=0.3, Rede=0.4")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Baseline
BASELINE = {'p50': 72864.00, 'p90': 3976428.50, 'p95': 12619737.04, 'p99': 78143970.65}

def fator_baseline(valor):
    if valor <= 0: return 0.0
    valor = max(valor, 1.0)
    log_v = math.log(valor)
    p50, p90, p95, p99 = BASELINE['p50'], BASELINE['p90'], BASELINE['p95'], BASELINE['p99']
    if valor <= p50: return 0.05 + 0.05 * log_v / math.log(p50)
    elif valor <= p90: return 0.1 + 0.4 * (log_v - math.log(p50)) / (math.log(p90) - math.log(p50))
    elif valor <= p95: return 0.5 + 0.2 * (log_v - math.log(p90)) / (math.log(p95) - math.log(p90))
    elif valor <= p99: return 0.7 + 0.2 * (log_v - math.log(p95)) / (math.log(p99) - math.log(p99))
    else: return min(1.0, 0.9 + 0.1 * (log_v - math.log(p99)) / math.log(p99))

def confianca(qtd): return 1 - math.exp(-qtd / 20)

def score_conc(prop, media_top1):
    if prop <= media_top1: return 0.0
    razao = prop / media_top1
    return min(1.0, (razao - 1) / 10)

# 1. Calcular baselines
print("\n[1/4] Calculando baselines...")
cur.execute("SELECT COUNT(*) FROM sp_contratos")
total = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM sp_contratos GROUP BY fornecedor ORDER BY COUNT(*) DESC LIMIT 1")
top1 = cur.fetchone()[0]
prop_media = top1 / total

# 2. Analise de Rede (pre-calcular)
print("\n[2/4] Pre-calculando metricas de rede...")

# Centralidade e inseparabilidade por fornecedor
cur.execute("""
    SELECT node_a, COUNT(*) as conexoes, SUM(weight) as peso_total, MAX(weight) as max_peso
    FROM graph_edges
    WHERE relation_type = 'co_occurrence_temporal'
    GROUP BY node_a
""")

metricas_rede = {}
for node, conexoes, peso_total, max_peso in cur.fetchall():
    centralidade = conexoes / 100  # Normalizar (assumir max 100 conexoes)
    inseparabilidade = max_peso / peso_total if peso_total > 0 else 0
    peso_medio = peso_total / conexoes if conexoes > 0 else 0
    peso_norm = min(1.0, peso_medio / 50)  # Assumir peso medio 50 como referencia
    
    score_rede = 0.5 * centralidade + 0.3 * inseparabilidade + 0.2 * peso_norm
    metricas_rede[node] = min(1.0, score_rede)

print(f"Metricas calculadas para {len(metricas_rede)} fornecedores")

# 3. Analisar top fornecedores
print("\n[3/4] Calculando scores completos...")

cur.execute("""
    SELECT fornecedor, COUNT(*), SUM(valor), AVG(valor)
    FROM sp_contratos
    GROUP BY fornecedor
    ORDER BY COUNT(*) DESC
    LIMIT 15
""")

resultados = []
for forn, qtd, total_v, media in cur.fetchall():
    # Score estatico
    prop = qtd / total
    score_c = score_conc(prop, prop_media)
    conf = confianca(qtd)
    fator = fator_baseline(media)
    score_est = score_c * conf * (0.5 + 0.5 * fator)
    
    # Score temporal (placeholder - usar spike detection)
    score_temp = 0.0
    
    # Score rede
    score_rede = metricas_rede.get(forn, 0.0)
    
    # Score final integrado
    score_final = score_est * 0.3 + score_temp * 0.3 + score_rede * 0.4
    
    resultados.append({
        'forn': forn,
        'qtd': qtd,
        'est': score_est,
        'temp': score_temp,
        'rede': score_rede,
        'final': score_final
    })

# 4. Exibir resultados
print("\n" + "=" * 80)
print("RESULTADOS - TOP 15 FORNECEDORES")
print("=" * 80)

print(f"\n{'Fornecedor':<35} {'Qtd':>6} {'Est':>7} {'Temp':>7} {'Rede':>7} {'FINAL':>7} {'Alerta':<10}")
print("-" * 90)

for r in sorted(resultados, key=lambda x: x['final'], reverse=True):
    nivel = "🔴 ALTO" if r['final'] > 0.70 else "🟡 MEDIO" if r['final'] > 0.35 else "🟢 BAIXO"
    print(f"{r['forn'][:33]:<35} {r['qtd']:>6} {r['est']:>7.3f} {r['temp']:>7.3f} {r['rede']:>7.3f} {r['final']:>7.3f} {nivel:<10}")

# Analise de clusters
print("\n" + "=" * 80)
print("ANALISE DE CLUSTERS (Rede forte)")
print("=" * 80)

cur.execute("""
    SELECT node_a, node_b, weight
    FROM graph_edges
    WHERE relation_type = 'co_occurrence_temporal'
    ORDER BY weight DESC
    LIMIT 10
""")

print("\nTop pares conectados (possiveis clusters):")
for a, b, w in cur.fetchall():
    score_a = metricas_rede.get(a, 0)
    score_b = metricas_rede.get(b, 0)
    alerta = "🔴" if score_a > 0.5 and score_b > 0.5 else "🟡" if score_a > 0.3 or score_b > 0.3 else "🟢"
    print(f"  {alerta} {a[:30]:<32} + {b[:30]:<32} = {w:>4}")

conn.close()

print("\n" + "=" * 80)
print("✓ Motor v2.4 concluido!")
print("=" * 80)
print("\nFormula: FINAL = 0.3*Est + 0.3*Temp + 0.4*Rede")
print("Rede = 0.5*Centralidade + 0.3*Inseparabilidade + 0.2*Peso")
PYEND

python motor_v24.py
