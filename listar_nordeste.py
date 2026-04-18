#!/usr/bin/env python3
# Lista todos os portais do Nordeste

import csv

ufs_nordeste = ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE']

with open('data/catalogos.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    portais = [r for r in reader if r['UF'] in ufs_nordeste]

print(f"# Portais do Nordeste ({len(portais)} portais)\n")

for i, row in enumerate(portais, 1):
    print(f"{i}. **{row['Titulo']}** ({row['UF']})")
    print(f"   {row['URL']}")
    print(f"   Tipo: {row['TipoFonte']} | Formato: {row['Formato']} | Qualidade: {row['Qualidade']}")
    print()
