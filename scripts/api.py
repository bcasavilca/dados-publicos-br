#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API REST para consulta ao catalogo de dados publicos brasileiros v2.1
- Com cache, healthcheck e métricas
- Deploy ready para Render/Railway
- INTEGRACAO com dados.gov.br

Endpoints:
  - /                  Info da API
  - /health            Healthcheck (para Render)
  - /metrics           Métricas da API
  - /catalogo          Lista todos os catalogos
  - /catalogo/{uf}     Filtra por UF
  - /catalogo/qualidade/{nivel}  Filtra por qualidade
  - /catalogo/categoria/{cat}    Filtra por categoria
  - /buscar?q={termo}  Busca tipo Google (HIBRIDA: portais + datasets)
  - /datasets?q={termo}  Busca datasets reais no dados.gov.br
  - /ranking           Ranking por qualidade
  - /estatisticas      Estatisticas gerais
  - /estados           Lista estados disponiveis
"""

from flask import Flask, jsonify, request
from flask_caching import Cache
from flask_cors import CORS
from functools import lru_cache
import pandas as pd
import os
import time
from datetime import datetime
import sys

# Adicionar path para importar modulo de integracao
sys.path.append(os.path.dirname(__file__))
from dadosgov_integration import DadosGovClient, search_hibrido

app = Flask(__name__)

# Habilitar CORS para permitir acesso do frontend
CORS(app, origins=['*'])

# Configuracao de cache
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5 minutos
cache = Cache(app)

# Caminho do arquivo CSV
CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'catalogos.csv')

# Inicio da aplicacao (para uptime)
START_TIME = time.time()

@lru_cache(maxsize=1)
def load_data():
    """Carrega dados do CSV com cache"""
    try:
        df = pd.read_csv(CSV_PATH)
        print(f"[INFO] Dados carregados: {len(df)} portais")
        return df
    except Exception as e:
        print(f"[ERRO] Ao carregar dados: {e}")
        return pd.DataFrame()

def get_uptime():
    """Retorna uptime da aplicacao"""
    uptime = time.time() - START_TIME
    return {
        'seconds': int(uptime),
        'minutes': int(uptime / 60),
        'hours': round(uptime / 3600, 2)
    }

@app.route('/')
def index():
    """Endpoint raiz com informacoes da API"""
    df = load_data()
    return jsonify({
        'nome': 'Dados Publicos BR API',
        'versao': '2.1.0',
        'descricao': 'API de consulta a portais de dados publicos brasileiros',
        'status': 'online',
        'uptime': get_uptime(),
        'timestamp': datetime.now().isoformat(),
        'total_portais': len(df),
        'endpoints': {
            'info': '/',
            'health': '/health - Healthcheck',
            'metrics': '/metrics - Métricas',
            'catalogo': '/catalogo - Lista todos',
            'buscar': '/buscar?q={termo} - Busca livre',
            'ranking': '/ranking - Ranking qualidade',
            'estatisticas': '/estatisticas - Dados agregados'
        }
    })

@app.route('/health')
def health():
    """Healthcheck para Render/Railway"""
    try:
        df = load_data()
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'uptime': get_uptime(),
            'total_portais': len(df),
            'data_loaded': not df.empty
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/metrics')
def metrics():
    """Métricas da API"""
    df = load_data()
    
    if df.empty:
        return jsonify({'error': 'Dados nao carregados'}), 500
    
    # Métricas calculadas
    stats = {
        'timestamp': datetime.now().isoformat(),
        'uptime': get_uptime(),
        'total_portais': len(df),
        'ufs_cobertas': int(df['UF'].nunique()),
        'categorias': int(df['Categoria'].nunique()),
        'qualidade': {
            'alta': int((df['Qualidade'] == 'Alta').sum()),
            'media': int((df['Qualidade'] == 'Media').sum()),
            'baixa': int((df['Qualidade'] == 'Baixa').sum())
        },
        'por_esfera': df['Esfera'].value_counts().to_dict(),
        'top_uf': df['UF'].value_counts().head(5).to_dict(),
        'api_hits': {
            'portais_ckan': int((df['TipoAcesso'] == 'API/Download').sum()),
            'portais_scraping': int((df['TipoAcesso'] == 'Scraping').sum())
        }
    }
    
    return jsonify(stats)

@app.route('/catalogo')
@cache.cached(timeout=300)
def catalogo():
    """Lista todos os portais catalogados com filtros"""
    df = load_data()
    
    # Filtros opcionais via query string
    uf = request.args.get('uf')
    qualidade = request.args.get('qualidade')
    categoria = request.args.get('categoria')
    esfera = request.args.get('esfera')
    
    filtered_df = df.copy()
    
    if uf:
        filtered_df = filtered_df[filtered_df['UF'].str.upper() == uf.upper()]
    if qualidade:
        filtered_df = filtered_df[filtered_df['Qualidade'].str.lower() == qualidade.lower()]
    if categoria:
        filtered_df = filtered_df[filtered_df['Categoria'].str.lower() == categoria.lower()]
    if esfera:
        filtered_df = filtered_df[filtered_df['Esfera'].str.lower() == esfera.lower()]
    
    return jsonify({
        'total': len(filtered_df),
        'filtros': {k: v for k, v in {
            'uf': uf,
            'qualidade': qualidade,
            'categoria': categoria,
            'esfera': esfera
        }.items() if v},
        'resultados': filtered_df.to_dict(orient='records')
    })

@app.route('/catalogo/uf/<uf>')
@cache.cached(timeout=300)
def catalogo_uf(uf):
    """Filtra portais por UF"""
    df = load_data()
    filtered = df[df['UF'].str.upper() == uf.upper()]
    
    return jsonify({
        'uf': uf.upper(),
        'total': len(filtered),
        'portais': filtered.to_dict(orient='records')
    })

@app.route('/catalogo/qualidade/<nivel>')
@cache.cached(timeout=300)
def catalogo_qualidade(nivel):
    """Filtra portais por nivel de qualidade"""
    df = load_data()
    filtered = df[df['Qualidade'].str.lower() == nivel.lower()]
    
    return jsonify({
        'qualidade': nivel.capitalize(),
        'total': len(filtered),
        'portais': filtered.to_dict(orient='records')
    })

@app.route('/catalogo/categoria/<cat>')
@cache.cached(timeout=300)
def catalogo_categoria(cat):
    """Filtra portais por categoria tematica"""
    df = load_data()
    filtered = df[df['Categoria'].str.lower() == cat.lower()]
    
    return jsonify({
        'categoria': cat.capitalize(),
        'total': len(filtered),
        'portais': filtered.to_dict(orient='records')
    })

@app.route('/buscar')
def buscar():
    """Busca tipo Google em todos os campos"""
    q = request.args.get('q', '').lower()
    
    if not q or len(q) < 2:
        return jsonify({
            'erro': 'Termo de busca muito curto (min 2 caracteres)',
            'busca': q
        }), 400
    
    df = load_data()
    
    # Busca em todas as colunas
    mask = df.apply(
        lambda row: any(q in str(val).lower() for val in row), 
        axis=1
    )
    results = df[mask]
    
    return jsonify({
        'busca': q,
        'total_resultados': len(results),
        'resultados': results.to_dict(orient='records')
    })

@app.route('/ranking')
@cache.cached(timeout=300)
def ranking():
    """Ranking dos melhores portais por qualidade"""
    df = load_data()
    
    # Ordenar por qualidade (Alta > Media > Baixa)
    qualidade_order = {'Alta': 3, 'Media': 2, 'Baixa': 1}
    df_sorted = df.copy()
    df_sorted['qualidade_num'] = df_sorted['Qualidade'].map(qualidade_order)
    df_sorted = df_sorted.sort_values(['qualidade_num', 'UF'], ascending=[False, True])
    
    # Agrupar por qualidade
    ranking_data = {
        'alta': df_sorted[df_sorted['Qualidade'] == 'Alta'].to_dict(orient='records'),
        'media': df_sorted[df_sorted['Qualidade'] == 'Media'].to_dict(orient='records'),
        'baixa': df_sorted[df_sorted['Qualidade'] == 'Baixa'].to_dict(orient='records')
    }
    
    return jsonify({
        'total_portais': len(df),
        'ranking': ranking_data,
        'melhores_uf': df[df['Qualidade'] == 'Alta']['UF'].value_counts().head(5).to_dict(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/estados')
@cache.cached(timeout=300)
def estados():
    """Lista estados/UFs disponiveis no catalogo"""
    df = load_data()
    estados_list = df['UF'].unique().tolist()
    
    # Contagem por estado
    counts = df['UF'].value_counts().to_dict()
    
    return jsonify({
        'total_estados': len(estados_list),
        'estados': sorted(estados_list),
        'por_estado': counts
    })

@app.route('/estatisticas')
@cache.cached(timeout=300)
def estatisticas():
    """Estatisticas gerais do catalogo"""
    df = load_data()
    
    stats = {
        'timestamp': datetime.now().isoformat(),
        'total_portais': len(df),
        'por_uf': df['UF'].value_counts().to_dict(),
        'por_esfera': df['Esfera'].value_counts().to_dict(),
        'por_poder': df['Poder'].value_counts().to_dict(),
        'por_qualidade': df['Qualidade'].value_counts().to_dict(),
        'por_tipo_fonte': df['TipoFonte'].value_counts().to_dict(),
        'por_categoria': df['Categoria'].value_counts().to_dict(),
        'por_tipo_acesso': df['TipoAcesso'].value_counts().to_dict(),
        'melhores_portais': df[df['Qualidade'] == 'Alta']['Titulo'].tolist()[:10],
        'uptime': get_uptime()
    }
    
    return jsonify(stats)

@app.route('/datasets')
def datasets():
    """
    Busca datasets reais no dados.gov.br
    """
    q = request.args.get('q', '')
    rows = request.args.get('rows', 20, type=int)
    
    client = DadosGovClient()
    
    if q:
        results = client.search_datasets(query=q, rows=rows)
    else:
        results = client.get_popular_datasets(rows=rows)
    
    return jsonify({
        'termo': q,
        'total': len(results),
        'datasets': results
    })

@app.route('/buscar')
def buscar():
    """
    BUSCA HIBRIDA: portais locais + datasets do dados.gov.br
    """
    q = request.args.get('q', '').lower()
    
    if not q or len(q) < 2:
        return jsonify({
            'erro': 'Termo de busca muito curto (min 2 caracteres)',
            'busca': q
        }), 400
    
    df = load_data()
    
    # Buscar em portais locais
    mask = df.apply(
        lambda row: any(q in str(val).lower() for val in row), 
        axis=1
    )
    portais = df[mask].to_dict(orient='records')
    
    # Adicionar tipo aos portais
    for portal in portais:
        portal['tipo'] = 'portal'
        portal['score'] = 50 if portal['Qualidade'] == 'Alta' else 30
    
    # Buscar datasets no dados.gov.br
    try:
        client = DadosGovClient()
        datasets = client.search_datasets(query=q, rows=20)
    except Exception as e:
        print(f"Erro ao buscar datasets: {e}")
        datasets = []
    
    # Combinar e ordenar por score
    todos = portais + datasets
    todos_ordenados = sorted(todos, key=lambda x: x.get('score', 0), reverse=True)
    
    return jsonify({
        'busca': q,
        'total_resultados': len(todos_ordenados),
        'total_portais': len(portais),
        'total_datasets': len(datasets),
        'resultados': todos_ordenados
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'erro': 'Endpoint nao encontrado',
        'endpoints_disponiveis': [
            '/',
            '/health',
            '/metrics',
            '/catalogo',
            '/buscar',
            '/datasets',
            '/ranking',
            '/estatisticas'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'erro': 'Erro interno do servidor',
        'message': str(error)
    }), 500

if __name__ == '__main__':
    df = load_data()
    
    print("=" * 80)
    print("API Dados Publicos BR v2.1")
    print("=" * 80)
    print(f"Total de portais: {len(df)}")
    print(f"Estados: {len(df['UF'].unique())}")
    print(f"Qualidade Alta: {len(df[df['Qualidade'] == 'Alta'])}")
    print("=" * 80)
    print("\nEndpoints disponiveis:")
    print("  http://localhost:5000/")
    print("  http://localhost:5000/health")
    print("  http://localhost:5000/metrics")
    print("  http://localhost:5000/catalogo")
    print("  http://localhost:5000/buscar?q=saude     # BUSCA HIBRIDA")
    print("  http://localhost:5000/datasets?q=saude   # Datasets dados.gov.br")
    print("  http://localhost:5000/ranking")
    print("  http://localhost:5000/estatisticas")
    print("=" * 80)
    print("\nNOVO: Busca hibrida com datasets reais do dados.gov.br!")
    print("=" * 80)
    print("\nPressione CTRL+C para parar\n")
    
    # Configuracao para deploy (aceita conexoes externas)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
