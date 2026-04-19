#!/usr/bin/env python3
"""
Motor de Regras v2 - COM CONFIANCA POR VOLUME
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import statistics
import json

@dataclass
class Alerta:
    tipo: str
    descricao: str
    nivel_risco: str
    score: float
    confianca: float
    evidencias: Dict
    fontes: List[str]
    nota: str = ""
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class RegraFornecedorRecorrente:
    """Regra com confianca por volume"""
    
    def analisar(self, dados: Dict) -> Optional[Alerta]:
        contratos = dados.get('contratos', [])
        total = len(contratos)
        
        # Calcula confianca baseada no volume
        confianca = min(1.0, total / 50)  # 50 contratos = confianca maxima
        
        if total < 5:
            return None
        
        fornecedores = {}
        for c in contratos:
            forn = c.get('fornecedor', 'N/A')
            valor = c.get('valor', 0)
            if forn not in fornecedores:
                fornecedores[forn] = {'qtd': 0, 'valor': 0}
            fornecedores[forn]['qtd'] += 1
            fornecedores[forn]['valor'] += valor
        
        for forn, dados_forn in fornecedores.items():
            percentual = dados_forn['qtd'] / total
            
            # Score baseado em faixas
            if percentual >= 0.70:
                score_bruto = 1.0
                nivel = 'critico'
            elif percentual >= 0.50:
                score_bruto = 0.8
                nivel = 'alto'
            elif percentual >= 0.40:
                score_bruto = 0.6
                nivel = 'medio'
            else:
                continue
            
            # Ajusta score pela confianca
            score_final = score_bruto * confianca
            
            # Nota sobre volume
            if confianca < 0.5:
                nota = f"Amostra pequena ({total} contratos)"
            else:
                nota = ""
            
            return Alerta(
                tipo='fornecedor_recorrente',
                descricao=f'{forn}: {dados_forn["qtd"]} contratos ({percentual:.1%})',
                nivel_risco=nivel,
                score=round(score_final, 2),
                confianca=round(confianca, 2),
                evidencias={
                    'fornecedor': forn,
                    'quantidade': dados_forn['qtd'],
                    'percentual': round(percentual, 2),
                    'valor_total': dados_forn['valor'],
                    'total_contratos': total
                },
                fontes=['Compras'],
                nota=nota
            )
        return None

class MotorRegras:
    def __init__(self):
        self.regras = [RegraFornecedorRecorrente()]
    
    def analisar(self, dados: Dict) -> Dict:
        alertas = []
        
        for regra in self.regras:
            alerta = regra.analisar(dados)
            if alerta:
                alertas.append(alerta)
        
        # Score ponderado
        if alertas:
            score = sum(a.score for a in alertas) / len(alertas)
        else:
            score = 0.0
        
        # Nivel geral
        if score >= 0.7:
            nivel = 'critico'
        elif score >= 0.5:
            nivel = 'alto'
        elif score >= 0.3:
            nivel = 'medio'
        else:
            nivel = 'baixo'
        
        return {
            'orgao': dados.get('orgao', 'N/A'),
            'score_risco': round(score, 2),
            'nivel_risco_geral': nivel,
            'total_alertas': len(alertas),
            'alertas': [{
                'tipo': a.tipo,
                'descricao': a.descricao,
                'nivel_risco': a.nivel_risco,
                'score': a.score,
                'confianca': a.confianca,
                'nota': a.nota,
                'evidencias': a.evidencias
            } for a in alertas]
        }

# Teste
if __name__ == '__main__':
    motor = MotorRegras()
    
    # Caso 1: 5 contratos (confianca baixa)
    print("=== CASO 1: 5 contratos (confianca baixa) ===")
    r1 = motor.analisar({
        'orgao': 'Prefeitura A',
        'contratos': [
            {'fornecedor': 'Emp A', 'valor': 50000},
            {'fornecedor': 'Emp A', 'valor': 45000},
            {'fornecedor': 'Emp B', 'valor': 48000},
            {'fornecedor': 'Emp C', 'valor': 52000},
            {'fornecedor': 'Emp D', 'valor': 47000},
        ]
    })
    print(f"Score: {r1['score_risco']} | Nivel: {r1['nivel_risco_geral']}")
    if r1['alertas']:
        print(f"Confianca: {r1['alertas'][0]['confianca']}")
        print(f"Nota: {r1['alertas'][0]['nota']}")
    
    # Caso 2: 50 contratos (confianca alta)
    print("\n=== CASO 2: 50 contratos (confianca alta) ===")
    contratos_50 = [{'fornecedor': 'Emp X', 'valor': 100000} for _ in range(25)]  # 50%
    contratos_50 += [{'fornecedor': f'Emp {i}', 'valor': 50000} for i in range(25)]
    
    r2 = motor.analisar({
        'orgao': 'Prefeitura B',
        'contratos': contratos_50
    })
    print(f"Score: {r2['score_risco']} | Nivel: {r2['nivel_risco_geral']}")
    if r2['alertas']:
        print(f"Confianca: {r2['alertas'][0]['confianca']}")
        print(f"Nota: {r2['alertas'][0]['nota']}")
