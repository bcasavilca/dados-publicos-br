#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de validacao de links de portais de dados publicos
Verifica se as URLs estao respondendo corretamente
"""

import requests
import csv
import time
from datetime import datetime

def check_url(url, timeout=10):
    """
    Verifica se a URL esta respondendo
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        r = requests.get(url, timeout=timeout, headers=headers, verify=False)
        return {
            'status_code': r.status_code,
            'ok': r.status_code == 200,
            'response_time': r.elapsed.total_seconds()
        }
    except requests.exceptions.Timeout:
        return {'status_code': 'TIMEOUT', 'ok': False, 'response_time': None}
    except requests.exceptions.ConnectionError:
        return {'status_code': 'CONNECTION_ERROR', 'ok': False, 'response_time': None}
    except Exception as e:
        return {'status_code': f'ERROR: {str(e)[:30]}', 'ok': False, 'response_time': None}

def validate_catalog(csv_file='data/catalogos.csv'):
    """
    Valida todas as URLs no catalogo CSV
    """
    results = []
    
    print("=" * 80)
    print("VALIDACAO DE LINKS - PORTAIS DE DADOS PUBLICOS")
    print("=" * 80)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row['URL']
            titulo = row['Titulo']
            
            print(f"Verificando: {titulo[:50]}")
            print(f"  URL: {url}")
            
            result = check_url(url)
            status = "OK" if result['ok'] else "FALHA"
            
            print(f"  Status: {result['status_code']} ({status})")
            if result['response_time']:
                print(f"  Tempo: {result['response_time']:.2f}s")
            
            results.append({
                'titulo': titulo,
                'url': url,
                'status_code': result['status_code'],
                'ok': result['ok'],
                'response_time': result['response_time']
            })
            
            time.sleep(1)  # Respeitar servidores
            print()
    
    # Resumo
    print("=" * 80)
    print("RESUMO")
    print("=" * 80)
    total = len(results)
    ok = sum(1 for r in results if r['ok'])
    falhas = total - ok
    
    print(f"Total verificado: {total}")
    print(f"OK: {ok} ({ok/total*100:.1f}%)")
    print(f"Falhas: {falhas} ({falhas/total*100:.1f}%)")
    
    # URLs com falha
    if falhas > 0:
        print("\n--- URLs com falha ---")
        for r in results:
            if not r['ok']:
                print(f"  {r['titulo']}: {r['status_code']}")
    
    return results

if __name__ == "__main__":
    # Desabilitar warnings SSL
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    validate_catalog()
