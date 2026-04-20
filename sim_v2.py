import math

def fator_baseline(valor):
    if valor <= 0:
        return 0.0
    valor = max(valor, 1.0)
    log_v = math.log(valor)
    p50, p90, p95, p99 = 72864, 3976428, 12619737, 78143970
    
    if valor <= p50:
        return 0.05 + 0.05 * log_v / math.log(p50)
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

def score_regra(qtd, total, nome):
    if 'outros' in nome.lower():
        return 0.0
    prop = qtd / total
    if prop < 0.10:
        return 0.0
    return min(1.0, (prop - 0.10) / 0.40)

def analisar(fornecedores, nome):
    total = sum(f[1] for f in fornecedores)
    print(f"\n{'='*60}\nCENÁRIO: {nome}\nTotal: {total:,}")
    
    resultados = []
    for nome_f, qtd, valor in fornecedores:
        score_r = score_regra(qtd, total, nome_f)
        if score_r == 0.0:
            continue
        conf = confianca(qtd)
        fator = fator_baseline(valor)
        final = score_r * conf * (0.5 + 0.5 * fator)
        resultados.append((nome_f, qtd, qtd/total, score_r, conf, fator, final))
    
    if not resultados:
        print("Sem concentração significativa")
        return
    
    resultados.sort(key=lambda x: x[6], reverse=True)
    print(f"\n{'Fornecedor':<20} {'Qtd':>5} {'%':>5} {'R':>4} {'C':>5} {'F':>5} {'FINAL':>6}")
    print("-" * 60)
    for r in resultados[:4]:
        print(f"{r[0]:<20} {r[1]:>5} {r[2]*100:>5.1f} {r[3]:>4.2f} {r[4]:>5.2f} {r[5]:>5.2f} {r[6]:>6.3f}")
    
    max_score = max(r[6] for r in resultados)
    print(f"\nScore máximo: {max_score:.3f}")
    if max_score > 0.70:
        print("ALERTA: Possível fraude!")
    elif max_score > 0.35:
        print("ATENÇÃO: Investigar")
    else:
        print("Distribuição normal")

print("=" * 60)
print("SIMULAÇÃO v2.2")
print("=" * 60)

# Normal
analisar([("A", 40, 100000), ("B", 35, 80000), ("C", 30, 120000), ("D", 25, 90000), ("Outros", 130, 75000)], "NORMAL")

# Leve
analisar([("Principal", 45, 150000), ("B", 30, 80000), ("C", 25, 120000), ("Outros", 180, 75000)], "LEVE (15%)")

# Moderado
analisar([("Dominante", 75, 200000), ("B", 25, 80000), ("C", 20, 120000), ("Outros", 150, 75000)], "MODERADO (25%)")

# Extremo
analisar([("SUSPEITA", 200, 5000000), ("B", 20, 80000), ("C", 15, 120000), ("Outros", 65, 75000)], "EXTREMO (50%)")

print("\n" + "=" * 60)
print("Simulação concluída!")
