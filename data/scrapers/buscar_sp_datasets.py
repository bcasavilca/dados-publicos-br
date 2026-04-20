#!/usr/bin/env python3
"""
Busca datasets em São Paulo CKAN
"""

import requests
import json

BASE_URL = 'https://dados.prefeitura.sp.gov.br/api/3/action'

def buscar_por_termo(termo):
    """Busca datasets por termo"""
    url = f'{BASE_URL}/package_search'
    params = {'q': termo, 'rows': 50}
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f'Erro ao buscar {termo}: {e}')
        return None

def listar_todos():
    """Lista todos os datasets"""
    url = f'{BASE_URL}/package_list'
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f'Erro ao listar: {e}')
        return None

def main():
    print('=' * 80)
    print('BUSCA EM SAO PAULO CKAN')
    print('=' * 80)
    
    # Busca por termos específicos
    termos = ['contrato', 'despesa', 'pagamento', 'fornecedor', 'empenho', 'licitacao']
    
    for termo in termos:
        print(f'\nBusca por: {termo}')
        print('-' * 60)
        
        data = buscar_por_termo(termo)
        if data:
            result = data.get('result', {})
            count = result.get('count', 0)
            print(f'Total encontrado: {count}')
            
            for r in result.get('results', [])[:5]:
                print(f' - {r.get("title", "N/A")}')
    
    # Listar todos e filtrar
    print('\n\n' + '=' * 80)
    print('FILTRANDO DATASETS RELEVANTES')
    print('=' * 80)
    
    data = listar_todos()
    if data:
        packages = data.get('result', [])
        print(f'Total de datasets: {len(packages)}')
        
        keywords = ['contrato', 'despesa', 'pagamento', 'fornecedor', 'empenho', 
                   'licitacao', 'compra', 'execucao', 'orcamento']
        
        relevantes = [p for p in packages if any(k in p.lower() for k in keywords)]
        
        print(f'\nRelevantes encontrados: {len(relevantes)}')
        print('\nLista completa:')
        for r in sorted(relevantes):
            print(f' - {r}')

if __name__ == '__main__':
    main()
