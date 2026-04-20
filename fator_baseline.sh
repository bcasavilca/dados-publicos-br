#!/bin/bash
# Fator Baseline Logarítmico - Versão Robusta

cat > fator_baseline.py << 'EOF'
import os
import psycopg2
import math

# Percentis do SP 2024 (do seu baseline)
P50 = 72864.00
P90 = 3976428.50
P95 = 12619737.04
P99 = 78143970.65

def calcular_fator_baseline(valor):
    """
    Calcula fator de baseline baseado em percentis com escala logarítmica.
    Retorna score 0.0-1.0 contínuo.
    """
    if valor <= 0:
        return 0.0
    
    # Evitar log(0)
    valor = max(valor, 1.0)
    
    log_v = math.log(valor)
    log_p50 = math.log(max(P50, 1.0))
    log_p90 = math.log(max(P90, 1.0))
    log_p95 = math.log(max(P95, 1.0))
    log_p99 = math.log(max(P99, 1.0))
    
    if valor <= P50:
        # Abaixo da mediana: score baixo
        return 0.05 + 0.05 * (log_v - math.log(1.0)) / (log_p50 - math.log(1.0))
    
    elif valor <= P90:
        # P50 → P90: interpolação suave
        return 0.1 + 0.4 * (log_v - log_p50) / (log_p90 - log_p50)
    
    elif valor <= P95:
        # P90 → P95: crescimento moderado
        return 0.5 + 0.2 * (log_v - log_p90) / (log_p95 - log_p90)
    
    elif valor <= P99:
        # P95 → P99: anomalia crescente
        return 0.7 + 0.2 * (log_v - log_p95) / (log_p99 - log_p95)
    
    else:
        # Acima de P99: crescimento desacelerado
        # Evita saturar em 1.0 muito rápido
        excesso = log_v - log_p99
        fator = min(1.0, 0.9 + 0.1 * (excesso / log_p99))
        return fator

# Testar com valores de exemplo
print("=" * 60)
print("FATOR BASELINE - TESTE COM VALORES DE EXEMPLO")
print("=" * 60)

valores_teste = [
    1000,      # Muito baixo
    50000,     # Abaixo da mediana
    72864,     # P50 exato
    100000,    # Logo acima da mediana
    500000,    # Comum
    2000000,   # Alto
    3976428,   # P90
    10000000,  # Acima de P90
    12619737,  # P95
    50000000,  # Alto
    78143970,  # P99
    100000000, # Muito acima de P99
    500000000, # Extremo
    8000000000 # Valor máximo SP
]

print(f"\nPercentis de referência:")
print(f"  P50: R$ {P50:,.2f}")
print(f"  P90: R$ {P90:,.2f}")
print(f"  P95: R$ {P95:,.2f}")
print(f"  P99: R$ {P99:,.2f}")
print()

print(f"{'Valor':>20} | {'Score':>8} | Interpretação")
print("-" * 60)

for v in valores_teste:
    score = calcular_fator_baseline(v)
    
    if score <= 0.1:
        interp = "Normal"
    elif score <= 0.5:
        interp = "Comum"
    elif score <= 0.7:
        interp = "Alto"
    elif score <= 0.9:
        interp = "Raro"
    else:
        interp = "Extremo"
    
    print(f"R$ {v:>15,.0f} | {score:>8.3f} | {interp}")

print("=" * 60)
print("✓ Fator baseline validado!")
print("=" * 60)

# Testar com dados reais do banco
print("\n📊 APLICAÇÃO EM DADOS REAIS")
print("-" * 60)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

cur.execute("""
    SELECT fornecedor, valor
    FROM sp_contratos
    ORDER BY valor DESC
    LIMIT 5
""")

top5 = cur.fetchall()

print("Top 5 contratos reais:")
for i, (forn, val) in enumerate(top5, 1):
    score = calcular_fator_baseline(val)
    print(f"{i}. {forn[:35]:<35} | R$ {val:>15,.0f} | Score: {score:.3f}")

conn.close()

print("\n✓ Pronto para integrar no motor v2!")
EOF

python fator_baseline.py
