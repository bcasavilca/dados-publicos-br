#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API REST para consulta ao catalogo de dados publicos brasileiros
Endpoints:
  - /                  Info da API
  - /catalogo          Lista todos os catalogos
  - /catalogo/{uf}     Filtra por UF
  - /catalogo/qualidade/{nivel}  Filtra por qualidade
  - /catalogo/categoria/{cat}    Filtra por categoria
  - /buscar?q={termo}  Busca tipo Google
  - /ranking           Ranking por qualidade
  - /estatisticas      Estatisticas gerais
  - /estados           Lista estados disponiveis
"""

from flask import Flask, jsonify, request
import pandas as pd
import os

app = Flask(__name__)

# Caminho do arquivo CSV
CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'catalogos.csv')

def load_data():
    """Carrega dados do CSV"""
    try:
        df = pd.read_csv(CSV_PATH)
        return df
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

@app.route('/')
def index():
    """Endpoint raiz com informacoes da API"""
    return jsonify({
        'nome': 'Dados Publicos BR API',
        'versao': '2.0.0',
        'descricao': 'API de consulta a portais de dados publicos brasileiros',
        'endpoints': {
            'catalogo': '/catalogo - Lista todos os portais',
            'catalogo_uf': '/catalogo/uf/{uf} - Filtra por estado',
            'catalogo_qualidade': '/catalogo/qualidade/{Alta|Media|Baixa}',
            'catalogo_categoria': '/catalogo/categoria/{categoria}',
            'buscar': '/buscar?q={termo} - Busca livre',
            'ranking': '/ranking - Melhores portais',
            'estatisticas': '/estatisticas - Dados agregados',
            'estados': '/estados - Lista de estados'
        },
        'total_portais': len(load_data())
    })

@app.route('/catalogo')
def catalogo():
    """Lista todos os portais catalogados"""
    df = load_data()
    
    # Filtros opcionais via query string
    uf = request.args.get('uf')
    qualidade = request.args.get('qualidade')
    categoria = request.args.get('categoria')
    
    if uf:
        df = df[df['UF'].str.upper() == uf.upper()]
    if qualidade:
        df = df[df['Qualidade'].str.lower() == qualidade.lower()]
    if categoria:
        df = df[df['Categoria'].str.lower() == categoria.lower()]
    
    return jsonify({
        'total': len(df),
        'filtros': {'uf': uf, 'qualidade': qualidade, 'categoria': categoria},
        'resultados': df.to_dict(orient='records')
    })

@app.route('/catalogo/uf/<uf>')
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
def ranking():
    """Ranking dos melhores portais por qualidade"""
    df = load_data()
    
    # Ordenar por qualidade (Alta > Media > Baixa)
    qualidade_order = {'Alta': 3, 'Media': 2, 'Baixa': 1}
    df['qualidade_num'] = df['Qualidade'].map(qualidade_order)
    df_sorted = df.sort_values(['qualidade_num', 'UF'], ascending=[False, True])
    
    # Agrupar por qualidade
    ranking_data = {
        'alta': df_sorted[df_sorted['Qualidade'] == 'Alta'].to_dict(orient='records'),
        'media': df_sorted[df_sorted['Qualidade'] == 'Media'].to_dict(orient='records'),
        'baixa': df_sorted[df_sorted['Qualidade'] == 'Baixa'].to_dict(orient='records')
    }
    
    return jsonify({
        'total_portais': len(df),
        'ranking': ranking_data,
        'melhores_uf': df[df['Qualidade'] == 'Alta']['UF'].value_counts().head(5).to_dict()
    })

@app.route('/estados')
def estados():
    """Lista estados/UFs disponiveis no catalogo"""
    df = load_data()
    estados_list = df['UF'].unique().tolist()
    
    return jsonify({
        'total_estados': len(estados_list),
        'estados': sorted(estados_list)
    })

@app.route('/estatisticas')
def estatisticas():
    """Estatisticas gerais do catalogo"""
    df = load_data()
    
    stats = {
        'total_portais': len(df),
        'por_uf': df['UF'].value_counts().to_dict(),
        'por_esfera': df['Esfera'].value_counts().to_dict(),
        'por_poder': df['Poder'].value_counts().to_dict(),
        'por_qualidade': df['Qualidade'].value_counts().to_dict(),
        'por_tipo_fonte': df['TipoFonte'].value_counts().to_dict(),
        'por_categoria': df['Categoria'].value_counts().to_dict(),
        'por_tipo_acesso': df['TipoAcesso'].value_counts().to_dict(),
        'melhores_portais': df[df['Qualidade'] == 'Alta']['Titulo'].tolist()[:10]
    }
    
    return jsonify(stats)

if __name__ == '__main__':
    df = load_data()
    
    print("=" * 80)
    print("API Dados Publicos BR v2.0")
    print("=" * 80)
    print(f"Total de portais: {len(df)}")
    print(f"Estados: {len(df['UF'].unique())}")
    print(f"Qualidade Alta: {len(df[df['Qualidade'] == 'Alta'])}")
    print("=" * 80)
    print("\nEndpoints disponiveis:")
    print("  http://localhost:5000/")
    print("  http://localhost:5000/catalogo")
    print("  http://localhost:5000/catalogo/uf/CE")
    print("  http://localhost:5000/catalogo/qualidade/Alta")
    print("  http://localhost:5000/catalogo/categoria/Financas")
    print("  http://localhost:5000/buscar?q=saude")
    print("  http://localhost:5000/ranking")
    print("  http://localhost:5000/estatisticas")
    print("  http://localhost:5000/estados")
    print("=" * 80)
    print("\nPressione CTRL+C para parar\n")
    
    # Configuracao para deploy (aceita conexoes externas)
    app.run(debug=True, host='0.0.0.0', port=5000)
