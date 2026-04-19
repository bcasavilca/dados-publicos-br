#!/usr/bin/env python3
"""
API de Integrações ROBUSTA - Dados Públicos BR v2.0
Com: paralelização, timeout, cache, resposta parcial
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import json
from datetime import datetime, timedelta
from functools import lru_cache
import sys
import os

sys.path.append(os.path.dirname(__file__))
from integracoes import IntegradorGeral

app = Flask(__name__)
CORS(app)

integrador = IntegradorGeral()

# Cache simples em memória
cache_dados = {}
CACHE_TTL = 600  # 10 minutos

def get_cache(key):
    """Obtém dados do cache se válido"""
    if key in cache_dados:
        data, timestamp = cache_dados[key]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_TTL):
            return data
    return None

def set_cache(key, data):
    """Armazena dados no cache"""
    cache_dados[key] = (data, datetime.now())

def buscar_com_timeout(func, timeout_sec=5):
    """
    Executa função com timeout
    Retorna (sucesso, dados)
    """
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func)
            return True, future.result(timeout=timeout_sec)
    except Exception as e:
        return False, str(e)

@app.route('/')
def home():
    return jsonify({
        'nome': 'API de Integrações - Dados Públicos BR v2.0',
        'versao': '2.0-robusta',
        'features': [
            'paralelizacao',
            'timeout_por_fonte',
            'cache',
            'resposta_parcial'
        ],
        'endpoints': [
            '/dadosgov/buscar?q=termo',
            '/busca/inteligente?q=termo',
            '/health',
            '/status/fontes'
        ]
    })

@app.route('/health')
def health():
    """Healthcheck rápido"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'cache_size': len(cache_dados)
    })

@app.route('/dadosgov/buscar')
def buscar_dadosgov():
    """
    Busca datasets no dados.gov.br com cache
    """
    termo = request.args.get('q', '')
    orgao = request.args.get('orgao')
    
    if not termo:
        return jsonify({'erro': 'Parâmetro q obrigatório'}), 400
    
    # Cache key
    cache_key = f'dadosgov_{termo}_{orgao}'
    cached = get_cache(cache_key)
    if cached:
        return jsonify({
            'termo': termo,
            'fonte': 'cache',
            'total': len(cached),
            'datasets': cached
        })
    
    # Buscar com timeout
    sucesso, resultado = buscar_com_timeout(
        lambda: integrador.dadosgov.buscar_datasets(termo, orgao),
        timeout_sec=10
    )
    
    if sucesso:
        set_cache(cache_key, resultado)
        return jsonify({
            'termo': termo,
            'fonte': 'api',
            'total': len(resultado),
            'datasets': resultado
        })
    else:
        return jsonify({
            'termo': termo,
            'fonte': 'erro',
            'erro': resultado,
            'datasets': []
        }), 503

@app.route('/busca/inteligente')
def busca_inteligente_robusta():
    """
    Busca em múltiplas fontes com paralelização e resposta parcial
    """
    termo = request.args.get('q', '')
    
    if not termo:
        return jsonify({'erro': 'Parâmetro q obrigatório'}), 400
    
    resultado_final = {
        'termo': termo,
        'timestamp': datetime.now().isoformat(),
        'fontes': {},
        'resultados_agrupados': []
    }
    
    # Definir buscas com timeouts
    buscas = {
        'dadosgov': (lambda: integrador.dadosgov.buscar_datasets(termo), 8),
        'tse': (lambda: integrador.tse.buscar_candidatos(2024), 5),
    }
    
    # Executar em paralelo
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for fonte, (func, timeout) in buscas.items():
            futures[executor.submit(buscar_com_timeout, func, timeout)] = fonte
        
        for future in as_completed(futures):
            fonte = futures[future]
            try:
                sucesso, dados = future.result()
                if sucesso:
                    resultado_final['fontes'][fonte] = {
                        'status': 'ok',
                        'total': len(dados) if isinstance(dados, list) else 1
                    }
                    if isinstance(dados, list):
                        resultado_final['resultados_agrupados'].extend([
                            {'fonte': fonte, 'dados': d} for d in dados[:5]
                        ])
                else:
                    resultado_final['fontes'][fonte] = {
                        'status': 'erro',
                        'erro': dados
                    }
            except Exception as e:
                resultado_final['fontes'][fonte] = {
                    'status': 'erro',
                    'erro': str(e)
                }
    
    resultado_final['total_resultados'] = len(resultado_final['resultados_agrupados'])
    resultado_final['sucesso'] = any(
        f.get('status') == 'ok' for f in resultado_final['fontes'].values()
    )
    
    return jsonify(resultado_final)

@app.route('/status/fontes')
def status_fontes():
    """
    Retorna status de todas as fontes
    """
    fontes = {
        'dadosgov': {'url': 'https://dados.gov.br', 'timeout_padrao': 10},
        'tse': {'url': 'https://dadosabertos.tse.jus.br', 'timeout_padrao': 5},
        'ibge': {'url': 'https://servicodados.ibge.gov.br', 'timeout_padrao': 5},
        'receita': {'url': 'API pública', 'timeout_padrao': 5, 'nota': 'Rate limit aplicável'},
    }
    
    return jsonify({
        'fontes_disponiveis': fontes,
        'cache': {
            'ttl_segundos': CACHE_TTL,
            'entradas_atuais': len(cache_dados)
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    print("=" * 80)
    print("API DE INTEGRAÇÕES ROBUSTA - v2.0")
    print("=" * 80)
    print(f"Porta: {port}")
    print("Features: paralelização | timeout | cache | resposta parcial")
    print("=" * 80)
    app.run(host='0.0.0.0', port=port)
