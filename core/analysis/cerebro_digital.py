#!/usr/bin/env python3
"""
Cerebro Digital - Análise de Dados Públicos para Transparência
Inspirado no projeto de Bruno César

Funcionalidades:
- Cruzamento de CPF/CNPJ em fornecedores
- Análise de patrimônio e evolução patrimonial
- Detecção de vínculos familiares em licitações
- Integração com APIs públicas (CEP, CNPJ, etc.)
"""

import requests
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class Pessoa:
    """Representa uma pessoa física ou jurídica"""
    nome: str
    documento: str  # CPF ou CNPJ
    tipo: str  # 'PF' ou 'PJ'
    
    # Dados enriquecidos
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None
    
    # Dados de risco
    quantidade_contratos: int = 0
    valor_total: float = 0.0
    score_risco: int = 0
    
    # Vínculos
    socios: List[str] = None
    parentes: List[str] = None
    
    def __post_init__(self):
        if self.socios is None:
            self.socios = []
        if self.parentes is None:
            self.parentes = []

class CerebroDigital:
    """
    Motor de análise para detecção de padrões em dados públicos
    """
    
    def __init__(self):
        self.cache = {}
        self.pessoas: Dict[str, Pessoa] = {}
        self.alertas = []
        
    def limpar_documento(self, doc: str) -> str:
        """Remove caracteres não numéricos do CPF/CNPJ"""
        return re.sub(r'[^\d]', '', doc)
    
    def validar_cpf(self, cpf: str) -> bool:
        """Valida CPF básico"""
        cpf = self.limpar_documento(cpf)
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        
        # Cálculo de dígitos verificadores
        for i in range(9, 11):
            value = sum(int(cpf[num]) * ((i+1) - num) for num in range(0, i))
            digit = 11 - (value % 11)
            if digit > 9:
                digit = 0
            if digit != int(cpf[i]):
                return False
        return True
    
    def validar_cnpj(self, cnpj: str) -> bool:
        """Valida CNPJ básico"""
        cnpj = self.limpar_documento(cnpj)
        if len(cnpj) != 14:
            return False
        
        # Remove CNPJs inválidos conhecidos
        if cnpj in ['00000000000000', '11111111111111', '22222222222222',
                    '33333333333333', '44444444444444', '55555555555555',
                    '66666666666666', '77777777777777', '88888888888888',
                    '99999999999999']:
            return False
        
        return True
    
    def detectar_parentesco(self, nome1: str, nome2: str) -> float:
        """
        Detecta possível parentesco entre nomes
        Retorna score de 0 a 1
        """
        # Sobrenomes em comum
        sobrenomes1 = set(nome1.upper().split())
        sobrenomes2 = set(nome2.upper().split())
        
        intersecao = sobrenomes1.intersection(sobrenomes2)
        
        # Score baseado em quantidade de sobrenomes iguais
        if len(intersecao) >= 2:
            return 0.8  # Alta probabilidade de parentesco
        elif len(intersecao) == 1:
            # Verificar se é sobrenome raro
            sobrenome = list(intersecao)[0]
            if len(sobrenome) > 4:  # Evitar nomes muito comuns
                return 0.5
        
        return 0.0
    
    def analisar_fornecedor(self, nome: str, documento: str, 
                           valor_contratos: float = 0,
                           orgaos: List[str] = None) -> Pessoa:
        """
        Analisa um fornecedor e calcula score de risco
        """
        doc_limpo = self.limpar_documento(documento)
        
        # Verificar se já existe
        if doc_limpo in self.pessoas:
            pessoa = self.pessoas[doc_limpo]
            pessoa.quantidade_contratos += 1
            pessoa.valor_total += valor_contratos
        else:
            tipo = 'PJ' if len(doc_limpo) == 14 else 'PF'
            pessoa = Pessoa(
                nome=nome,
                documento=documento,
                tipo=tipo,
                quantidade_contratos=1,
                valor_total=valor_contratos
            )
            self.pessoas[doc_limpo] = pessoa
        
        # Adicionar órgãos
        if orgaos:
            for orgao in orgaos:
                if orgao not in pessoa.parentes:  # Reutilizando campo para órgãos
                    pessoa.parentes.append(orgao)
        
        # Calcular score de risco
        self._calcular_score_risco(pessoa)
        
        return pessoa
    
    def _calcular_score_risco(self, pessoa: Pessoa):
        """
        Calcula score de risco baseado em múltiplos fatores
        """
        score = 0
        alertas = []
        
        # Fator 1: Quantidade de contratos
        if pessoa.quantidade_contratos >= 20:
            score += 30
            alertas.append("FORNECEDOR_FREQUENTE")
        elif pessoa.quantidade_contratos >= 10:
            score += 15
            alertas.append("FORNECEDOR_RECORRENTE")
        
        # Fator 2: Valor total
        if pessoa.valor_total >= 10_000_000:  # R$ 10 milhões
            score += 25
            alertas.append("VALOR_ELEVADO")
        elif pessoa.valor_total >= 1_000_000:  # R$ 1 milhão
            score += 10
            alertas.append("VALOR_SIGNIFICATIVO")
        
        # Fator 3: Presença em múltiplos órgãos
        orgaos_unicos = len(set(pessoa.parentes))
        if orgaos_unicos >= 5:
            score += 20
            alertas.append("MULTIPLOS_ORGAOS")
        elif orgaos_unicos >= 3:
            score += 10
            alertas.append("PRESENCA_AMPLIADA")
        
        # Fator 4: Pessoa física com valor elevado
        if pessoa.tipo == 'PF' and pessoa.valor_total >= 500_000:
            score += 15
            alertas.append("PF_VALOR_ELEVADO")
        
        pessoa.score_risco = min(score, 100)
        
        # Gerar alerta se score alto
        if pessoa.score_risco >= 50:
            self._gerar_alerta(pessoa, alertas)
    
    def _gerar_alerta(self, pessoa: Pessoa, motivos: List[str]):
        """Gera alerta para investigação"""
        alerta = {
            'tipo': 'FORNECEDOR_RISCO',
            'nome': pessoa.nome,
            'documento': pessoa.documento,
            'score': pessoa.score_risco,
            'motivos': motivos,
            'quantidade_contratos': pessoa.quantidade_contratos,
            'valor_total': pessoa.valor_total,
            'gerado_em': datetime.now().isoformat()
        }
        self.alertas.append(alerta)
    
    def cruzar_documentos(self, doc1: str, doc2: str) -> Dict:
        """
        Compara dois documentos buscando vínculos
        """
        doc1_limpo = self.limpar_documento(doc1)
        doc2_limpo = self.limpar_documento(doc2)
        
        resultado = {
            'doc1': doc1_limpo,
            'doc2': doc2_limpo,
            'vinculos_encontrados': [],
            'score_vinculo': 0
        }
        
        # Verificar se são do mesmo endereço
        if doc1_limpo in self.pessoas and doc2_limpo in self.pessoas:
            p1 = self.pessoas[doc1_limpo]
            p2 = self.pessoas[doc2_limpo]
            
            # Mesmo endereço
            if p1.cep and p1.cep == p2.cep:
                resultado['vinculos_encontrados'].append('MESMO_CEP')
                resultado['score_vinculo'] += 0.3
            
            # Mesma cidade
            if p1.cidade and p1.cidade == p2.cidade:
                resultado['vinculos_encontrados'].append('MESMA_CIDADE')
                resultado['score_vinculo'] += 0.1
            
            # Nomes similares (parentesco)
            parentesco = self.detectar_parentesco(p1.nome, p2.nome)
            if parentesco > 0:
                resultado['vinculos_encontrados'].append('POSSIVEL_PARENTESCO')
                resultado['score_vinculo'] += parentesco
        
        return resultado
    
    def buscar_receita_ws(self, cnpj: str) -> Optional[Dict]:
        """
        Busca dados da Receita Federal via API pública
        """
        cnpj_limpo = self.limpar_documento(cnpj)
        
        # API pública gratuita (exemplo)
        url = f"https://www.receitaws.com.br/v1/cnpj/{cnpj_limpo}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return None
    
    def gerar_relatorio(self) -> Dict:
        """
        Gera relatório completo de análise
        """
        total_pessoas = len(self.pessoas)
        pessoas_fisicas = len([p for p in self.pessoas.values() if p.tipo == 'PF'])
        pessoas_juridicas = len([p for p in self.pessoas.values() if p.tipo == 'PJ'])
        
        # Top fornecedores por valor
        top_fornecedores = sorted(
            self.pessoas.values(),
            key=lambda x: x.valor_total,
            reverse=True
        )[:10]
        
        # Alertas críticos
        alertas_criticos = [a for a in self.alertas if a['score'] >= 70]
        
        return {
            'resumo': {
                'total_pessoas_analisadas': total_pessoas,
                'pessoas_fisicas': pessoas_fisicas,
                'pessoas_juridicas': pessoas_juridicas,
                'total_alertas': len(self.alertas),
                'alertas_criticos': len(alertas_criticos)
            },
            'top_fornecedores': [
                {
                    'nome': p.nome,
                    'documento': p.documento,
                    'valor_total': p.valor_total,
                    'contratos': p.quantidade_contratos,
                    'score_risco': p.score_risco
                }
                for p in top_fornecedores
            ],
            'alertas': self.alertas
        }


