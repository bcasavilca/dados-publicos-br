#!/usr/bin/env python3
"""
API Cerebro Digital - Análise Avançada de Dados Públicos
Endpoints para transparência e detecção de padrões
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sys
import os

sys.path.append(os.path.dirname(__file__))
from cerebro_digital import CerebroDigital

app = Flask(__name__)
CORS(app)

# Instância do Cerebro
cerebro = CerebroDigital()

@app.route('/')
def home():
    return jsonify({
        'nome': 'Cerebro Digital API',
        'versao': '1.0',
        'funcionalidades': [
            '/analise/documento - Analisar CPF/CNPJ',
            '/cruzamento - Cruzar dois documentos',
            '/fornecedores/ranking - Ranking por valor',
            '/alertas - Lista de alertas gerados',
            '/relatorio - Relatório completo'
        ]
    })

@app.route('/analise/documento', methods=['POST'])
def analisar_documento():
    """
    Analisa um CPF ou CNPJ
    """
    data = request.get_json()
    
    if not data or 'nome' not in data or 'documento' not in data:
        return jsonify({'erro': 'Campos obrigatórios: nome, documento'}), 400
    
    nome = data['nome']
    documento = data['documento']
    valor = data.get('valor', 0)
    orgaos = data.get('orgaos', [])
    
    pessoa = cerebro.analisar_fornecedor(nome, documento, valor, orgaos)
    
    return jsonify({
        'nome': pessoa.nome,
        'documento': pessoa.documento,
        'tipo': pessoa.tipo,
        'quantidade_contratos': pessoa.quantidade_contratos,
        'valor_total': pessoa.valor_total,
        'score_risco': pessoa.score_risco,
        'orgaos': list(set(pessoa.parentes))
    })

@app.route('/cruzamento', methods=['POST'])
def cruzar_documentos():
    """
    Cruza dois documentos buscando vínculos
    """
    data = request.get_json()
    
    if not data or 'doc1' not in data or 'doc2' not in data:
        return jsonify({'erro': 'Campos obrigatórios: doc1, doc2'}), 400
    
    resultado = cerebro.cruzar_documentos(data['doc1'], data['doc2'])
    
    return jsonify(resultado)

@app.route('/fornecedores/ranking')
def ranking_fornecedores():
    """
    Retorna ranking de fornecedores por valor
    """
    limite = request.args.get('limite', 10, type=int)
    
    fornecedores = sorted(
        cerebro.pessoas.values(),
        key=lambda x: x.valor_total,
        reverse=True
    )[:limite]
    
    return jsonify({
        'total': len(cerebro.pessoas),
        'ranking': [
            {
                'nome': f.nome,
                'documento': f.documento,
                'tipo': f.tipo,
                'valor_total': f.valor_total,
                'quantidade_contratos': f.quantidade_contratos,
                'score_risco': f.score_risco
            }
            for f in fornecedores
        ]
    })

@app.route('/alertas')
def listar_alertas():
    """
    Retorna alertas de risco gerados
    """
    min_score = request.args.get('min_score', 50, type=int)
    
    alertas_filtrados = [
        a for a in cerebro.alertas 
        if a['score'] >= min_score
    ]
    
    return jsonify({
        'total_alertas': len(cerebro.alertas),
        'alertas_filtrados': len(alertas_filtrados),
        'alertas': alertas_filtrados
    })

@app.route('/relatorio')
def gerar_relatorio():
    """
    Gera relatório completo
    """
    relatorio = cerebro.gerar_relatorio()
    return jsonify(relatorio)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print("=" * 80)
    print("CEREBRO DIGITAL API")
    print("=" * 80)
    print(f"Porta: {port}")
    print("Endpoints:")
    print("  POST /analise/documento")
    print("  POST /cruzamento")
    print("  GET  /fornecedores/ranking")
    print("  GET  /alertas")
    print("  GET  /relatorio")
    print("=" * 80)
    app.run(host='0.0.0.0', port=port)
