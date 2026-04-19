#!/usr/bin/env python3
"""
API de Cruzamento - Detecta padrões suspeitos
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

@app.route('/cruzamento/analisar')
def analisar():
    """
    Analisa um órgão/cidade e retorna alertas de padrões suspeitos
    
    Parâmetros:
    - orgao: nome do órgão ou cidade
    - estado: UF (opcional)
    """
    orgao = request.args.get('orgao', '')
    estado = request.args.get('estado', '')
    
    if not orgao:
        return jsonify({'erro': 'Informe o parâmetro orgao'}), 400
    
    # Simulação de análise (dados reais seriam buscados das APIs)
    alertas = []
    
    # Alertas de exemplo baseados em padrões reais
    alertas.append({
        'tipo': 'concentracao_fornecedor',
        'descricao': f'Empresa X ganhou 40% dos contratos de {orgao} em 2023',
        'gravidade': 'alta',
        'evidencia': '5 contratos no valor total de R$ 2.5M'
    })
    
    alertas.append({
        'tipo': 'financiamento_politico',
        'descricao': 'Dona da empresa X doou R$ 50k para campanha em 2022',
        'gravidade': 'media',
        'evidencia': 'TSE - Prestação de Contas'
    })
    
    return jsonify({
        'orgao_analisado': orgao,
        'estado': estado,
        'total_alertas': len(alertas),
        'alertas': alertas,
        'recomendacao': 'Investigar relação entre empresa X e candidato Y'
    })

@app.route('/cruzamento/empresa')
def analisar_empresa():
    """
    Analisa uma empresa específica
    
    Parâmetros:
    - cnpj: CNPJ da empresa
    """
    cnpj = request.args.get('cnpj', '')
    
    if not cnpj:
        return jsonify({'erro': 'Informe o CNPJ'}), 400
    
    # Buscar na Receita
    try:
        url = f'https://receitaws.com.br/v1/cnpj/{cnpj}'
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            dados = resp.json()
            return jsonify({
                'cnpj': cnpj,
                'nome': dados.get('nome'),
                'atividade_principal': dados.get('atividade_principal'),
                'situacao': dados.get('situacao'),
                'alerta': 'Consulta realizada'
            })
    except:
        pass
    
    return jsonify({'erro': 'Não foi possível consultar CNPJ'}), 502

@app.route('/')
def home():
    return jsonify({
        'servico': 'API de Cruzamento - Detecção de Padrões',
        'endpoints': [
            '/cruzamento/analisar?orgao=Fortaleza',
            '/cruzamento/empresa?cnpj=00000000000191'
        ]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
