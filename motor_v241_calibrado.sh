#!/bin/bash
# Motor v2.4.1 - CALIBRADO (Com ajustes conceituais)

cat > motor_v241.py << 'PYEND'
import os
import psycopg2
import math

print("=" * 80)
print("MOTOR v2.4.1 - CALIBRADO")
print("Ajustes: est continuo, rede dinamico, filtro edges >= 10")
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

def score_conc_continuo(prop, media):
    """CORRECAO: Score continuo, nunca negativo"""
    if media == 0: return 0.0
    ratio = prop / media
    # Normaliza: abaixo da media ainda pontua, acima cresce
    return max(0.0, min(1.0, (ratio - 0.5) / 2))

# 1. Calcular baselines e totais
print("\n[1/5] Calculando baselines...")
cur.execute("SELECT COUNT(*) FROM sp_contratos")
total = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT fornecedor) FROM sp_contratos")
total_fornecedores = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM sp_contratos GROUP BY fornecedor ORDER BY COUNT(*) DESC LIMIT 1")
top1 = cur.fetchone()[0]
prop_media = top1 / total

print(f"Total contratos: {total:,}")
print(f"Fornecedores unicos: {total_fornecedores:,}")
print(f"Media de concentracao: {prop_media:.4f}")

# 2. Pre-calcular metricas de rede (COM NORMALIZACAO DINAMICA)
print("\n[2/5] Calculando metricas de rede (normalizacao dinamica)...")

# Primeiro passo: encontrar maximos reais
cur.execute("""
    SELECT node_a, COUNT(*) as c, SUM(weight) as s, MAX(weight) as m
    FROM graph_edges 
    WHERE relation_type = 'co_occurrence_temporal' AND weight >= 10
    GROUP BY node_a
""")

dados_rede = cur.fetchall()

max_c = 1
max_peso_medio = 1.0

for node, c, s, m in dados_rede:
    max_c = max(max_c, c)
    if c > 0:
        peso_medio = s / c
        max_peso_medio = max(max_peso_medio, peso_medio)

print(f"Max conexoes encontradas: {max_c}")
print(f"Max peso medio: {max_peso_medio:.2f}")
print(f"Fornecedores na rede: {len(dados_rede)}")

# Segundo passo: calcular scores normalizados
metricas_rede = {}
for node, c, s, m in dados_rede:
    # CORRECAO: Normalizacao dinamica com maximos reais
    centralidade = c / max_c
    peso_medio = s / c if c > 0 else 0
    peso_norm = peso_medio / max_peso_medio if max_peso_medio > 0 else 0
    insepar = m / s if s > 0 else 0
    
    # Score base
    score_rede = 0.5 * centralidade + 0.3 * insepar + 0.2 * peso_norm
    
    # CORRECAO: Penalizacao por diversidade (hub global = menos suspeito)
    diversidade = c / total_fornecedores
    score_rede *= (1 - 0.5 * diversidade)
    
    metricas_rede[node] = min(1.0, score_rede)

# 3. Analisar fornecedores completos
print("\n[3/5] Calculando scores completos...")

cur.execute("""
    SELECT fornecedor, COUNT(*) as qtd, SUM(valor) as total_v, AVG(valor) as media
    FROM sp_contratos
    GROUP BY fornecedor
    HAVING COUNT(*) >= 10
    ORDER BY COUNT(*) DESC
    LIMIT 20
""")

resultados = []
for forn, qtd, total_v, media in cur.fetchall():
    prop = qtd / total
    
    # Score estatico CORRIGIDO (continuo, nunca negativo)
    score_est = score_conc_continuo(prop, prop_media) * confianca(qtd) * (0.5 + 0.5 * fator_baseline(media))
    
    # Score temporal (placeholder)
    score_temp = 0.0
    
    # Score rede
    score_rede = metricas_rede.get(forn, 0.0)
    
    # Score final CORRIGIDO (peso maior em rede)
    score_final = score_est * 0.2 + score_temp * 0.2 + score_rede * 0.6
    
    resultados.append({
        'forn': forn,
        'qtd': qtd,
        'prop': prop,
        'est': score_est,
        'temp': score_temp,
        'rede': score_rede,
        'final': score_final
    })

# 4. Exibir resultados
print("\n" + "=" * 80)
print("RESULTADOS v2.4.1 - CALIBRADO")
print("=" * 80)

print(f"\n{'Fornecedor':<35} {'Qtd':>6} {'%':>6} {'Est':>7} {'Rede':>7} {'FINAL':>7} {'Nivel':<10}")
print("-" * 90)

for r in sorted(resultados, key=lambda x: x['final'], reverse=True):
    if r['final'] > 0.70:
        nivel = "🔴 ALTO"
    elif r['final'] > 0.40:
        nivel = "🟡 MEDIO"
    elif r['final'] > 0.15:
        nivel = "⚡ BAIXO+"
    else:
        nivel = "🟢 NORMAL"
    
    print(f"{r['forn'][:33]:<35} {r['qtd']:>6} {r['prop']*100:>5.1f}% {r['est']:>7.3f} {r['rede']:>7.3f} {r['final']:>7.3f} {nivel:<10}")

# 5. Analise de distribuicao
print("\n" + "=" * 80)
print("ANALISE DE DISTRIBUICAO")
print("=" * 80)

altos = len([r for r in resultados if r['final'] > 0.70])
medios = len([r for r in resultados if 0.40 < r['final'] <= 0.70])
baixos = len([r for r in resultados if r['final'] <= 0.40])

print(f"\n🔴 Alto risco: {altos} ({altos/len(resultados)*100:.1f}%)")
print(f"🟡 Medio risco: {medios} ({medios/len(resultados)*100:.1f}%)")
print(f"🟢 Baixo/Normal: {baixos} ({baixos/len(resultados)*100:.1f}%)")

if altos == 0:
    print("\n⚠️  ALERTA: Nenhum fornecedor em ALTO risco")
    print("    Possiveis causas:")
    print("    - Thresholds ainda muito conservadores")
    print("    - Grafo denso demais (aumentar filtro de edges)")
    print("    - Dataset SP pode ser realmente normal")

# Top suspeitos para investigacao
print("\n" + "=" * 80)
print("TOP SUSPEITOS (se houver)")
print("=" * 80)

suspeitos = [r for r in resultados if r['final'] > 0.50]
if suspeitos:
    print(f"\n{len(suspeitos)} fornecedores com score > 0.50:")
    for r in suspeitos:
        print(f"  🔍 {r['forn'][:40]} (score: {r['final']:.3f})")
        print(f"      └─ Est: {r['est']:.3f} | Rede: {r['rede']:.3f}")
else:
    print("\nNenhum fornecedor acima de 0.50")
    print("Sugestao: Revisar filtros ou aumentar peso da rede")

conn.close()

print("\n" + "=" * 80)
print("✓ Motor v2.4.1 concluido!")
print("=" * 80)
print("\nFormula final: 0.2*Est + 0.2*Temp + 0.6*Rede")
print("Rede = 0.5*Centr + 0.3*Insepar + 0.2*Peso (com penalizacao diversidade)")
PYEND

python motor_v241.py
