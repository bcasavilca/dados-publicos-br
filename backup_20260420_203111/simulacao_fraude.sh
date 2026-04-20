#!/bin/bash
# Simulação de Fraude Controlada - Teste do Motor v2.1

cat > simulacao_fraude.py << 'EOF'
"""
Simulação de Fraude Controlada
Valida comportamento do Motor v2.1 em cenários extremos
"""

import os
import psycopg2
import math

# Baseline SP 2024
BASELINE = {
    'p50': 72864.00,
    'p90': 3976428.50,
    'p95': 12619737.04,
    'p99': 78143970.65,
    'conc_top3': 0.0161
}

def fator_baseline(valor):
    if valor <= 0:
        return 0.0
    valor = max(valor, 1.0)
    log_v = math.log(valor)
    p50, p90, p95, p99 = BASELINE['p50'], BASELINE['p90'], BASELINE['p95'], BASELINE['p99']
    
    if valor <= p50:
        return 0.05 + 0.05 * (log_v - math.log(1.0)) / (math.log(p50) - math.log(1.0))
    elif valor <= p90:
        return 0.1 + 0.4 * (log_v - math.log(p50)) / (math.log(p90) - math.log(p50))
    elif valor <= p95:
        return 0.5 + 0.2 * (log_v - math.log(p90)) / (math.log(p95) - math.log(p90))
    elif valor <= p99:
        return 0.7 + 0.2 * (log_v - math.log(p95)) / (math.log(p99) - math.log(p95))
    else:
        return min(1.0, 0.9 + 0.1 * (log_v - math.log(p99)) / math.log(p99))

def confianca(qtd):
    return 1 - math.exp(-qtd / 20)

def score_regra_fornecedor(qtd, total):
    """Score CONTÍNUO baseado na proporção de contratos"""
    proporcao = qtd / total
    limiar = BASELINE['conc_top3']  # 1.61%
    
    if proporcao < limiar:
        return 0.0
    
    # Cresce suavemente acima do baseline
    return min(1.0, (proporcao - limiar) / 0.20)

def analisar_cenario(fornecedores, nome_cenario):
    """
    fornecedores = [(nome, qtd_contratos, valor_medio), ...]
    """
    total = sum(f[1] for f in fornecedores)
    
    print(f"\n{'='*70}")
    print(f"CENÁRIO: {nome_cenario}")
    print(f"{'='*70}")
    print(f"Total de contratos: {total:,}")
    print(f"Fornecedores: {len(fornecedores)}")
    
    resultados = []
    
    for nome, qtd, valor_medio in fornecedores:
        # Score regra contínuo
        score_r = score_regra_fornecedor(qtd, total)
        
        # Confiança
        conf = confianca(qtd)
        
        # Fator baseline
        fator = fator_baseline(valor_medio)
        
        # Score final v2.1
        score_final = score_r * conf * (0.5 + 0.5 * fator)
        
        resultados.append({
            'nome': nome,
            'qtd': qtd,
            'proporcao': qtd/total,
            'valor_medio': valor_medio,
            'score_r': score_r,
            'conf': conf,
            'fator': fator,
            'final': score_final
        })
    
    # Ordenar por score final
    resultados.sort(key=lambda x: x['final'], reverse=True)
    
    print(f"\n{'Fornecedor':<30} {'Qtd':>6} {'%':>6} {'Score_R':>8} {'Conf':>6} {'Fator':>6} {'FINAL':>8}")
    print("-" * 70)
    
    for r in resultados[:5]:  # Top 5
        print(f"{r['nome'][:28]:<30} {r['qtd']:>6} {r['proporcao']*100:>6.1f} {r['score_r']:>8.3f} {r['conf']:>6.3f} {r['fator']:>6.3f} {r['final']:>8.3f}")
    
    # Análise
    max_score = max(r['final'] for r in resultados)
    fornecedor_top = max(resultados, key=lambda x: x['final'])
    
    print(f"\n📊 ANÁLISE:")
    print(f"  Score máximo: {max_score:.3f}")
    print(f"  Fornecedor crítico: {fornecedor_top['nome'][:30]}")
    print(f"  Proporção: {fornecedor_top['proporcao']*100:.1f}%")
    
    if max_score > 0.75:
        print(f"  ⚠️  ALERTA: Score > 0.75 - Possível concentração anômala!")
    elif max_score > 0.4:
        print(f"  ⚡ ATENÇÃO: Score médio-alto - Requer investigação")
    else:
        print(f"  ✅ Distribuição normal")
    
    return resultados

