#!/usr/bin/env python3
"""
Motor de Regras v2.0 - Detecao de Padroes Suspeitos
Estrutura: dados → regras → sinais (alertas) com confianca
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import statistics
import math

ENGINE_VERSION = "v2.0"

@dataclass
class Alerta:
    """Modelo padronizado de alerta com confianca"""
    tipo: str
    descricao: str
    nivel_risco: str
    score: float
    confianca: float
    nivel_confianca: str
    evidencias: Dict
    fontes: List[str]
    nota: str = ""
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class Regra:
    """Classe base para todas as regras"""
    def calcular_confianca(self, total_contratos: int) -> float:
        """Confianca nao-linear: cresce rapido no inicio, estabiliza depois"""
        return 1 - math.exp(-total_contratos / 20)
    
    def nivel_confianca(self, conf: float) -> str:
        if conf >= 0.75:
            return 'alta'
        elif conf >= 0.4:
            return 'media'
        return 'baixa'
    
    def analisar(self, dados: Dict) -> Optional[Alerta]:
        raise NotImplementedError

class RegraFornecedorRecorrente(Regra):
    """
    Regra 1: Mesma empresa ganhando muitos contratos
    Alerta se empresa tem > 40% dos contratos (com confianca)
    """
    def analisar(self, dados: Dict) -> Optional[Alerta]:
        contratos = dados.get('contratos', [])
        total = len(contratos)
        
        if total < 5:
            return None
        
        confianca = self.calcular_confianca(total)
        nivel_conf = self.nivel_confianca(confianca)
        
        # Contar por fornecedor
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
            
            # Score por faixas
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
            
            # Ajusta pela confianca
            score_final = score_bruto * confianca
            
            # Nota
            nota = f"Confianca {nivel_conf}" if confianca < 0.75 else ""
            
            return Alerta(
                tipo='fornecedor_recorrente',
                descricao=f'{forn}: {dados_forn["qtd"]} contratos ({percentual:.1%})',
                nivel_risco=nivel,
                score=round(score_final, 2),
                confianca=round(confianca, 2),
                nivel_confianca=nivel_conf,
                evidencias={
                    'fornecedor': forn,
                    'quantidade': dados_forn['qtd'],
                    'percentual': round(percentual, 2),
                    'valor_total': dados_forn['valor'],
                    'total_contratos': total
                },
                fontes=['Compras.gov.br'],
                nota=nota
            )
        return None

class RegraValorAnomalo(Regra):
    """Regra 2: Valor muito acima da media"""
    def analisar(self, dados: Dict) -> Optional[Alerta]:
        contratos = dados.get('contratos', [])
        valores = [c.get('valor', 0) for c in contratos if c.get('valor', 0) > 0]
        
        if len(valores) < 5:
            return None
        
        confianca = self.calcular_confianca(len(valores))
        nivel_conf = self.nivel_confianca(confianca)
        
        media = statistics.mean(valores)
        desvio = statistics.stdev(valores) if len(valores) > 1 else 0
        
        for c in contratos:
            valor = c.get('valor', 0)
            if valor > media + (3 * desvio):
                score_bruto = min((valor / media) / 5, 1.0)
                score_final = score_bruto * confianca
                
                return Alerta(
                    tipo='valor_anomalo',
                    descricao=f'R$ {valor:,.2f} ({valor/media:.1f}x media)',
                    nivel_risco='alto',
                    score=round(score_final, 2),
                    confianca=round(confianca, 2),
                    nivel_confianca=nivel_conf,
                    evidencias={
                        'valor': valor,
                        'media': round(media, 2),
                        'desvio': round(desvio, 2),
                        'fornecedor': c.get('fornecedor', 'N/A')
                    },
                    fontes=['Compras.gov.br'],
                    nota=f"Confianca {nivel_conf}" if confianca < 0.75 else ""
                )
        return None

class MotorRegras:
    """Orquestrador de todas as regras"""
    
    def __init__(self):
        self.regras = [
            RegraFornecedorRecorrente(),
            RegraValorAnomalo()
        ]
    
    def analisar(self, dados: Dict) -> Dict:
        alertas = []
        
        for regra in self.regras:
            alerta = regra.analisar(dados)
            if alerta:
                alertas.append(alerta)
        
        # Score medio ponderado pela confianca
        if alertas:
            score = sum(a.score for a in alertas) / len(alertas)
            confianca_media = sum(a.confianca for a in alertas) / len(alertas)
        else:
            score = 0.0
            confianca_media = self.calcular_confianca(len(dados.get('contratos', [])))
        
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
            'aviso_legal': 'Este resultado nao indica irregularidade, apenas padrao estatistico. Nao use como prova sem investigacao adicional.',
            'uso_recomendado': 'apoio a analise, nao evidencia conclusiva',
            'engine_version': ENGINE_VERSION,
            'orgao_analisado': dados.get('orgao', 'N/A'),
            'score_risco': round(score, 2),
            'confianca_media': round(confianca_media, 2),
            'nivel_risco_geral': nivel,
            'total_alertas': len(alertas),
            'alertas': [{
                'tipo': a.tipo,
                'descricao': a.descricao,
                'nivel_risco': a.nivel_risco,
                'score': a.score,
                'confianca': a.confianca,
                'nivel_confianca': a.nivel_confianca,
                'nota': a.nota,
                'evidencias': a.evidencias
            } for a in alertas],
            'recomendacao': self._gerar_recomendacao(alertas, score, confianca_media)
        }
    
    def calcular_confianca(self, total: int) -> float:
        return 1 - math.exp(-total / 20)
    
    def _gerar_recomendacao(self, alertas: List, score: float, confianca: float) -> str:
        if confianca < 0.4:
            return "Volume insuficiente para analise conclusiva. Coletar mais dados."
        
        if score >= 0.7:
            return "Investigacao prioritária. Sinais de risco significativos."
        elif score >= 0.5:
            return "Revisao detalhada sugerida. Verificar relacoes comerciais."
        elif score >= 0.3:
            return "Monitoramento recomendado. Padroes atipicos detectados."
        return "Padroes dentro da normalidade."

# Teste
if __name__ == '__main__':
    motor = MotorRegras()
    
    print(f"Motor de Regras v{ENGINE_VERSION}")
    print("=" * 60)
    
    # Teste 1: 5 contratos (confianca baixa)
    print("\n=== Teste 1: 5 contratos ===")
    r1 = motor.analisar({
        'orgao': 'Prefeitura Pequena',
        'contratos': [
            {'fornecedor': 'Emp A', 'valor': 50000},
            {'fornecedor': 'Emp A', 'valor': 45000},
            {'fornecedor': 'Emp B', 'valor': 48000},
            {'fornecedor': 'Emp C', 'valor': 52000},
            {'fornecedor': 'Emp D', 'valor': 47000},
        ]
    })
    print(f"Score: {r1['score_risco']} | Conf: {r1['confianca_media']:.2f} | {r1['nivel_risco_geral']}")
    if r1['alertas']:
        print(f"Nota: {r1['alertas'][0]['nota']}")
    
    # Teste 2: 50 contratos (confianca alta)
    print("\n=== Teste 2: 50 contratos ===")
    contratos_50 = [{'fornecedor': 'Emp X', 'valor': 100000} for _ in range(25)]
    contratos_50 += [{'fornecedor': f'Emp {i}', 'valor': 50000} for i in range(25)]
    
    r2 = motor.analisar({
        'orgao': 'Prefeitura Grande',
        'contratos': contratos_50
    })
    print(f"Score: {r2['score_risco']} | Conf: {r2['confianca_media']:.2f} | {r2['nivel_risco_geral']}")
