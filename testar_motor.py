#!/usr/bin/env python3
"""
Teste do Motor de Regras - Casos Reais Simulados
Validacao antes de deploy publico
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
    
    print(f"\nResultado:")
    print(f"   Score de Risco: {resultado['score_risco']}")
    print(f"   Nivel: {resultado['nivel_risco_geral'].upper()}")
    print(f"   Alertas: {resultado['total_alertas']}")
    
    if resultado['alertas']:
        print(f"\nDetalhes dos Alertas:")
        for i, alerta in enumerate(resultado['alertas'], 1):
            print(f"\n   {i}. [{alerta['nivel_risco'].upper()}] {alerta['tipo']}")
            print(f"      {alerta['descricao']}")
            print(f"      Score: {alerta['score']}")
            print(f"      Evidencias: {json.dumps(alerta['evidencias'], indent=6)}")
    
    print(f"\nRecomendacao:")
    print(f"   {resultado['recomendacao']}")
    
    print(f"\nExpectativa: {expectativa}")
    print(f"Resultado: {'PASSOU' if resultado['score_risco'] > 0.3 else 'BAIXO RISCO'}")
    
    return resultado

# Caso 1: Prefeitura media - Padrao normal
caso_1 = {
    'orgao': 'Prefeitura de Cidade Media',
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
    "Prefeitura com distribuicao normal",
    caso_1,
    "Esperado: Score baixo (<0.3), sem alertas - distribuicao equilibrada"
)

# Caso 2: Concentracao suspeita
caso_2 = {
    'orgao': 'Prefeitura com cartel suspeito',
    'contratos': [
        {'fornecedor': 'Empresa X', 'valor': 500000, 'tipo_servico': 'TI'},
        {'fornecedor': 'Empresa X', 'valor': 450000, 'tipo_servico': 'TI'},
        {'fornecedor': 'Empresa X', 'valor': 600000, 'tipo_servico': 'TI'},
        {'fornecedor': 'Empresa X', 'valor': 550000, 'tipo_servico': 'TI'},
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
    "Esperado: Score ALTO (>0.5), alerta de concentracao"
)

# Resumo
print("\n" + "="*80)
print("RESUMO DOS TESTES")
print("="*80)

print(f"\n{'Caso':<30} {'Score':<10} {'Nivel':<15} {'Alertas':<10}")
print("-" * 70)
print(f"{'Caso 1 - Normal':<30} {r1['score_risco']:<10.2f} {r1['nivel_risco_geral'].upper():<15} {r1['total_alertas']:<10}")
print(f"{'Caso 2 - Concentracao':<30} {r2['score_risco']:<10.2f} {r2['nivel_risco_geral'].upper():<15} {r2['total_alertas']:<10}")

print("\nANALISE:")
print(f"- Caso 1 (Normal): Score {r1['score_risco']:.2f} - {'OK' if r1['score_risco'] < 0.3 else 'REVISAR'}")
print(f"- Caso 2 (Suspeito): Score {r2['score_risco']:.2f} - {'OK' if r2['score_risco'] > 0.5 else 'REVISAR'}")
