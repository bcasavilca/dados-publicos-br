#!/usr/bin/env python3
"""
Cruzador de Dados - Detecta padrões suspeitos
Cruza: TSE (candidatos) + Compras (contratos) + Receita (empresas)
"""

import requests
import json
from datetime import datetime

class CruzadorDados:
    """Cruza dados de múltiplas fontes para detectar anomalias"""
    
    def __init__(self):
        self.resultados = []
    
    def buscar_candidatos_tse(self, ano=2022, cargo='deputado_federal'):
        """Busca candidatos do TSE"""
        try:
            url = f'https://dadosabertos.tse.jus.br/api/3/action/candidatos_{ano}_{cargo}'
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.json().get('result', [])
        except:
            pass
        return []
    
    def buscar_empresas_receita(self, cnpj):
        """Busca dados de empresa na Receita"""
        try:
            url = f'https://receitaws.com.br/v1/cnpj/{cnpj}'
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {}
    
    def analisar_contratos(self, orgao):
        """Analisa contratos de um órgão"""
        # Placeholder - dados.gov.br/compras
        return {
            'orgao': orgao,
            'total_contratos': 0,
            'fornecedores_repetidos': [],
            'valores_anomalos': []
        }
    
    def detectar_padroes_suspeitos(self, contratos, candidatos):
        """Detecta padrões suspeitos"""
        alertas = []
        
        # Padrão 1: Mesma empresa ganha vários contratos
        fornecedores = {}
        for c in contratos:
            forn = c.get('fornecedor', 'N/A')
            fornecedores[forn] = fornecedores.get(forn, 0) + 1
        
        for forn, qtd in fornecedores.items():
            if qtd > 3:
                alertas.append({
                    'tipo': 'fornecedor_repetido',
                    'descricao': f'Empresa {forn} ganhou {qtd} contratos',
                    'gravidade': 'media'
                })
        
        # Padrão 2: Valores muito acima da média
        valores = [c.get('valor', 0) for c in contratos if c.get('valor', 0) > 0]
        if valores:
            media = sum(valores) / len(valores)
            for c in contratos:
                if c.get('valor', 0) > media * 5:
                    alertas.append({
                        'tipo': 'valor_anomalo',
                        'descricao': f'Contrato R$ {c.get("valor"):,.2f} (média: R$ {media:,.2f})',
                        'gravidade': 'alta'
                    })
        
        return alertas

if __name__ == '__main__':
    c = CruzadorDados()
    print("Cruzador pronto para uso!")
