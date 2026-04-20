# Diagnóstico - Backend Render Offline

## Data: 2026-04-20 15:30

## Problema
Backend em `dados-publicos-br.onrender.com` retornando 404 em todas as rotas:
- ❌ `/health` → 404
- ❌ `/buscar?q=saude` → 404
- ❌ Raiz provavelmente → 404

## Possíveis Causas

### 1. Serviço Dormiu (Mais Provável)
- Render free tier "dorme" após período de inatividade
- Pode levar 30-60s para "acordar" no primeiro acesso
- Mas deveria responder, não dar 404

### 2. Deploy Quebrou
- Último deploy pode ter falhado
- Aplicação não iniciou corretamente
- Logs mostrariam erro

### 3. Rotas Não Definidas
- Código pode estar rodando mas sem rotas mapeadas
- Problema no Flask/FastAPI

### 4. Banco de Dados Desconectado
- API inicia mas falha ao conectar no banco
- Pode retornar 404 ou 500

## Ações Recomendadas

### Ação 1: Verificar Dashboard do Render
1. Acessar https://dashboard.render.com
2. Verificar serviço `dados-publicos-br`
3. Checar:
   - Status: Healthy ou Crashed?
   - Último deploy: Quando?
   - Logs: Erros recentes?

### Ação 2: Tentar Wake Up
```bash
curl -I https://dados-publicos-br.onrender.com/
```
Esperar 60s e tentar novamente

### Ação 3: Verificar Logs
No dashboard do Render, ver logs:
- Application startup logs
- Error logs
- Database connection logs

### Ação 4: Forçar Redeploy
Se logs mostrarem erro:
1. Trigger deploy manual
2. Ou fazer commit vazio no GitHub:
```bash
git commit --allow-empty -m "trigger: redeploy"
git push
```

## Código API Original

O backend usava:
```python
# api.py ou similar
from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/health')
def health():
    return {'status': 'ok'}

@app.route('/buscar')
def buscar():
    q = request.args.get('q')
    # ... busca no banco
```

Se estava funcionando antes, provavelmente é:
- Serviço dormiu e não acordou
- Ou banco PostgreSQL desconectou

## Próximos Passos

1. [ ] Verificar dashboard Render
2. [ ] Verificar logs de erro
3. [ ] Testar conexão com banco Railway
4. [ ] Se necessário, fazer redeploy
5. [ ] Verificar variáveis de ambiente (DATABASE_URL)
