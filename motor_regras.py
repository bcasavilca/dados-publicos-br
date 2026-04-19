#!/usr/bin/env python3
"""
Motor de Regras - Detecção de Padrões Suspeitos
Estrutura: dados → regras → sinais (alertas)
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import statistics

@dataclass
class Alerta:
    """Modelo padronizado de alerta"""
    tipo: str
    descricao: str
    nivel_risco: str  # 'baixo', 'medio', 'alto', 'critico'
    score: float      # 0.0 a 1.0
    evidencias: Dict
    fontes: List[str]
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class Regra:
    """Classe base para todas as regras"""
    def analisar(self, dados: Dict) -> Optional[Alerta]:
        """Retorna alerta ou None se não aplicável"""
        raise NotImplementedError

class RegraFornecedorRecorrente(Regra):
    """
    Regra 1: Mesma empresa ganhando muitos contratos
    Alerta se empresa tem > 20% dos contratos do órgão
    """
    def analisar(self, dados: Dict) -> Optional[Alerta]:
        contratos = dados.get('contratos', [])
        if len(contratos) < 5:  # Precisa ter dados suficientes
            return None
        
        # Contar contratos por fornecedor
        fornecedores = {}
        for c in contratos:
            forn = c.get('fornecedor', 'N/A')
            valor = c.get('valor', 0)
            if forn not in fornecedores:
                fornecedores[forn] = {'qtd': 0, 'valor': 0}
            fornecedores[forn]['qtd'] += 1
            fornecedores[forn]['valor'] += valor
        
        total_contratos = len(contratos)
        
        for forn, dados_forn in fornecedores.items():
            percentual = dados_forn['qtd'] / total_contratos
            
            if percentual >= 0.40:  # Aumentado de 20% para 40%
                score = min(percentual * 2, 1.0)  # Score baseado na concentração
                nivel = 'alto' if percentual > 0.40 else 'medio'
                
                return Alerta(
                    tipo='fornecedor_recorrente',
                    descricao=f'{forn} recebeu {dados_forn["qtd"]} contratos ({percentual:.1%})',
                    nivel_risco=nivel,
                    score=round(score, 2),
                    evidencias={
                        'fornecedor': forn,
                        'quantidade_contratos': dados_forn['qtd'],
                        'percentual': round(percentual, 2),
                        'valor_total': dados_forn['valor']
                    },
                    fontes=['Compras.gov.br']
                )
        return None

class RegraValorAnomalo(Regra):
    """
    Regra 2: Valor muito acima da média
    Alerta se contrato é > 3x desvio padrão acima da média
    """
    def analisar(self, dados: Dict) -> Optional[Alerta]:
        contratos = dados.get('contratos', [])
        valores = [c.get('valor', 0) for c in contratos if c.get('valor', 0) > 0]
        
        if len(valores) < 5:
            return None
        
        media = statistics.mean(valores)
        desvio = statistics.stdev(valores) if len(valores) > 1 else 0
        
        for c in contratos:
            valor = c.get('valor', 0)
            if valor > media + (3 * desvio):  # 3 sigma
                score = min((valor / media) / 5, 1.0)  # Normaliza
                return Alerta(
                    tipo='valor_anomalo',
                    descricao=f'Contrato de R$ {valor:,.2f} é {valor/media:.1f}x acima da média',
                    nivel_risco='alto',
                    score=round(score, 2),
                    evidencias={
                        'valor_contrato': valor,
                        'media_orgao': round(media, 2),
                        'desvio_padrao': round(desvio, 2),
                        'fornecedor': c.get('fornecedor', 'N/A')
                    },
                    fontes=['Compras.gov.br']
                )
        return None

class RegraEmpresaNova(Regra):
    """
    Regra 3: Empresa criada recentemente com contratos grandes
    Alerta se empresa tem < 1 ano e recebeu contrato > R$ 100k
    """
    def analisar(self, dados: Dict) -> Optional[Alerta]:
        contratos = dados.get('contratos', [])
        empresas = dados.get('empresas', {})
        
        for c in contratos:
            forn = c.get('fornecedor', '')
            valor = c.get('valor', 0)
            
            info_emp = empresas.get(forn, {})
            data_abertura = info_emp.get('data_abertura')
            
            if data_abertura and valor > 100000:
                # Calcular idade da empresa (simplificado)
                from datetime import datetime
                try:
                    data_emp = datetime.strptime(data_abertura, '%Y-%m-%d')
                    idade_dias = (datetime.now() - data_emp).days
                    
                    if idade_dias < 365:  # Menos de 1 ano
                        score = min(valor / 500000, 1.0)  # Maior valor = maior score
                        return Alerta(
                            tipo='empresa_nova_com_contrato',
                            descricao=f'{forn} tem {idade_dias} dias e recebeu R$ {valor:,.2f}',
                            nivel_risco='critico',
                            score=round(score, 2),
                            evidencias={
                                'fornecedor': forn,
                                'valor_contrato': valor,
                                'dias_desde_abertura': idade_dias,
                                'data_abertura': data_abertura
                            },
                            fontes=['Compras.gov.br', 'Receita Federal']
                        )
                except:
                    pass
        return None

class RegraIncompatibilidadeCNAE(Regra):
    """
    Regra 4: Atividade da empresa não bate com contrato
    Ex: Padaria ganhando contrato de TI
    """
    def analisar(self, dados: Dict) -> Optional[Alerta]:
        contratos = dados.get('contratos', [])
        empresas = dados.get('empresas', {})
        
        incompatibilidades = {
            'TI': ['padaria', 'restaurante', 'comercio'],
            'obra': ['consultoria', 'advocacia'],
            'servico_medico': ['construcao', 'alimentacao']
        }
        
        for c in contratos:
            forn = c.get('fornecedor', '')
            tipo_servico = c.get('tipo_servico', '').lower()
            
            info_emp = empresas.get(forn, {})
            cnae = info_emp.get('cnae', '').lower()
            
            for servico, incompat in incompatibilidades.items():
                if servico in tipo_servico:
                    for palavra in incompat:
                        if palavra in cnae:
                            return Alerta(
                                tipo='incompatibilidade_cnae',
                                descricao=f'{forn} ({cnae}) ganhou contrato de {tipo_servico}',
                                nivel_risco='medio',
                                score=0.6,
                                evidencias={
                                    'fornecedor': forn,
                                    'cnae_principal': cnae,
                                    'tipo_contrato': tipo_servico,
                                    'valor': c.get('valor', 0)
                                },
                                fontes=['Compras.gov.br', 'Receita Federal']
                            )
        return None

class MotorRegras:
    """Orquestrador de todas as regras"""
    
    def __init__(self):
        self.regras = [
            RegraFornecedorRecorrente(),
            RegraValorAnomalo(),
            RegraEmpresaNova(),
            RegraIncompatibilidadeCNAE()
        ]
        
        # Pesos para cálculo de risco total
        self.pesos = {
            'fornecedor_recorrente': 0.6,  # Aumentado de 0.4
            'valor_anomalo': 0.3,
            'empresa_nova_com_contrato': 0.3,
            'incompatibilidade_cnae': 0.2
        }
    
    def analisar(self, dados: Dict) -> Dict:
        """
        Executa todas as regras e retorna resultado completo
        """
        alertas = []
        
        for regra in self.regras:
            alerta = regra.analisar(dados)
            if alerta:
                alertas.append(alerta)
        
        # Calcular score total ponderado
        if alertas:
            score_total = sum(
                a.score * self.pesos.get(a.tipo, 0.1) 
                for a in alertas
            )
            score_total = min(score_total, 1.0)
        else:
            score_total = 0.0
        
        # Determinar nível geral
        if score_total >= 0.7:
            nivel_geral = 'critico'
        elif score_total >= 0.5:
            nivel_geral = 'alto'
        elif score_total >= 0.3:
            nivel_geral = 'medio'
        else:
            nivel_geral = 'baixo'
        
        return {
            'orgao_analisado': dados.get('orgao', 'N/A'),
            'total_alertas': len(alertas),
            'score_risco': round(score_total, 2),
            'nivel_risco_geral': nivel_geral,
            'alertas': [self._alerta_to_dict(a) for a in alertas],
            'recomendacao': self._gerar_recomendacao(alertas, score_total)
        }
    
    def _alerta_to_dict(self, alerta: Alerta) -> Dict:
        return {
            'tipo': alerta.tipo,
            'descricao': alerta.descricao,
            'nivel_risco': alerta.nivel_risco,
            'score': alerta.score,
            'evidencias': alerta.evidencias,
            'fontes': alerta.fontes,
            'timestamp': alerta.timestamp
        }
    
    def _gerar_recomendacao(self, alertas: List[Alerta], score: float) -> str:
        if score >= 0.7:
            return 'Investigação prioritária recomendada. Múltiplos sinais de risco alto.'
        elif score >= 0.5:
            return 'Revisão detalhada sugerida. Verificar relações comerciais.'
        elif score >= 0.3:
            return 'Monitoramento recomendado. Padronização atípica detectada.'
        else:
            return 'Nenhuma ação imediata necessária. Padrões dentro da normalidade.'

# Exemplo de uso
if __name__ == '__main__':
    motor = MotorRegras()
    
    # Dados de exemplo
    dados_teste = {
        'orgao': 'Prefeitura de Exemplo',
        'contratos': [
            {'fornecedor': 'Empresa X', 'valor': 500000, 'tipo_servico': 'TI'},
            {'fornecedor': 'Empresa X', 'valor': 450000, 'tipo_servico': 'TI'},
            {'fornecedor': 'Empresa X', 'valor': 600000, 'tipo_servico': 'TI'},
            {'fornecedor': 'Empresa Y', 'valor': 50000, 'tipo_servico': 'limpeza'},
            {'fornecedor': 'Empresa Z', 'valor': 30000, 'tipo_servico': 'manutencao'},
        ],
        'empresas': {
            'Empresa X': {'data_abertura': '2024-01-15', 'cnae': 'Padaria e confeitaria'},
        }
    }
    
    resultado = motor.analisar(dados_teste)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
