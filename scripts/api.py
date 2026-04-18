#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API simples para consulta ao catalogo de dados publicos
Endpoints:
  - /catalogo - Lista todos os catalogos
  - /catalogo/{uf} - Filtra por UF
  - /catalogo/qualidade/{nivel} - Filtra por qualidade (Alta/Media/Baixa)
  - /estatisticas - Estatisticas gerais
"""

from flask import Flask, jsonify, request
import pandas as pd

app = Flask(__name__)

# Carregar dados
def load_data():
    df = pd.read_csv('data/catalogos.csv')
    return df

@app.route('/')
def index():
    return jsonify({
        'nome': 'Dados Publicos BR API',
        'versao': '1.0.0',
        'endpoints': [
            '/catalogo',
            '/catalogo/uf/<uf>',
            '/catalogo/qualidade/<nivel>',
            '/estatisticas'
        ]
    })

@app.route('/catalogo')
def catalogo():
    df = load_data()
    return jsonify(df.to_dict(orient='records'))

@app.route('/catalogo/uf/<uf>')
def catalogo_uf(uf):
    df = load_data()
    filtered = df[df['UF'].str.upper() == uf.upper()]
    return jsonify(filtered.to_dict(orient='records'))

@app.route('/catalogo/qualidade/<nivel>')
def catalogo_qualidade(nivel):
    df = load_data()
    filtered = df[df['Qualidade'].str.lower() == nivel.lower()]
    return jsonify(filtered.to_dict(orient='records'))

@app.route('/catalogo/tipo/<tipo>')
def catalogo_tipo(tipo):
    df = load_data()
    filtered = df[df['TipoFonte'].str.lower() == tipo.lower()]
    return jsonify(filtered.to_dict(orient='records'))

@app.route('/estatisticas')
def estatisticas():
    df = load_data()
    
    stats = {
        'total_catalogos': len(df),
        'por_uf': df['UF'].value_counts().to_dict(),
        'por_esfera': df['Esfera'].value_counts().to_dict(),
        'por_poder': df['Poder'].value_counts().to_dict(),
        'por_qualidade': df['Qualidade'].value_counts().to_dict(),
        'por_tipo_fonte': df['TipoFonte'].value_counts().to_dict()
    }
    
    return jsonify(stats)

if __name__ == '__main__':
    print("=" * 80)
    print("API Dados Publicos BR")
    print("=" * 80)
    print("Endpoints disponiveis:")
    print("  http://localhost:5000/")
    print("  http://localhost:5000/catalogo")
    print("  http://localhost:5000/catalogo/uf/CE")
    print("  http://localhost:5000/catalogo/qualidade/Alta")
    print("  http://localhost:5000/estatisticas")
    print("=" * 80)
    print("\nPressione CTRL+C para parar\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
