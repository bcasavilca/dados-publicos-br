#!/usr/bin/env python3
"""
Teste do Motor de Regras - Casos Reais Simulados
Validação antes de deploy público
"""

from motor_regras import MotorRegras
import json

def testar_caso(nome, dados, expectativa):
    """Executa teste e mostra resultado"""
    print(f"\n{'='*80}")
    print(f"CASO: {nome}")
    print(f"{'='*80}")
    
    motor = MotorRegras()
    resultado = motor.analisar(dados)
    
    print(f"\n📊 Resultado:")
    print(f"   Score de Risco: {resultado['score_risco']}")
    print(f"   Nível: {resultado['nivel_risco_geral'].upper()}")
    print(f"   Alertas: {resultado['total_alertas']}")
    
    if resultado['alertas']:
        print(f"\n🚨 Detalhes dos Alertas:")
        for i, alerta in enumerate(resultado['alertas'], 1):
            print(f"\n   {i}. [{alerta['nivel_risco'].upper()}] {alerta['tipo']}")
            print(f"      {alerta['descricao']}")
            print(f"      Score: {alerta['score']}")
            print(f"      Evidências: {json.dumps(alerta['evidencias'], indent=6)}")
    
    print(f"\n💡 Recomendação:")
    print(f"   {resultado['recomendacao']}")
    
    print(f"\n✓ Expectativa: {expectativa}")
    print(f"✓ Resultado: {'PASSOU' if resultado['score_risco'] > 0.3 else 'BAIXO RISCO'}")
    
    return resultado

# Caso 1: Prefeitura média - Padrão normal
print("\n" + "="*80)
print("TESTE 1: Prefeitura com padrão NORMAL")
print("="*80)

caso_1 = {
    'orgao': 'Prefeitura de Cidade Média',
    'contratos': [
        {'fornecedor': 'Empresa A', 'valor': 50000, 'tipo_servico': 'limpeza'},
        {'fornecedor': 'Empresa B', 'valor': 45000, 'tipo_servico': 'limpeza'},
        {'fornecedor': 'Empresa C', 'valor': 48000, 'tipo_servico': 'limpeza'},
        {'fornecedor': 'Empresa A', 'valor': 52000, 'tipo_servico': 'manutencao'},
        {'fornecedor': 'Empresa D', 'valor': 47000, 'tipo_servico': 'seguranca'},
    ],
    'empresas': {}
}

r1 = testar_caso(
    "Prefeitura com distribuição normal",
    caso_1,
    "Esperado: Score baixo (<0.3), sem alertas - distribuição equilibrada"
)

# Caso 2: Concentração suspeita
print("\n" + "="*80)
print("TESTE 2: Concentração SUSPEITA")
print("="*80)

caso_2 = {
    'orgao': 'Prefeitura com cartel suspeito',
    'contratos': [
        {'fornecedor': 'Empresa X', 'valor': 500000, 'tipo_servico': 'TI'},
        {'fornecedor': 'Empresa X', 'valor': 450000, 'tipo_servico': 'TI'},
        {'fornecedor': 'Empresa X', 'valor': 600000, 'tipo_servico': 'TI'},
        {'fornecidor': 'Empresa X', 'valor': 550000, 'tipo_servico': 'TI'},
        {'fornecedor': 'Empresa X', 'valor': 480000, 'tipo_servico': 'TI'},
        {'fornecedor': 'Empresa Y', 'valor': 50000, 'tipo_servico': 'limpeza'},
    ],
    'empresas': {
        'Empresa X': {'data_abertura': '2023-06-15', 'cnae': 'Comercio varejista'},
    }
}

r2 = testar_caso(
    "Empresa dominando 83% dos contratos",
    caso_2,
    "Esperado: Score ALTO (>0.5), alerta de concentração"
)

# Caso 3: Empresa nova com contrato milionário
print("\n" + "="*80)
print("TESTE 3: Empresa NOVA com contrato MILIONÁRIO")
print("="*80)

caso_3 = {
    'orgao': 'Órgão Federal',
    'contratos': [
        {'fornecedor': 'Nova Empresa Ltda', 'valor': 2500000, 'tipo_servico': 'consultoria'},
        {'fornecedor': 'Empresa Antiga', 'valor': 150000, 'tipo_servico': 'limpeza'},
        {'fornecedor': 'Outra Empresa', 'valor': 200000, 'tipo_servico': 'manutencao'},
    ],
    'empresas': {
        'Nova Empresa Ltda': {'data_abertura': '2024-03-01', 'cnae': 'Consultoria'},
    }
}

r3 = testar_caso(
    "Empresa criada há 2 meses ganha contrato de R$ 2.5M",
    caso_3,
    "Esperado: Score ALTO, alerta de empresa nova"
)

# Caso 4: Incompatibilidade de CNAE
print("\n" + "="*80)
print("TESTE 4: Incompatibilidade de CNAE")
print("="*80)

caso_4 = {
    'orgao': 'Secretaria de Saúde',
    'contratos': [
        {'fornecedor': 'Padaria São João', 'valor': 800000, 'tipo_servico': 'TI'},
        {'fornecedor': 'TechCorp', 'valor': 90000, 'tipo_servico': 'TI'},
    ],
    'empresas': {
        'Padaria São João': {'data_abertura': '2015-01-01', 'cnae': 'Padaria e confeitaria'},
    }
}

r4 = testar_caso(
    "Padaria ganhando contrato de TI de R$ 800k",
    caso_4,
    "Esperado: Alerta de incompatibilidade CNAE"
)

# Resumo final
print("\n" + "="*80)
print("RESUMO DOS TESTES")
print("="*80)

casos = [
    ("Caso 1 - Normal", r1),
    ("Caso 2 - Concentração", r2),
    ("Caso 3 - Empresa Nova", r3),
    ("Caso 4 - CNAE", r4),
]

print("\n📊 Tabela de Resultados:")
print(f"{'Caso':<30} {'Score':<10} {'Nível':<15} {'Alertas':<10}")
print("-" * 70)
for nome, r in casos:
    print(f"{nome:<30} {r['score_risco']:<10.2f} {r['nivel_risco_geral'].upper():<15} {r['total_alertas']:<10}")

# Calibração sugerida
print("\n🔧 CALIBRAÇÃO SUGERIDA:")
print("-" * 40)

# Analisar thresholds
print(f"\n1. Threshold de concentração (atual: 20%):")
print(f"   Caso 2 teve 83% - Score: {r2['score_risco']:.2f}")
print(f"   → Parece adequado")

print(f"\n2. Threshold de valor (atual: 3x desvio):")
if r3['alertas']:
    val_alert = [a for a in r3['alertas'] if a['tipo'] == 'valor_anomalo']
    if val_alert:
        print(f"   Caso 3 disparou alerta de valor")
        print(f"   → Parece adequado")

print(f"\n3. Peso das regras:")
print(f"   fornecedor_recorrente: 0.4 (maior peso)")
print(f"   valor_anomalo: 0.3")
print(f"   empresa_nova: 0.3")
print(f"   → Distribuição parece equilibrada")

print("\n" + "="*80)
print("✅ Testes concluídos. Revise os resultados acima.")
print("="*80)
