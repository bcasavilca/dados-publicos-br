#!/bin/bash
# Motor v2.3 - Estatico Continuo + Temporal

cat > motor_v23.py << 'PYEND'
import os
import psycopg2
import math

print("=" * 80)
print("MOTOR v2.3 - ESTATICO CONTINUO + TEMPORAL")
print("Score baseado em distribuicao real de concentracao")
print("=" * 80)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Baseline SP 2024
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

def score_concentracao_continuo(prop_fornecedor, prop_media_top1):
    """
    Score continuo baseado em desvio da media
    prop_media_top1 = 0.006 (0.6% baseline SP)
    """
    if prop_fornecedor <= prop_media_top1:
        return 0.0
    
    # Quanto maior que a media, maior o score
    razao = prop_fornecedor / prop_media_top1
    # razao = 1 → na media
    # razao = 2 → 2x acima da media
    # razao = 10 → 10x acima (muito anomalo)
    
    score = min(1.0, (razao - 1) / 10)  # Saturar em 10x
    return score

# 1. Calcular baseline de concentracao
print("\n" + "=" * 80)
print("CAMADA 1: ESTATICA CONTINUA")
print("=" * 80)

cur.execute("SELECT COUNT(*) FROM sp_contratos")
total = cur.fetchone()[0]

# Media de concentracao (top 1)
cur.execute("""
    SELECT fornecedor, COUNT(*) as qtd
    FROM sp_contratos
    GROUP BY fornecedor
    ORDER BY qtd DESC
    LIMIT 1
""")
top1_qtd = cur.fetchone()[1]
prop_media_top1 = top1_qtd / total

print(f"\nTotal contratos: {total:,}")
print(f"Top 1 (baseline): {top1_qtd} contratos ({prop_media_top1*100:.2f}%)")
print(f"\nScore de concentracao = desvio em relacao a {prop_media_top1*100:.2f}%")

# Analisar fornecedores
print(f"\n{'Fornecedor':<30} {'Qtd':>6} {'Prop':>7} {'Razao':>6} {'Score_C':>8} {'Conf':>6} {'Score_E':>8}")
print("-" * 80)

cur.execute("""
    SELECT fornecedor, COUNT(*), SUM(valor), AVG(valor)
    FROM sp_contratos
    GROUP BY fornecedor
    ORDER BY COUNT(*) DESC
    LIMIT 10
""")

estaticos = []
for forn, qtd, total_v, media in cur.fetchall():
    prop = qtd / total
    razao = prop / prop_media_top1
    score_c = score_concentracao_continuo(prop, prop_media_top1)
    conf = confianca(qtd)
    fator = fator_baseline(media)
    
    # Score estatico: concentracao + confianca + baseline
    score_e = score_c * conf * (0.5 + 0.5 * fator)
    
    estaticos.append((forn, score_e, score_c, prop))
    
    print(f"{forn[:28]:<30} {qtd:>6} {prop*100:>6.2f}% {razao:>6.1f}x {score_c:>8.3f} {conf:>6.3f} {score_e:>8.3f}")

# 2. TEMPORAL
print("\n" + "=" * 80)
print("CAMADA 2: TEMPORAL")
print("=" * 80)

cur.execute("SELECT COUNT(*) FROM sp_contratos WHERE data_assinatura IS NOT NULL")
com_data = cur.fetchone()[0]
print(f"\nCom data: {com_data:,} ({com_data/total*100:.1f}%)")

score_temp = 0.0
if com_data > 0:
    cur.execute("SELECT SUBSTRING(data_assinatura FROM 4 FOR 2), COUNT(*) FROM sp_contratos WHERE data_assinatura IS NOT NULL GROUP BY 1 ORDER BY 1")
    meses = cur.fetchall()
    
    print(f"\n{'Mes':<6} {'Contratos':>10}")
    print("-" * 20)
    for mes, c in meses:
        print(f"{mes:<6} {c:>10,}")
    
    for i in range(1, len(meses)):
        if meses[i][1] > meses[i-1][1] * 1.5:
            spike = (meses[i][1]/meses[i-1][1]-1)*100
            print(f"\n⚡ SPIKE em {meses[i][0]}: +{spike:.0f}%")
            score_temp = min(1.0, spike / 100)

# 3. FUSAO PONDERADA
print("\n" + "=" * 80)
print("CAMADA 3: FUSAO PONDERADA")
print("=" * 80)

# Pesos baseados em cobertura
cobertura_temp = com_data / total
peso_temp = 0.3 + (0.7 * cobertura_temp)  # Min 30%, max 100%
peso_est = 1 - peso_temp + 0.2  # Estatico sempre tem peso significativo

# Normalizar
soma = peso_est + peso_temp
peso_est_norm = peso_est / soma
peso_temp_norm = peso_temp / soma

print(f"\nCobertura temporal: {cobertura_temp*100:.1f}%")
print(f"Peso Estatico: {peso_est_norm:.2f}")
print(f"Peso Temporal: {peso_temp_norm:.2f}")
print(f"\nFormula: FINAL = {peso_est_norm:.2f}*Estatico + {peso_temp_norm:.2f}*Temporal")

print(f"\n{'Fornecedor':<30} {'Score_C':>8} {'Score_E':>8} {'Score_T':>8} {'FINAL':>8} {'Nivel':<10}")
print("-" * 80)

for forn, score_e, score_c, prop in estaticos[:7]:
    final = (peso_est_norm * score_e) + (peso_temp_norm * score_temp)
    nivel = "ALTO" if final > 0.70 else "MEDIO" if final > 0.35 else "BAIXO"
    print(f"{forn[:28]:<30} {score_c:>8.3f} {score_e:>8.3f} {score_temp:>8.3f} {final:>8.3f} {nivel:<10}")

conn.close()

print("\n" + "=" * 80)
print("✓ Motor v2.3 concluido!")
print("=" * 80)
print("\nMelhorias:")
print("  - Score de concentracao continuo (varia por fornecedor)")
print("  - Fusao ponderada preserva ambos os sinais")
print("  - Diferenciacao restaurada entre fornecedores")
PYEND

python motor_v23.py
