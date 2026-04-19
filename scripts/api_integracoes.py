#!/usr/bin/env python3
"""
API de Integrações - Acesso unificado a fontes de dados públicos
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os

sys.path.append(os.path.dirname(__file__))
from integracoes import IntegradorGeral

app = Flask(__name__)
CORS(app)

integrador = IntegradorGeral()

@app.route('/')
def home():
    return jsonify({
        'nome': 'API de Integrações - Dados Públicos BR',
        'versao': '1.0',
        'fontes_disponiveis': [
            '/dadosgov - Portal dados.gov.br',
            '/ibge - Dados do IBGE',
            '/tse - Dados eleitorais',
            '/receita - Dados da Receita (CNPJ)',
            '/transparencia - Portal Transparência Gov',
            '/busca - Busca inteligente em todas as fontes'
        ]
    })

@app.route('/dadosgov/buscar')
def buscar_dadosgov():
    """
    Busca datasets no dados.gov.br
    """
    termo = request.args.get('q', '')
    orgao = request.args.get('orgao')
    
    if not termo:
        return jsonify({'erro': 'Parâmetro q obrigatório'}), 400
    
    resultados = integrador.dadosgov.buscar_datasets(termo, orgao)
    
    return jsonify({
        'termo': termo,
        'total': len(resultados),
        'datasets': resultados
    })

@app.route('/dadosgov/organizacoes')
def listar_organizacoes():
    """
    Lista organizações no dados.gov.br
    """
    orgs = integrador.dadosgov.organizacoes()
    return jsonify({
        'total': len(orgs),
        'organizacoes': orgs
    })

@app.route('/ibge/municipio/<codigo>')
def dados_municipio(codigo):
    """
    Obtém dados de um município pelo código IBGE
    """
    dados = integrador.ibge.dados_municipio(codigo)
    return jsonify(dados)

@app.route('/tse/candidatos')
def candidatos_tse():
    """
    Busca candidatos por ano e cargo
    """
    ano = request.args.get('ano', 2024, type=int)
    cargo = request.args.get('cargo', 'deputado_federal')
    
    resultados = integrador.tse.buscar_candidatos(ano, cargo)
    
    return jsonify({
        'ano': ano,
        'cargo': cargo,
        'total': len(resultados),
        'candidatos': resultados
    })

@app.route('/receita/cnpj/<cnpj>')
def consultar_cnpj(cnpj):
    """
    Consulta dados de CNPJ na Receita Federal
    """
    dados = integrador.receita.consultar_cnpj(cnpj)
    
    if dados:
        return jsonify({
            'encontrado': True,
            'cnpj': cnpj,
            'dados': dados
        })
    
    return jsonify({
        'encontrado': False,
        'cnpj': cnpj,
        'mensagem': 'CNPJ não encontrado ou API indisponível'
    }), 404

@app.route('/busca/inteligente')
def busca_inteligente():
    """
    Busca em múltiplas fontes simultaneamente
    """
    termo = request.args.get('q', '')
    
    if not termo:
        return jsonify({'erro': 'Parâmetro q obrigatório'}), 400
    
    resultados = integrador.busca_inteligente(termo)
    
    return jsonify(resultados)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    print("=" * 80)
    print("API DE INTEGRAÇÕES - DADOS PÚBLICOS BR")
    print("=" * 80)
    print(f"Porta: {port}")
    print("Endpoints:")
    print("  GET /dadosgov/buscar?q=termo")
    print("  GET /dadosgov/organizacoes")
    print("  GET /ibge/municipio/<codigo>")
    print("  GET /tse/candidatos")
    print("  GET /receita/cnpj/<cnpj>")
    print("  GET /busca/inteligente?q=termo")
    print("=" * 80)
    app.run(host='0.0.0.0', port=port)
