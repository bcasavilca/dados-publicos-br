#!/usr/bin/env python3
"""
Scraper Fortaleza - Extrai dados do portal de transparencia
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
from datetime import datetime

def scrape_fortaleza():
    """
    Scraper simplificado para dados de Fortaleza
    Portal: https://transparencia.fortaleza.ce.gov.br/
    """
    
    # URL base do portal
    base_url = "https://transparencia.fortaleza.ce.gov.br/"
    
    print("Iniciando scraping de Fortaleza...")
    print(f"URL: {base_url}")
    
    try:
        response = requests.get(base_url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extrair links de despesas/contratos
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if any(x in href.lower() for x in ['despesa', 'contrato', 'licitacao']):
                links.append({
                    'texto': a.get_text(strip=True),
                    'url': href if href.startswith('http') else base_url + href
                })
        
        print(f"Encontrados {len(links)} links relevantes")
        
        # Salvar para analise manual
        with open('fortaleza_links.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['texto', 'url'])
            writer.writeheader()
            writer.writerows(links)
        
        print("Links salvos em: fortaleza_links.csv")
        
        # Nota: scraping real precisaria de analise profunda do HTML
        # e provavelmente paginacao
        
        return {
            'status': 'ok',
            'links_encontrados': len(links),
            'arquivo': 'fortaleza_links.csv',
            'observacao': 'Analise manual necessaria para estruturar scraping completo'
        }
        
    except Exception as e:
        return {
            'status': 'erro',
            'mensagem': str(e),
            'sugestao': 'Verificar se site esta acessivel ou usar API oficial'
        }

if __name__ == '__main__':
    resultado = scrape_fortaleza()
    print(f"\nResultado: {resultado}")
