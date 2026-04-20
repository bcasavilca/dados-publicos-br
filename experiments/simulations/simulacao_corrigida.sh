#!/bin/bash
# Simulação Corrigida - Motor v2.2

cat > simulacao_corrigida.py << 'EOF'
import os
import psycopg2
import math

BASELINE = {'p50': 72864.00, 'p90': 3976428.50, 'p95': 12619737.04, 'p99': 78143970.65}

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

def score_regra_corrigido(qtd, total, nome):
    """
    Versão corrigida:
    - Ignora 'Outros' (agregação)
    - Threshold mais conservador (10%)
    - Curva mais suave
    """
    # Ignorar agregações
    if 'outros' in nome.lower() or 'outro' in nome.lower():
        return 0.0, "ignorado (agregação)"
    
    prop = qtd / total
    limiar = 0.10  # 10% - mais conservador
    
    if prop < limiar:
        return 0.0, f"abaixo de {limiar*100:.0f}%"
    
    # Curva suave: cresce a partir de 10%, satura em 50%
    # prop=10% → 0
    # prop=30% → 0.5
    # prop=50%+ → 1.0
    score = min(1.0, (prop - limiar) / 0.40)
    
    return score, f"concentração {prop*100:.1f}%"

def analisar(fornecedores, nome, mostrar_ignorados=False):
    total = sum(f[1] for f in fornecedores)
    
    print(f"\n{'='*60}")
    print(f"CENÁRIO: {nome}")
    print(f"Total: {total:,} contratos")
    
    resultados = []
    ignorados = []
    
    for nome_f, qtd, valor in fornecedores:
        score_r, msg = score_regra_corrigido(qtd, total, nome_f)
        
        if score_r == 0.0 and 'ignorado' in msg:
            ignorados.append((nome_f, qtd, msg))
            continue
        
        conf = confianca(qtd)
        fator = fator_baseline(valor)
        final = score_r * conf * (0.5 + 0.5 * fator)
        
        resultados.append({
            'nome': nome_f,
            'qtd': qtd,
            'prop': qtd/total,
            'score_r': score_r,
            'msg': msg,
            'conf': conf,
            'fator': fator,
            'final': final
        })
    
    # Ordenar por score final
    resultados.sort(key=lambda x: x['final'], reverse=True)
    
    if resultados:
        print(f"\n{'Fornecedor':<22} {'Qtd':>5} {'%':>5} {'R':>4} {'C':<5} {'F':<5} {'FINAL':<6}")
        print("-" * 60)
        for r in resultados[:5]:
            print(f"{r['nome'][:20]:<22} {r['qtd']:>5} {r['prop']*100:>5.1f} {r['score_r']:>4.2f} {r['conf']:<5.2f} {r['fator']:<5.2f} {r['final']:<6.3f}")
    
    if mostrar_ignorados and ignorados:
        print(f"\n[Ignorados: {len(ignorados)} agregações]")
        for ign in ignorados[:2]:
            print(f"  - {ign[0]}: {ign[1]} contratos ({ign[2]})")
    
    if resultados:
        max_score = max(r['final'] for r in resultados)
        print(f"\n📊 Score máximo: {max_score:.3f}")
        
        if max_score > 0.70:
            print("⚠️  ALERTA: Possível fraude!")
        elif max_score > 0.35:
            print("⚡ ATENÇÃO: Investigar")
        else:
            print("✅ Distribuição normal")
    else:
        print("\n✅ Sem concentração significativa")

def main():
    print("=" * 60)
    print("SIMULAÇÃO CORRIGIDA - Motor v2.2")
    print("Ajustes: threshold 10%, ignora 'Outros', curva suave")
    print("=" * 60)
    
    # Cenário A: Normal - distribuição homogênea
    analisar([
        ("Empresa A", 40, 100000),
        ("Empresa B", 35, 80000),
        ("Empresa C", 30, 120000),
        ("Empresa D", 25, 90000),
        ("Empresa E", 20, 110000),
        ("Outros", 130, 75000),  # Será ignorado
    ], "NORMAL")
    
    # Cenário B: Leve - 15%
    analisar([
        ("Fornecedor Principal", 45, 150000),  # 15%
        ("Empresa B", 30, 80000),
        ("Empresa C", 25, 120000),
        ("Empresa D", 20, 90000),
        ("Outros", 180, 75000),  # Será ignorado
    ], "LEVE (15%)")
    
    # Cenário C: Moderado - 25%
    analisar([
        ("Grupo Dominante", 75, 200000),  # 25%
        ("Empresa B", 25, 80000),
        ("Empresa C", 20, 120000),
        ("Outros", 150, 75000),
    ], "MODERADO (25%)")
    
    # Cenário D: Extremo - 50%
    analisar([
        ("EMPRESA SUSPEITA LTDA", 200, 5000000),  # 50%!
        ("Empresa B", 20, 80000),
        ("Empresa C", 15, 120000),
        ("Outros", 65, 75000),
    ], "EXTREMO (50%) - FRAUDE")
    
    # Cenário E: Dados reais SP 2024
    print(f"\n{'='*60}")
    print("CENÁRIO: DADOS REAIS SÃO PAULO 2024")
    print(f"{'='*60}")
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM sp_contratos")
    total_real = cur.fetchone()[0]
    
    # Pegar top 10, filtrar agregações depois
    cur.execute("""
        SELECT fornecedor, COUNT(*), AVG(valor)
        FROM sp_contratos
        GROUP BY fornecedor
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    
    fornecedores_sp = [(f, q, v) for f, q, v in cur.fetchall()]
    conn.close()
    
    analisar(fornecedores_sp, f"REAL SP ({total_real:,} contratos)", mostrar_ignorados=False)
    
    print("\n" + "=" * 60)
    print("✓ Simulação corrigida concluída!")
    print("=" * 60)

if __name__ == '__main__':
    main()
EOF

python simulacao_corrigida.py