def main():
    print("=" * 70)
    print("SIMULAÇÃO DE FRAUDE CONTROLADA")
    print("Motor v2.1 - Validação de Comportamento")
    print("=" * 70)
    
    # ============================================================
    # CENÁRIO A: Normal (distribuição homogênea)
    # ============================================================
    cenario_normal = [
        ("Fornecedor A", 50, 100000),
        ("Fornecedor B", 45, 80000),
        ("Fornecedor C", 40, 120000),
        ("Fornecedor D", 35, 90000),
        ("Fornecedor E", 30, 110000),
        ("Outros", 100, 75000),
    ]
    
    analisar_cenario(cenario_normal, "NORMAL (distribuição homogênea)")
    
    # ============================================================
    # CENÁRIO B: Leve concentração (~15%)
    # ============================================================
    cenario_leve = [
        ("FORNECEDOR DOMINANTE", 60, 150000),  # ~15%
        ("Fornecedor B", 30, 80000),
        ("Fornecedor C", 25, 120000),
        ("Fornecedor D", 20, 90000),
        ("Outros", 145, 75000),
    ]
    
    analisar_cenario(cenario_leve, "LEVE CONCENTRAÇÃO (15% do total)")
    
    # ============================================================
    # CENÁRIO C: Extremo - Fraude clássica (~50%)
    # ============================================================
    cenario_extremo = [
        ("EMPRESA SUSPEITA LTDA", 200, 5000000),  # 50%!
        ("Fornecedor B", 20, 80000),
        ("Fornecedor C", 15, 120000),
        ("Fornecedor D", 10, 90000),
        ("Outros", 55, 75000),
    ]
    
    analisar_cenario(cenario_extremo, "EXTREMO - FRAUDE CLÁSSICA (50% do total)")
    
    # ============================================================
    # CENÁRIO D: Real SP (dados reais)
    # ============================================================
    print(f"\n{'='*70}")
    print("CENÁRIO: DADOS REAIS SÃO PAULO 2024")
    print(f"{'='*70}")
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    cur.execute("""
        SELECT fornecedor, COUNT(*), AVG(valor)
        FROM sp_contratos
        GROUP BY fornecedor
        ORDER BY COUNT(*) DESC
        LIMIT 5
    """)
    
    cur_total = conn.cursor()
    cur_total.execute("SELECT COUNT(*) FROM sp_contratos")
    total_real = cur_total.fetchone()[0]
    
    print(f"\nTotal real: {total_real:,} contratos")
    print(f"\n{'Fornecedor':<30} {'Qtd':>6} {'%':>6} {'Score_R':>8} {'Conf':>6} {'Fator':>6} {'FINAL':>8}")
    print("-" * 70)
    
    for fornecedor, qtd, valor_medio in cur.fetchall():
        score_r = score_regra_fornecedor(qtd, total_real)
        conf = confianca(qtd)
        fator = fator_baseline(valor_medio)
        final = score_r * conf * (0.5 + 0.5 * fator)
        
        print(f"{fornecedor[:28]:<30} {qtd:>6} {(qtd/total_real)*100:>6.1f} {score_r:>8.3f} {conf:>6.3f} {fator:>6.3f} {final:>8.3f}")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✓ Simulação concluída!")
    print("=" * 70)

if __name__ == '__main__':
    main()
EOF

python simulacao_fraude.py