if __name__ == "__main__":
    print("=" * 80)
    print("CEREBRO DIGITAL - ANÁLISE DE DADOS PÚBLICOS")
    print("=" * 80)
    
    cerebro = CerebroDigital()
    
    # Exemplo de uso
    print("\n[Exemplo] Analisando fornecedores fictícios...")
    
    # Simular dados de contratos
    cerebro.analisar_fornecedor(
        "CONSTRUTORA XYZ LTDA",
        "12.345.678/0001-90",
        5_500_000,
        ["Prefeitura de São Paulo", "Prefeitura de Campinas", "Governo de SP"]
    )
    
    cerebro.analisar_fornecedor(
        "COMERCIO ABC ME",
        "98.765.432/0001-10",
        800_000,
        ["Prefeitura de São Paulo"]
    )
    
    cerebro.analisar_fornecedor(
        "JOSE SILVA SERVICOS",
        "123.456.789-00",
        1_200_000,
        ["Câmara Municipal", "Prefeitura de Santos", "Governo de SP", "TCE", "TCM"]
    )
    
    # Gerar relatório
    print("\n[Relatório Gerado]")
    relatorio = cerebro.gerar_relatorio()
    
    print(f"\nTotal analisado: {relatorio['resumo']['total_pessoas_analisadas']}")
    print(f"Pessoas Jurídicas: {relatorio['resumo']['pessoas_juridicas']}")
    print(f"Pessoas Físicas: {relatorio['resumo']['pessoas_fisicas']}")
    print(f"Alertas gerados: {relatorio['resumo']['total_alertas']}")
    
    print("\n[Top Fornecedores por Valor]")
    for i, f in enumerate(relatorio['top_fornecedores'], 1):
        print(f"{i}. {f['nome'][:40]:40} | R$ {f['valor_total']:>15,.0f} | Score: {f['score_risco']}")
    
    print("\n[Alertas de Risco]")
    for alerta in relatorio['alertas']:
        print(f"⚠️  {alerta['nome'][:30]:30} | Score: {alerta['score']} | Motivos: {', '.join(alerta['motivos'])}")
    
    print("\n" + "=" * 80)
    print("Sistema pronto para análise de dados reais!")
    print("=" * 80)
