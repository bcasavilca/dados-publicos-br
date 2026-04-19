#!/usr/bin/env python3
"""
Integrações com Fontes de Dados Públicos Brasileiras
Conectores para APIs e bases de dados abertas
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime

class IntegracaoTSE:
    """
    Integração com dados eleitorais do TSE
    """
    BASE_URL = "https://dadosabertos.tse.jus.br/api/3/action"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DadosPublicosBR/1.0'
        })
    
    def buscar_candidatos(self, ano: int, cargo: str = "deputado_federal") -> List[Dict]:
        """
        Busca candidatos por ano e cargo
        """
        try:
            url = f"{self.BASE_URL}/package_search"
            params = {
                'q': f'candidatos {ano} {cargo}',
                'rows': 100
            }
            
            response = self.session.get(url, params=params, timeout=30)
            data = response.json()
            
            if data.get('success'):
                return data['result']['results']
            return []
            
        except Exception as e:
            print(f"[TSE] Erro ao buscar candidatos: {e}")
            return []
    
    def buscar_bens_candidato(self, cpf: str, ano: int) -> List[Dict]:
        """
        Busca bens declarados por candidato
        """
        # Dados públicos de bens de candidatos
        try:
            url = f"http://divulgacandcontas.tse.jus.br/divulga/rest/v1/prestador/consulta/2040602024/1/{ano}/1/{cpf}/0"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json().get('bens', [])
        except:
            pass
        return []


class IntegracaoIBGE:
    """
    Integração com dados do IBGE
    """
    BASE_URL = "https://servicodados.ibge.gov.br/api/v1"
    
    def __init__(self):
        self.session = requests.Session()
    
    def dados_municipio(self, codigo_ibge: str) -> Dict:
        """
        Obtém dados de um município
        """
        try:
            url = f"{self.BASE_URL}/localidades/municipios/{codigo_ibge}"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"[IBGE] Erro: {e}")
        return {}
    
    def dados_pesquisa(self, indicador: str, localidade: str) -> List[Dict]:
        """
        Obtém dados de pesquisa do IBGE (PIB, população, etc)
        """
        try:
            url = f"{self.BASE_URL}/pesquisas/indicadores/{indicador}/resultados/{localidade}"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"[IBGE] Erro na pesquisa: {e}")
        return []


class IntegracaoReceita:
    """
    Integração com dados da Receita Federal
    APIs públicas de consulta
    """
    
    def consultar_cnpj(self, cnpj: str) -> Optional[Dict]:
        """
        Consulta dados de CNPJ via API pública
        """
        cnpj_limpo = re.sub(r'[^\d]', '', cnpj)
        
        # API pública gratuita (rate limit aplicável)
        apis = [
            f"https://www.receitaws.com.br/v1/cnpj/{cnpj_limpo}",
            f"https://api.cnpja.com.br/cnpj/{cnpj_limpo}",
        ]
        
        for url in apis:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    return response.json()
            except:
                continue
        
        return None


class IntegracaoPortalTransparencia:
    """
    Integração com Portal da Transparência do Governo Federal
    """
    BASE_URL = "http://www.portaltransparencia.gov.br/api-de-dados"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({
                'chave-api-dados': api_key
            })
    
    def buscar_gastos_cartao(self, cpf: str, ano: int) -> List[Dict]:
        """
        Busca gastos de cartão corporativo por CPF
        """
        # Requer chave de API
        if not self.api_key:
            return []
        
        try:
            url = f"{self.BASE_URL}/cartoes"
            params = {
                'cpf': cpf,
                'ano': ano,
                'pagina': 1
            }
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"[Transparencia] Erro: {e}")
        return []
    
    def buscar_viagens(self, cpf: str, ano: int) -> List[Dict]:
        """
        Busca viagens oficiais pagas com dinheiro público
        """
        if not self.api_key:
            return []
        
        try:
            url = f"{self.BASE_URL}/viagens"
            params = {
                'cpf': cpf,
                'ano': ano
            }
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"[Transparencia] Erro: {e}")
        return []


class IntegracaoDadosGov:
    """
    Integração com dados.gov.br
    """
    BASE_URL = "https://dados.gov.br/api/3/action"
    
    def __init__(self):
        self.session = requests.Session()
    
    def buscar_datasets(self, termo: str, orgao: Optional[str] = None) -> List[Dict]:
        """
        Busca datasets no portal dados.gov.br
        """
        try:
            url = f"{self.BASE_URL}/package_search"
            params = {
                'q': termo,
                'rows': 50
            }
            if orgao:
                params['fq'] = f'organization:{orgao}'
            
            response = self.session.get(url, params=params, timeout=30)
            data = response.json()
            
            if data.get('success'):
                return data['result']['results']
        except Exception as e:
            print(f"[DadosGov] Erro: {e}")
        return []
    
    def organizacoes(self) -> List[Dict]:
        """
        Lista organizações no dados.gov.br
        """
        try:
            url = f"{self.BASE_URL}/organization_list"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json().get('result', [])
        except Exception as e:
            print(f"[DadosGov] Erro: {e}")
        return []


class IntegradorGeral:
    """
    Orquestra múltiplas integrações
    """
    
    def __init__(self):
        self.tse = IntegracaoTSE()
        self.ibge = IntegracaoIBGE()
        self.receita = IntegracaoReceita()
        self.transparencia = IntegracaoPortalTransparencia()
        self.dadosgov = IntegracaoDadosGov()
    
    def perfil_completo_pessoa(self, documento: str) -> Dict:
        """
        Gera perfil completo cruzando múltiplas fontes
        """
        documento_limpo = re.sub(r'[^\d]', '', documento)
        perfil = {
            'documento': documento_limpo,
            'fontes': [],
            'dados': {}
        }
        
        # Se for CNPJ
        if len(documento_limpo) == 14:
            dados_receita = self.receita.consultar_cnpj(documento_limpo)
            if dados_receita:
                perfil['fontes'].append('receita_federal')
                perfil['dados']['cnpj'] = dados_receita
        
        # Se for CPF (requer chaves de API para dados sensíveis)
        # Perfis públicos disponíveis
        
        return perfil
    
    def busca_inteligente(self, termo: str) -> Dict:
        """
        Busca em múltiplas fontes simultaneamente
        """
        resultados = {
            'termo': termo,
            'timestamp': datetime.now().isoformat(),
            'fontes': {}
        }
        
        # Buscar em dados.gov.br
        resultados['fontes']['dadosgov'] = self.dadosgov.buscar_datasets(termo)
        
        # Buscar no TSE
        resultados['fontes']['tse'] = self.tse.buscar_candidatos(2024)
        
        return resultados


if __name__ == "__main__":
    print("=" * 80)
    print("INTEGRAÇÕES - FONTES DE DADOS PÚBLICOS")
    print("=" * 80)
    
    integrador = IntegradorGeral()
    
    # Teste de busca
    print("\n[1] Testando busca em dados.gov.br...")
    resultados = integrador.dadosgov.buscar_datasets("transparencia saude")
    print(f"  Encontrados {len(resultados)} datasets")
    
    if resultados:
        print(f"  Primeiro: {resultados[0].get('title', 'N/A')}")
    
    print("\n[2] Testando consulta de CNPJ (exemplo)...")
    # Exemplo: CNPJ da Petrobras (público)
    cnpj_petrobras = "33.000.167/0001-01"
    print(f"  CNPJ: {cnpj_petrobras}")
    print("  (Consulta real requer cuidado com rate limits)")
    
    print("\n[3] Listando organizações no dados.gov.br...")
    orgs = integrador.dadosgov.organizacoes()
    print(f"  Total de organizações: {len(orgs)}")
    if orgs:
        print(f"  Exemplos: {', '.join(orgs[:5])}")
    
    print("\n" + "=" * 80)
    print("Integrações prontas para uso!")
    print("=" * 80)
    print("\nPara usar em produção:")
    print("  - Obter chaves de API quando necessário")
    print("  - Respeitar rate limits")
    print("  - Cachear resultados para performance")
