#!/usr/bin/env python3
"""
Scraper para Transparencia Legislativa AL-RN
https://transparencialegislativa.al.rn.leg.br
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
from datetime import datetime
from typing import List, Dict

class ScraperALRN:
    """
    Extrai dados de gastos da Assembleia Legislativa do RN
    """
    
    BASE_URL = "https://transparencialegislativa.al.rn.leg.br"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.dados = []
    
    def verificar_estrutura(self) -> Dict:
        """
        Verifica a estrutura do site
        """
        try:
            response = self.session.get(self.BASE_URL, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar links de menu
            menus = soup.find_all('a', href=True)
            links_relevantes = [
                {'texto': m.text.strip(), 'url': m['href']}
                for m in menus
                if any(palavra in m.text.lower() for palavra in [
                    'despesa', 'gasto', 'diaria', 'verba', 'indenizacao', 
                    'salario', 'remuneracao', 'beneficio', 'cotas'
                ])
            ]
            
            return {
                'status': 'online',
                'titulo': soup.title.string if soup.title else 'N/A',
                'links_encontrados': links_relevantes[:10],
                'total_links': len(menus)
            }
            
        except Exception as e:
            return {'status': 'erro', 'mensagem': str(e)}
    
    def extrair_despesas(self, ano: int = 2025) -> List[Dict]:
        """
        Tenta extrair despesas parlamentares
        """
        try:
            # URLs comuns de transparência legislativa
            urls_teste = [
                f"{self.BASE_URL}/despesas",
                f"{self.BASE_URL}/verbas",
                f"{self.BASE_URL}/cotas",
                f"{self.BASE_URL}/diarias",
                f"{self.BASE_URL}/salarios",
            ]
            
            resultados = []
            
            for url in urls_teste:
                try:
                    response = self.session.get(url, timeout=5)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Verificar se tem tabela de dados
                        tabelas = soup.find_all('table')
                        if tabelas:
                            resultados.append({
                                'url': url,
                                'titulo': soup.title.string if soup.title else 'N/A',
                                'tabelas_encontradas': len(tabelas),
                                'possui_dados': True
                            })
                        else:
                            resultados.append({
                                'url': url,
                                'titulo': soup.title.string if soup.title else 'N/A',
                                'tabelas_encontradas': 0,
                                'possui_dados': False
                            })
                            
                except Exception as e:
                    resultados.append({'url': url, 'erro': str(e)})
            
            return resultados
            
        except Exception as e:
            return [{'erro': str(e)}]
    
    def salvar_catalogo(self, filename: str = '../data/alrn_catalogo.json'):
        """
        Salva informações do portal no catálogo
        """
        estrutura = self.verificar_estrutura()
        
        catalogo = {
            'titulo': 'Transparência Legislativa AL-RN',
            'url': self.BASE_URL,
            'tipo': 'Transparencia',
            'esfera': 'Estadual',
            'poder': 'Legislativo',
            'uf': 'RN',
            'verificacao': estrutura,
            'atualizado_em': datetime.now().isoformat()
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(catalogo, f, ensure_ascii=False, indent=2)
            print(f"[Scraper] Catálogo salvo em {filename}")
        except Exception as e:
            print(f"[Erro] Salvar catálogo: {e}")


if __name__ == "__main__":
    scraper = ScraperALRN()
    
    print("=" * 80)
    print("SCRAPER - TRANSPARÊNCIA LEGISLATIVA AL-RN")
    print("=" * 80)
    
    # Verificar estrutura
    print("\n[1] Verificando estrutura do site...")
    estrutura = scraper.verificar_estrutura()
    print(f"Status: {estrutura.get('status')}")
    print(f"Título: {estrutura.get('titulo')}")
    
    if estrutura.get('links_encontrados'):
        print("\nLinks relevantes encontrados:")
        for link in estrutura['links_encontrados'][:5]:
            print(f"  - {link['texto']}: {link['url']}")
    
    # Tentar extrair despesas
    print("\n[2] Tentando extrair dados de despesas...")
    despesas = scraper.extrair_despesas()
    
    for d in despesas:
        if 'url' in d:
            status = "✅ Dados" if d.get('possui_dados') else "❌ Sem dados"
            print(f"  {d['url']}: {status}")
        elif 'erro' in d:
            print(f"  Erro: {d['erro']}")
    
    # Salvar catálogo
    print("\n[3] Salvando informações...")
    scraper.salvar_catalogo()
    
    print("=" * 80)
