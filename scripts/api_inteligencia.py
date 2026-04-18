#!/usr/bin/env python3
"""
API de Inteligência de Transparência
Passo 2: Normalizacao + Anomalias
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os

# Adicionar path para imports
sys.path.append(os.path.dirname(__file__))
from normalizador import Normalizador, TipoEvento

app = Flask(__name__)
CORS(app, origins=['*'])

# Cache de eventos e anomalias
cache_eventos = []
cache_anomalias = []

@app.route('/')
def home():
    return jsonify({
        'nome': 'Dados Publicos BR - Inteligencia',
        'versao': '3.0-inteligencia',
        'fase': '2',
        'funcionalidades': [
            '/eventos - Lista eventos financeiros normalizados',
            '/anomalias - Detecta padroes suspeitos',
            '/fornecedores - Analise de fornecedores',
            '/status - Status do sistema'
        ]
    })

@app.route('/eventos')
def listar_eventos():
    """
    Retorna eventos financeiros normalizados
    Filtros: tipo, fornecedor, valor_min, valor_max, uf
    """
    # Aqui carregaria de banco de dados ou arquivo
    # Por enquanto retorna estrutura vazia ou cache
    
    tipo = request.args.get('tipo')
    fornecedor = request.args.get('fornecedor', '').lower()
    uf = request.args.get('uf', '').upper()
    valor_min = request.args.get('valor_min', 0, type=float)
    valor_max = request.args.get('valor_max', float('inf'), type=float)
    
    return jsonify({
        'total': len(cache_eventos),
        'filtros': {'tipo': tipo, 'fornecedor': fornecedor, 'uf': uf, 'valor_min': valor_min, 'valor_max': valor_max},
        'eventos': [],
        'nota': 'Sistema de normalizacao implementado. Alimentar com dados reais para ver resultados.'
    })

@app.route('/anomalias')
def detectar_anomalias():
    """
    Detecta anomalias nos dados
    Tipos: fornecedor_frequente, valor_atipico, pico_temporal
    """
    # Se tiver eventos no cache, analisa
    if cache_eventos:
        norm = Normalizador()
        anomalias = norm.detectar_anomalias(cache_eventos)
        return jsonify({
            'total_anomalias': len(anomalias),
            'por_tipo': {
                'fornecedor_frequente': len([a for a in anomalias if a['tipo'] == 'fornecedor_frequente']),
                'valor_atipico': len([a for a in anomalias if a['tipo'] == 'valor_atipico']),
                'pico_temporal': len([a for a in anomalias if a['tipo'] == 'pico_temporal'])
            },
            'anomalias_criticas': [a for a in anomalias if a.get('gravidade') == 'alta'][:10],
            'todas': anomalias
        })
    
    return jsonify({
        'total_anomalias': 0,
        'nota': 'Nenhum dado normalizado ainda. Use /eventos para carregar dados primeiro.',
        'exemplo': {
            'tipo': 'fornecedor_frequente',
            'fornecedor': 'Empresa Exemplo LTDA',
            'quantidade': 15,
            'valor_total': 250000.00,
            'gravidade': 'alta'
        }
    })

@app.route('/fornecedores')
def analisar_fornecedores():
    """
    Analise agregada de fornecedores
    """
    if not cache_eventos:
        return jsonify({
            'total_fornecedores': 0,
            'nota': 'Carregue dados primeiro via /eventos'
        })
    
    # Agrupar por fornecedor
    fornecedores = {}
    for e in cache_eventos:
        if e.fornecedor:
            if e.fornecedor not in fornecedores:
                fornecedores[e.fornecedor] = {
                    'nome': e.fornecedor,
                    'documento': e.fornecedor_doc,
                    'quantidade_eventos': 0,
                    'valor_total': 0,
                    'ufs': set(),
                    'orgaos': set()
                }
            fornecedores[e.fornecedor]['quantidade_eventos'] += 1
            fornecedores[e.fornecedor]['valor_total'] += e.valor
            fornecedores[e.fornecedor]['ufs'].add(e.uf)
            fornecedores[e.fornecedor]['orgaos'].add(e.orgao)
    
    # Converter sets para listas
    for f in fornecedores.values():
        f['ufs'] = list(f['ufs'])
        f['orgaos'] = list(f['orgaos'])
    
    # Ordenar por valor total
    ranking = sorted(fornecedores.values(), key=lambda x: x['valor_total'], reverse=True)
    
    return jsonify({
        'total_fornecedores': len(fornecedores),
        'top_10': ranking[:10],
        'fornecedores_multiplo_uf': len([f for f in ranking if len(f['ufs']) > 1])
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 80)
    print("API DE INTELIGENCIA DE TRANSPARENCIA")
    print("=" * 80)
    print(f"[OK] Servidor iniciando na porta {port}")
    print("[OK] Endpoints:")
    print("       /eventos     - Eventos financeiros normalizados")
    print("       /anomalias   - Detecção de padrões suspeitos")
    print("       /fornecedores- Análise de fornecedores")
    print("=" * 80)
    app.run(host='0.0.0.0', port=port)
