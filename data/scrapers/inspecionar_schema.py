#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspeciona schema do dataset de contratos de SP
"""

import requests
import json

def main():
    dataset = 'base-de-compras-e-licitacoes'
    url = 'https://dados.prefeitura.sp.gov.br/api/3/action/package_show'
    
    print('Buscando detalhes do dataset...')
    resp = requests.get(url, params={'id': dataset}, timeout=30)
    data = resp.json()
    
    result = data.get('result', {})
    
    print('=' * 80)
    print('DETALHES DO DATASET: Base de Compras e Licitacoes')
    print('=' * 80)
    print()
    print('Titulo:', result.get('title', 'N/A'))
    print('Descricao:', result.get('notes', 'N/A')[:200] if result.get('notes') else 'N/A')
    print()
    
    resources = result.get('resources', [])
    print('Total de recursos:', len(resources))
    print()
    
    # Mostrar apenas recursos CSV de 2024
    print('RECURSOS CSV RECENTES:')
    print('-' * 80)
    
    csv_resources = [r for r in resources if r.get('format', '').upper() == 'CSV']
    
    for i, r in enumerate(csv_resources[:3], 1):
        print(f'{i}. {r.get("name", "N/A")}')
        print('   URL:', r.get('url', 'N/A'))
        print('   Tamanho:', r.get('size', 'N/A'), 'bytes')
        print('   Ultima modificacao:', r.get('last_modified', 'N/A'))
        
        # Verificar schema
        if r.get('fields'):
            print(f'   CAMPOS ({len(r.get("fields", []))}):')
            for field in r['fields'][:15]:
                print(f'     - {field.get("id", "N/A")}: {field.get("type", "N/A")}')
        else:
            print('   Nota: Schema nao disponivel via CKAN - necessario baixar CSV e inspecionar')
        print()
    
    print('=' * 80)
    print('PROXIMA ETAPA:')
    print('- Baixar CSV de 2024')
    print('- Inspecionar colunas manualmente')
    print('- Validar presenca de: fornecedor, valor, data')
    print('=' * 80)

if __name__ == '__main__':
    main()
