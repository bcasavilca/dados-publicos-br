#!/bin/bash
# Motor v2.2 Hibrido - Estatico + Temporal

cat > motor_v22.py << 'EOF'
import os
import psycopg2
import math
from datetime import datetime

print("=" * 80)
print("MOTOR DE ANALISE v2.2 - HIBRIDO")
print("Estatico (98%) + Temporal (2%) com preservacao de sinais raros")
print("=" * 80)

# Baseline SP 2024
BASELINE = {
    'p50': 72864.00, 'p90': 3976428.50, 'p95': 12619737.04, 'p99': 78143970.65,
    'conc_top3': 0.0161
}

def fator_baseline(valor):
    if valor <= 0: return 0.0
    valor = max(valor, 1.0)
    log_v = math.log(valor)
    p50, p90, p95, p99 = BASELINE['p50'], BASELINE['p90'], BASELINE['p95'], BASELINE['p99']
    
    if valor <= p50: return 0.05 + 0.05 * log_v / math.log(p50)
    elif valor <= p90: return 0.1 + 0.4 * (log_v - math.log(p50)) / (math.log(p90) - math.log(p50))
    elif valor <= p95: return 0.5 + 0.2 * (log_v - math.log(p90)) / (math.log(p95) - math.log(p90))
    elif valor <= p99: return 0.7 + 0.2 * (log_v - math.log(p95)) / (math.log(p99) - math.log(p95))
    else: return min(1.0, 0.9 + 0.1 * (log_v - math.log(p99)) / math.log(p99))

def confianca(qtd): return 1 - math.exp(-qtd / 20)

def score_concentracao(qtd, total):
    prop = qtd / total
    limiar = 0.10
    if prop < limiar: return 0.0
    return min(1.0, (prop - limiar) / 0.40)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# ============================================================
# 1. Analise ESTATICA (98% dos dados - estrutura)
# ============================================================
print("\n" + "=" * 80)
print("CAMADA 1: ANALISE ESTATICA (estrutura do sistema)")
print("=" * 80)

cur.execute("SELECT COUNT(*) FROM sp_contratos")
total = cur.fetchone()[0]

cur.execute("""
    SELECT fornecedor, COUNT(*), SUM(valor), AVG(valor)
    FROM sp_contratos
    GROUP BY fornecedor
    ORDER BY COUNT(*) DESC
    LIMIT 5
""")

print(f"\nTotal contratos: {total:,}")
print(f"\n{'Fornecedor':<30} {'Qtd':>6} {'Score_E':>8} {'Conf':>6} {'Fator':>6}")
print("-" * 70)

analises_estaticas = []
for fornecedor, qtd, total_valor, media in cur.fetchall():
    score_c = score_concentracao(qtd, total)
    conf = confianca(qtd)
    fator = fator_baseline(media)
    
    # Score estatico v2.1
    score_estatico = score_c * conf * (0.5 + 0.5 * fator)
    
    analises_estaticas.append({
        'fornecedor': fornecedor,
        'score_estatico': score_estatico,
        'qtd': qtd
    })
    
    print(f"{fornecedor[:28]:<30} {qtd:>6} {score_estatico:>8.3f} {conf:>6.3f} {fator:>6.3f}")

# ============================================================
# 2. Analise TEMPORAL (2% dos dados - eventos raros)
# ============================================================
print("\n" + "=" * 80)
print("CAMADA 2: ANALISE TEMPORAL (eventos raros)")
print("=" * 80)

cur.execute("SELECT COUNT(*) FROM sp_contratos WHERE data_assinatura IS NOT NULL")
com_data = cur.fetchone()[0]
print(f"\nRegistros com data: {com_data:,} ({com_data/total*100:.1f}%)")

if com_data > 0:
    # Analise temporal por mes
    cur.execute("""
        SELECT SUBSTRING(data_assinatura FROM 4 FOR 2) as mes,
               COUNT(*) as contratos,
               SUM(valor) as total
        FROM sp_contratos
        WHERE data_assinatura IS NOT NULL
        GROUP BY SUBSTRING(data_assinatura FROM 4 FOR 2)
        ORDER BY mes
    """)
    
    meses = cur.fetchall()
    
    print(f"\n{'Mes':<6} {'Contratos':>10} {'Valor (M)':>12} {'Variacao':>12}")
    print("-" * 50)
    
    alertas_temporais = []
    for i, (mes, contratos, valor) in enumerate(meses):
        var_str = "-"
        
        # Detectar spike vs mes anterior
        if i > 0:
            prev_contratos = meses[i-1][1]
            if contratos > prev_contratos * 1.5:
                var_str = f"SPIKE +{(contratos/prev_contratos-1)*100:.0f}%"
                alertas_temporais.append({
                    'mes': mes,
                    'tipo': 'spike_contratos',
                    'severidade': (contratos/prev_contratos-1)
                })
        
        print(f"{mes:<6} {contratos:>10,} R${valor/1e6:>10.1f}M {var_str:<12}")
    
    # Score temporal (maximo dos alertas)
    score_temporal = min(1.0, len(alertas_temporais) * 0.5) if alertas_temporais else 0.0
    
    print(f"\nAlertas temporais: {len(alertas_temporais)}")
    for alt in alertas_temporais:
        print(f"  - {alt['mes']}: {alt['tipo']}")
else:
    score_temporal = 0.0
    print("Sem dados temporais suficientes")

# ============================================================
# 3. FUSAO INTELIGENTE (preservacao de sinais raros)
# ============================================================
print("\n" + "=" * 80)
print("CAMADA 3: FUSAO INTELIGENTE")
print("=" * 80)

print("\nFormula: score_final = max(score_estatico, score_temporal)")
print("Racional: eventos temporais raros sao mais importantes que estrutura")

print(f"\n{'Fornecedor':<30} {'Est':>8} {'Temp':>8} {'FINAL':>8} {'Nivel':<12}")
print("-" * 70)

for analise in analises_estaticas[:5]:
    score_est = analise['score_estatico']
    score_temp = score_temporal if alertas_temporais else 0.0
    
    # FUSAO: maximo preserva sinais raros
    score_final = max(score_est, score_temp)
    
    nivel = "ALTO" if score_final > 0.70 else "MEDIO" if score_final > 0.35 else "BAIXO"
    
    print(f"{analise['fornecedor'][:28]:<30} {score_est:>8.3f} {score_temp:>8.3f} {score_final:>8.3f} {nivel:<12}")
    
    # Destaque para eventos temporais
    if score_temp > score_est:
        print(f"  {'':<30} ⚡ Evento temporal predominante!")

conn.close()

print("\n" + "=" * 80)
print("✓ Motor v2.2 Hibrido executado!")
print("=" * 80)
print("\nNota: Score temporal aparece quando ha eventos raros detectados")
print("      Score estatico representa a estrutura normal do sistema")
EOF

python motor_v22.py
