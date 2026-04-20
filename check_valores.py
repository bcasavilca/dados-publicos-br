import requests

CSV_URL = 'https://dados.prefeitura.sp.gov.br/dataset/6588aef7-20ff-4cec-b1e1-6c06520240c0/resource/fd48b7dd-c5f1-4352-963f-f1e5ebc6d61b/download/contratos.csv'

print("Baixando amostra...")
r = requests.get(CSV_URL, timeout=60)
lines = r.text.split('\n')

# Pular até header
header_line = 4
for i, line in enumerate(lines[:10]):
    if 'Contrato' in line:
        header_line = i
        break

header = lines[header_line].split(';')
print(f"\nHeader ({len(header)} colunas):")
for i, h in enumerate(header):
    print(f"  {i}: {h}")

# Mostrar primeiras 10 linhas de dados
print("\nPrimeiros 10 registros (colunas 8 e 9):")
print("-" * 80)
for i, line in enumerate(lines[header_line+1:header_line+11], 1):
    if not line.strip():
        continue
    cols = line.split(';')
    if len(cols) > 9:
        fornecedor = cols[8][:40] if len(cols) > 8 else 'N/A'
        valor = cols[9] if len(cols) > 9 else 'N/A'
        print(f"{i}. Fornecedor: {fornecedor}")
        print(f"   Valor raw: '{valor}'")
        print()

print("\nVerificando formatos de valor:")
valores = []
for line in lines[header_line+1:header_line+101]:
    if not line.strip():
        continue
    cols = line.split(';')
    if len(cols) > 9:
        valores.append(cols[9])

# Analisar formatos
print("\nAmostra de valores brutos:")
for v in valores[:10]:
    print(f"  '{v}'")
