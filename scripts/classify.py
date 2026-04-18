#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de classificacao automatica de URLs de dados publicos
Classifica o tipo de acesso baseado na URL
"""

def classify_url(url):
    """
    Classifica a URL em tipos de acesso
    """
    url_lower = url.lower()
    
    if "api" in url_lower:
        return "API"
    elif "dados" in url_lower or "ckan" in url_lower:
        return "API/Download"
    elif "transparencia" in url_lower:
        return "Scraping"
    elif "download" in url_lower:
        return "Download"
    else:
        return "Desconhecido"

def classify_format(url):
    """
    Classifica o formato provavel baseado na URL
    """
    url_lower = url.lower()
    
    if ".json" in url_lower or "api" in url_lower:
        return "JSON"
    elif ".csv" in url_lower:
        return "CSV"
    elif ".xls" in url_lower or ".xlsx" in url_lower:
        return "XLS"
    elif ".pdf" in url_lower:
        return "PDF"
    elif "transparencia" in url_lower:
        return "HTML"
    else:
        return "Variado"

def classify_quality(tipo_acesso, formato):
    """
    Classifica qualidade baseada no tipo de acesso e formato
    """
    if tipo_acesso == "API" and formato in ["JSON", "CSV"]:
        return "Alta"
    elif tipo_acesso == "API/Download" and formato in ["JSON", "CSV"]:
        return "Alta"
    elif tipo_acesso == "Download" and formato == "CSV":
        return "Media"
    elif formato in ["XLS", "PDF"]:
        return "Baixa"
    elif tipo_acesso == "Scraping":
        return "Baixa"
    else:
        return "Media"

if __name__ == "__main__":
    urls = [
        "http://dados.al.gov.br/",
        "https://www.cmnat.rn.gov.br/portal-da-transparencia",
        "http://api.tcm.ce.gov.br/",
        "https://transparencia.fortaleza.ce.gov.br/"
    ]
    
    print("=" * 80)
    print("CLASSIFICACAO DE URLs")
    print("=" * 80)
    
    for url in urls:
        tipo = classify_url(url)
        formato = classify_format(url)
        qualidade = classify_quality(tipo, formato)
        print(f"\nURL: {url}")
        print(f"  Tipo Acesso: {tipo}")
        print(f"  Formato: {formato}")
        print(f"  Qualidade: {qualidade}")
