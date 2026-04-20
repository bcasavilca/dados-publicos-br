#!/usr/bin/env python3
"""Debug - verificar estrutura do CSV"""
import requests

CSV_URL = 'https://dados.prefeitura.sp.gov.br/dataset/6588aef7-20ff-4cec-b1e1-6c06520240c0/resource/fd48b7dd-c5f1-4352-963f-f1e5ebc6d61b/download/contratos.csv'

r = requests.get(CSV_URL, timeout=120)
lines = r.text.split('\n')

print("Primeiras 10 linhas do CSV:")
print("=" * 80)
for i, line in enumerate(lines[:10]):
    print(f"{i}: {line}")
