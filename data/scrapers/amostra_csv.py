#!/usr/bin/env python3
"""
Inspeciona amostra do CSV antes de download completo
"""

import requests

def inspecionar_amostra(url, nome):
    """Baixa apenas primeiras linhas do CSV"""
    print(f'Inspecionando: {nome}')
    print(f'URL: {url}')
    print('-' * 80)
    
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        
        lines = []
        for i, line in enumerate(r.iter_lines()):
            if i >= 20:  # Apenas 20 primeiras linhas
                break
            lines.append(line.decode('utf-8', errors='ignore'))
        
        print(f'Amostra obtida: {len(lines)} linhas')
        print()
        
        # Mostrar linhas
        for i, line in enumerate(lines, 1):
            print(f'{i:2d}: {line}')
            
        return lines
        
    except Exception as e:
        print(f'Erro: {e}')
        return None

def analisar_schema(lines):
    """Analisa headers do CSV"""
    if not lines:
        return None
    
    headers = lines[0].split(',')
    
    print('\n' + '=' * 80)
    print('ANALISE DE SCHEMA')
    print('=' * 80)
    
    print(f'Total de colunas: {len(headers)}')
    print('\nColunas encontradas:')
    for i, h in enumerate(headers, 1):
        print(f'  {i:2d}. {h.strip()}')
    
    # Buscar campos importantes
    headers_lower = [h.lower().strip() for h in headers]
    
    campos_fornecedor = ['fornecedor', 'razao_social', 'credor', 'empresa', 'contratado']
    campos_valor = ['valor', 'valor_total', 'valor_contrato', 'valor_homologado']
    campos_data = ['data', 'data_contrato', 'data_assinatura', 'data_inicio', 'data_publicacao']
    
    print('\n' + '-' * 80)
    print('BUSCA POR CAMPOS ESSENCIAIS:')
    print('-' * 80)
    
    # Fornecedor
    print('\n1. FORNECEDOR:')
    encontrado = False
    for campo in campos_fornecedor:
        matches = [h for h in headers_lower if campo in h]
        if matches:
            print(f'   ✅ {matches}')
            encontrado = True
    if not encontrado:
        print('   ❌ NAO ENCONTRADO')
    
    # Valor
    print('\n2. VALOR:')
    encontrado = False
    for campo in campos_valor:
        matches = [h for h in headers_lower if campo in h]
        if matches:
            print(f'   ✅ {matches}')
            encontrado = True
    if not encontrado:
        print('   ❌ NAO ENCONTRADO')
    
    # Data
    print('\n3. DATA:')
    encontrado = False
    for campo in campos_data:
        matches = [h for h in headers_lower if campo in h]
        if matches:
            print(f'   ✅ {matches}')
            encontrado = True
    if not encontrado:
        print('   ❌ NAO ENCONTRADO')
    
    return headers

def main():
    # CSV de 2024
    url = 'https://dados.prefeitura.sp.gov.br/dataset/6588aef7-20ff-4cec-b1e1-6c06520240c0/resource/fd48b7dd-c5f1-4352-963f-f1e5ebc6d61b/download/contratos.csv'
    
    print('=' * 80)
    print('AMOSTRAGEM INTELIGENTE - Base de Compras SP 2024')
    print('=' * 80)
    print()
    
    lines = inspecionar_amostra(url, 'Contratos 2024')
    
    if lines:
        analisar_schema(lines)
        
        print('\n' + '=' * 80)
        print('DECISAO:')
        print('=' * 80)
        print('Se os 3 campos essenciais foram encontrados:')
        print('  -> APROVADO para baseline')
        print('Se faltou algum:')
        print('  -> REPROVADO - buscar outro dataset')
        print('=' * 80)

if __name__ == '__main__':
    main()
