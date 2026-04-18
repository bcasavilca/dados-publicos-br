#!/usr/bin/env python3
"""
Normalizador de dados públicos
Transforma diferentes fontes em estrutura única: eventos financeiros
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class TipoEvento(Enum):
    CONTRATO = "contrato"
    DISPENSA = "dispensa_licitacao"
    ADITIVO = "aditivo"
    TRANSFERENCIA = "transferencia"
    DIARIA = "diaria"
    REEMBOLSO = "reembolso"
    OUTRO = "outro"

class FormatoDado(Enum):
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    PDF = "pdf"
    HTML = "html"
    API = "api"

@dataclass
class EventoFinanceiro:
    """
    Estrutura única para qualquer evento financeiro público
    """
    # Identificação
    id: str
    tipo: TipoEvento
    
    # Origem
    orgao: str
    orgao_id: str
    municipio: str
    uf: str
    esfera: str  # municipal, estadual, federal
    
    # Participantes
    fornecedor: Optional[str]
    fornecedor_doc: Optional[str]  # CPF/CNPJ
    responsavel: Optional[str]
    
    # Valores
    valor: float
    valor_original: Optional[float]
    moeda: str
    
    # Temporal
    data_inicio: Optional[str]
    data_fim: Optional[str]
    data_publicacao: Optional[str]
    ano_exercicio: int
    
    # Conteúdo
    objeto: str
    justificativa: Optional[str]
    
    # Fonte
    fonte_url: str
    fonte_tipo: FormatoDado
    fonte_confiança: int  # 0-100
    
    # Metadados
    extraido_em: str
    hash_verificacao: str

class Normalizador:
    """
    Converte dados de diferentes formatos para EventoFinanceiro
    """
    
    def __init__(self):
        self.eventos = []
    
    def normalizar_diarias_fortaleza_2023(self, csv_path: str) -> List[EventoFinanceiro]:
        """
        Normaliza dados de diárias da Prefeitura de Fortaleza 2023
        """
        eventos = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for i, row in enumerate(reader):
                    try:
                        # Extrair valor (remover R$ e pontos, manter vírgula)
                        valor_str = row.get('Valor total diaria', '0')
                        valor_str = valor_str.replace('R$', '').replace('.', '').replace(',', '.')
                        valor = float(valor_str) if valor_str else 0.0
                        
                        # Extrair ano do exercício
                        exercicio = row.get('Exercicio', '2023')
                        
                        # Criar evento
                        evento = EventoFinanceiro(
                            id=f"fortaleza_diaria_2023_{i}",
                            tipo=TipoEvento.DIARIA,
                            orgao=row.get('Unidade orçamentaria', 'Prefeitura de Fortaleza'),
                            orgao_id=row.get('N do empenho', ''),
                            municipio="Fortaleza",
                            uf="CE",
                            esfera="municipal",
                            fornecedor=row.get('Beneficiario', ''),
                            fornecedor_doc=None,  # Não disponível
                            responsavel=None,
                            valor=valor,
                            valor_original=valor,
                            moeda="BRL",
                            data_inicio=row.get('Periodo', '').split(' a ')[0] if ' a ' in row.get('Periodo', '') else None,
                            data_fim=row.get('Periodo', '').split(' a ')[1] if ' a ' in row.get('Periodo', '') else None,
                            data_publicacao=None,
                            ano_exercicio=int(exercicio) if exercicio.isdigit() else 2023,
                            objeto=f"Viagem para {row.get('Destino', '')}: {row.get('Motivo', '')}",
                            justificativa=None,
                            fonte_url="https://transparencia.fortaleza.ce.gov.br/",
                            fonte_tipo=FormatoDado.CSV,
                            fonte_confiança=80,
                            extraido_em=datetime.now().isoformat(),
                            hash_verificacao=""
                        )
                        
                        eventos.append(evento)
                        
                    except Exception as e:
                        print(f"[Erro] Linha {i}: {e}")
                        continue
                        
        except Exception as e:
            print(f"[Erro] Arquivo {csv_path}: {e}")
        
        print(f"[Normalizador] {len(eventos)} eventos extraídos de {csv_path}")
        return eventos
    
    def detectar_anomalias(self, eventos: List[EventoFinanceiro]) -> List[Dict]:
        """
        Detecta padrões suspeitos nos eventos
        """
        anomalias = []
        
        # Agrupar por fornecedor
        fornecedores = {}
        for e in eventos:
            if e.fornecedor:
                if e.fornecedor not in fornecedores:
                    fornecedores[e.fornecedor] = []
                fornecedores[e.fornecedor].append(e)
        
        # Anomalia 1: Fornecedor com muitos contratos
        for forn, evs in fornecedores.items():
            if len(evs) > 5:
                valor_total = sum(e.valor for e in evs)
                anomalias.append({
                    'tipo': 'fornecedor_frequente',
                    'fornecedor': forn,
                    'quantidade': len(evs),
                    'valor_total': valor_total,
                    'eventos_ids': [e.id for e in evs[:5]],
                    'gravidade': 'media' if len(evs) < 10 else 'alta'
                })
        
        # Anomalia 2: Valores muito acima da média
        valores = [e.valor for e in eventos if e.valor > 0]
        if valores:
            media = sum(valores) / len(valores)
            desvio_padrao = (sum((v - media) ** 2 for v in valores) / len(valores)) ** 0.5
            
            for e in eventos:
                if e.valor > media + (3 * desvio_padrao):
                    anomalias.append({
                        'tipo': 'valor_atipico',
                        'evento_id': e.id,
                        'valor': e.valor,
                        'media': media,
                        'desvios_acima_media': (e.valor - media) / desvio_padrao,
                        'fornecedor': e.fornecedor,
                        'gravidade': 'alta'
                    })
        
        # Anomalia 3: Picos temporais (muitos eventos no mesmo mês)
        eventos_por_mes = {}
        for e in eventos:
            if e.data_inicio:
                mes = e.data_inicio[:7]  # YYYY-MM
                eventos_por_mes[mes] = eventos_por_mes.get(mes, 0) + 1
        
        if eventos_por_mes:
            media_mensal = sum(eventos_por_mes.values()) / len(eventos_por_mes)
            for mes, qtd in eventos_por_mes.items():
                if qtd > media_mensal * 2:
                    anomalias.append({
                        'tipo': 'pico_temporal',
                        'mes': mes,
                        'quantidade': qtd,
                        'media_esperada': media_mensal,
                        'gravidade': 'media'
                    })
        
        return anomalias
    
    def exportar_json(self, eventos: List[EventoFinanceiro], filename: str):
        """Exporta eventos para JSON"""
        data = [{
            'id': e.id,
            'tipo': e.tipo.value,
            'orgao': e.orgao,
            'municipio': e.municipio,
            'uf': e.uf,
            'fornecedor': e.fornecedor,
            'valor': e.valor,
            'data_inicio': e.data_inicio,
            'data_fim': e.data_fim,
            'objeto': e.objeto,
            'fonte_url': e.fonte_url
        } for e in eventos]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"[Normalizador] Exportados {len(eventos)} eventos para {filename}")


if __name__ == "__main__":
    norm = Normalizador()
    
    # Exemplo: normalizar diárias de Fortaleza
    print("=" * 80)
    print("NORMALIZADOR DE DADOS PÚBLICOS")
    print("=" * 80)
    
    # Aqui você chamaria para seus arquivos reais
    # eventos = norm.normalizar_diarias_fortaleza_2023('caminho/do/arquivo.csv')
    # anomalias = norm.detectar_anomalias(eventos)
    # norm.exportar_json(eventos, 'eventos_normalizados.json')
    
    print("\nUso:")
    print("  from normalizador import Normalizador")
    print("  norm = Normalizador()")
    print("  eventos = norm.normalizar_diarias_fortaleza_2023('diarias.csv')")
    print("  anomalias = norm.detectar_anomalias(eventos)")
    print("=" * 80)
