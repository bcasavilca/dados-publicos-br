#!/bin/bash
# Motor v2.1 - Integrado com Fator Baseline

cat > motor_v21.py << 'EOF'
"""
Motor de Regras v2.1 - Integrado com Baseline Contextual
Data: 2024-04-20
Base: SP 2024 (23.987 contratos)
"""

import os
import psycopg2
import math
from datetime import datetime

# ============================================================
# BASELINE SP 2024 (percentis calculados)
# ============================================================
BASELINE_SP = {
    'p50': 72864.00,
    'p90': 3976428.50,
    'p95': 12619737.04,
    'p99': 78143970.65,
    'total_contratos': 23987,
    'concentracao_top3': 0.0161  # 1.61%
}

def calcular_fator_baseline(valor):
    """
    Calcula fator de baseline com escala logarítmica.
    Retorna valor entre 0.0 e 1.0
    """
    if valor <= 0:
        return 0.0
    
    valor = max(valor, 1.0)
    p50, p90, p95, p99 = BASELINE_SP['p50'], BASELINE_SP['p90'], BASELINE_SP['p95'], BASELINE_SP['p99']
    
    log_v = math.log(valor)
    log_p50 = math.log(max(p50, 1.0))
    log_p90 = math.log(max(p90, 1.0))
    log_p95 = math.log(max(p95, 1.0))
    log_p99 = math.log(max(p99, 1.0))
    
    if valor <= p50:
        return 0.05 + 0.05 * (log_v - math.log(1.0)) / (log_p50 - math.log(1.0))
    elif valor <= p90:
        return 0.1 + 0.4 * (log_v - log_p50) / (log_p90 - log_p50)
    elif valor <= p95:
        return 0.5 + 0.2 * (log_v - log_p90) / (log_p95 - log_p90)
    elif valor <= p99:
        return 0.7 + 0.2 * (log_v - log_p95) / (log_p99 - log_p95)
    else:
        excesso = log_v - log_p99
        return min(1.0, 0.9 + 0.1 * (excesso / log_p99))

def calcular_confianca(qtd_contratos):
    """Confiança não-linear baseada em volume"""
    return 1 - math.exp(-qtd_contratos / 20)

def regra_concentracao(contratos_fornecedor, total_contratos):
    """Detecta fornecedor com muitos contratos"""
    concentracao = contratos_fornecedor / total_contratos
    limiar = BASELINE_SP['concentracao_top3'] * 3  # 3× baseline
    
    if concentracao > limiar:
        return min(1.0, concentracao * 2), "Fornecedor com concentração anômala"
    return 0.0, None

def regra_valor_anomalo(valor):
    """Detecta valor muito acima do normal"""
    if valor > BASELINE_SP['p99']:
        return 0.7, f"Valor acima de P99 (R$ {BASELINE_SP['p99']:,.2f})"
    elif valor > BASELINE_SP['p95']:
        return 0.5, f"Valor acima de P95 (R$ {BASELINE_SP['p95']:,.2f})"
    return 0.0, None

def analisar_fornecedor(fornecedor, conn):
    """Analisa um fornecedor específico"""
    cur = conn.cursor()
    
    # Buscar dados do fornecedor
    cur.execute("""
        SELECT COUNT(*), SUM(valor), MAX(valor)
        FROM sp_contratos
        WHERE fornecedor = %s
    """, (fornecedor,))
    
    qtd, total, maximo = cur.fetchone()
    
    if qtd == 0:
        return None
    
    # Total de contratos no sistema
    cur.execute("SELECT COUNT(*) FROM sp_contratos")
    total_sistema = cur.fetchone()[0]
    
    # Aplicar regras
    alertas = []
    scores = []
    
    # R1: Concentração
    score_r1, msg_r1 = regra_concentracao(qtd, total_sistema)
    if score_r1 > 0:
        scores.append(score_r1)
        alertas.append(msg_r1)
    
    # R2: Valor anômalo
    score_r2, msg_r2 = regra_valor_anomalo(maximo)
    if score_r2 > 0:
        scores.append(score_r2)
        alertas.append(msg_r2)
    
    # Combinar scores das regras (máximo)
    score_regras = max(scores) if scores else 0.0
    
    # Calcular confiança
    confianca = calcular_confianca(qtd)
    
    # Calcular fator baseline (média dos valores)
    media_valor = total / qtd
    fator_baseline = calcular_fator_baseline(media_valor)
    
    # FÓRMULA CORRETA v2.1
    # score_final = score_regras × confiança × (0.5 + 0.5 × fator_baseline)
    score_final = score_regras * confianca * (0.5 + 0.5 * fator_baseline)
    
    return {
        'fornecedor': fornecedor,
        'contratos': qtd,
        'total_valor': total,
        'valor_maximo': maximo,
        'score_regras': score_regras,
        'confianca': confianca,
        'fator_baseline': fator_baseline,
        'score_final': score_final,
        'alertas': alertas,
        'nivel': 'ALTO' if score_final > 0.75 else 'MEDIO' if score_final > 0.4 else 'BAIXO'
    }

def main():
    print("=" * 80)
    print("MOTOR DE ANÁLISE v2.1 - Integrado com Baseline SP 2024")
    print("=" * 80)
    print(f"\nBaseline carregado:")
    print(f"  Total: {BASELINE_SP['total_contratos']:,} contratos")
    print(f"  P50: R$ {BASELINE_SP['p50']:,.2f}")
    print(f"  P99: R$ {BASELINE_SP['p99']:,.2f}")
    print(f"  Concentração Top 3: {BASELINE_SP['concentracao_top3']*100:.2f}%")
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    
    # Analisar top fornecedores
    print("\n" + "=" * 80)
    print("ANÁLISE DOS TOP FORNECEDORES")
    print("=" * 80)
    
    cur = conn.cursor()
    cur.execute("""
        SELECT fornecedor, COUNT(*)
        FROM sp_contratos
        GROUP BY fornecedor
        ORDER BY COUNT(*) DESC
        LIMIT 5
    """)
    
    top5 = cur.fetchall()
    
    for fornecedor, _ in top5:
        resultado = analisar_fornecedor(fornecedor, conn)
        if resultado:
            print(f"\n{resultado['fornecedor'][:50]}")
            print(f"  Contratos: {resultado['contratos']}")
            print(f"  Valor máximo: R$ {resultado['valor_maximo']:,.2f}")
            print(f"  Score Regras: {resultado['score_regras']:.3f}")
            print(f"  Confiança: {resultado['confianca']:.3f}")
            print(f"  Fator Baseline: {resultado['fator_baseline']:.3f}")
            print(f"  → SCORE FINAL: {resultado['score_final']:.3f} [{resultado['nivel']}]")
            if resultado['alertas']:
                for alerta in resultado['alertas']:
                    print(f"  ⚠️ {alerta}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✓ Análise concluída!")
    print("=" * 80)

if __name__ == '__main__':
    main()
EOF

python motor_v21.py
