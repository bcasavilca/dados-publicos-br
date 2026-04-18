#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detector automatico de portais CKAN
Identifica se um portal usa a plataforma CKAN para dados abertos
"""

import requests
import json

def is_ckan(url):
    """
    Verifica se a URL e um portal CKAN
    Tenta acessar a API CKAN padrao
    """
    try:
        # Limpar URL
        url = url.rstrip('/')
        
        # Endpoints CKAN comuns
        endpoints = [
            "/api/3/action/site_read",
            "/api/3/action/package_list",
            "/api/action/package_search?rows=1"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        for endpoint in endpoints:
            try:
                r = requests.get(url + endpoint, timeout=10, headers=headers)
                if r.status_code == 200:
                    # Verificar se retorna JSON valido
                    try:
                        data = r.json()
                        if 'success' in data or 'result' in data:
                            return True
                    except:
                        pass
            except:
                continue
        
        return False
    except Exception as e:
        return False

def detect_ckan_version(url):
    """
    Tenta detectar a versao do CKAN
    """
    try:
        url = url.rstrip('/')
        r = requests.get(url + "/api/util/status", timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get('ckan_version', 'desconhecida')
    except:
        pass
    return 'desconhecida'

def get_ckan_info(url):
    """
    Obtem informacoes basicas do portal CKAN
    """
    try:
        url = url.rstrip('/')
        
        # Tentar obter lista de datasets
        r = requests.get(url + "/api/3/action/package_search?rows=1", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get('success'):
                count = data['result'].get('count', 0)
                return {
                    'is_ckan': True,
                    'datasets': count,
                    'version': detect_ckan_version(url)
                }
    except:
        pass
    
    return {'is_ckan': False}

if __name__ == "__main__":
    # Lista de portais para testar
    urls = [
        "http://dados.al.gov.br",
        "http://dados.gov.br",
        "https://dados.rs.gov.br",
        "https://data.rio",
        "https://dados.mg.gov.br",
        "http://dados.fortaleza.ce.gov.br",
        "https://transparencia.fortaleza.ce.gov.br"  # Nao e CKAN
    ]
    
    print("=" * 80)
    print("DETECTOR DE PORTAIS CKAN")
    print("=" * 80)
    
    for url in urls:
        print(f"\nVerificando: {url}")
        
        info = get_ckan_info(url)
        
        if info['is_ckan']:
            print(f"  ✅ CKAN detectado!")
            print(f"  📊 Datasets: {info['datasets']}")
            print(f"  🔧 Versao: {info['version']}")
        else:
            print(f"  ❌ Nao e CKAN")
            # Verificar se responde de qualquer forma
            try:
                r = requests.get(url, timeout=5)
                print(f"  📡 Status: HTTP {r.status_code}")
            except Exception as e:
                print(f"  ⚠️  Erro: {str(e)[:50]}")
