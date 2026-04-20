#!/usr/bin/env python3
"""
Inspeciona dataset especifico de Sao Paulo
"""

import requests

BASE_URL = 'https://dados.prefeitura.sp.gov.br/api/3/action'

def inspecionar_dataset(name):
    """Busca detalhes de um dataset"""
    url = f'{BASE_URL}/package_show'
    params = {'id': name}
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f'Erro: {e}')
        return None

def main():
    # Dataset recomendado
    dataset_name = 'base-de-compras-e-licitacoes'
    
    print('=' * 80)
    print(f'INSPECAO: {dataset_name}')
    print('=' * 80)
    
    data = inspecionar_dataset(dataset_name)
    if not data:
        print('Dataset nao encontrado ou erro na API')
        return
    
    result = data.get('result', {})
    
    print(f"\nTitulo: {result.get('title', 'N/A')}")
    print(f"Nome: {result.get('name', 'N/A')}")
    print(f"Descricao: {result.get('notes', 'N/A')[:300]}...")
    print(f"\nTags: {[t.get('name') for t in result.get('tags', [])]}")
    print(f"Grupos: {[g.get('title') for g in result.get('groups', [])]}")
    
    print(f"\nRecursos disponiveis: {len(result.get('resources', []))}")
    print('\n' + '-' * 80)
    
    for i, resource in enumerate(result.get('resources', []), 1):
        print(f"\nRecurso {i}:")
        print(f"  Nome: {resource.get('name', 'N/A')}")
        print(f"  Formato: {resource.get('format', 'N/A')}")
        print(f"  URL: {resource.get('url', 'N/A')}")
        print(f"  Tamanho: {resource.get('size', 'N/A')} bytes")
        print(f"  Ultima atualizacao: {resource.get('last_modified', 'N/A')}")
        
        # Campos do recurso (se disponivel)
        if resource.get('fields'):
            print(f"  Campos: {len(resource.get('fields', []))}")
            for field in resource.get('fields', [])[:10]:
                print(f"    - {field.get('id', 'N/A')}: {field.get('type', 'N/A')}")
    
    print('\n' + '=' * 80)
    
    # Avaliacao rapida
    print('\nAVALIACAO RAPIDA:')
    print('-' * 40)
    
    resources = result.get('resources', [])
    if not resources:
        print('❌ Nenhum recurso disponivel')
        return
    
    # Verificar formatos
    formatos = [r.get('format', '').upper() for r in resources]
    
    if 'CSV' in formatos:
        print('✅ CSV disponivel - formato ideal')
    elif 'JSON' in formatos:
        print('✅ JSON disponivel - formato OK')
    else:
        print(f'⚠️ Formatos encontrados: {formatos}')
    
    # Verificar atualizacao
    last_mod = resources[0].get('last_modified', '')
    if last_mod:
        print(f'✅ Ultima atualizacao: {last_mod}')
    else:
        print('⚠️ Data de atualizacao nao informada')

if __name__ == '__main__':
    main()
