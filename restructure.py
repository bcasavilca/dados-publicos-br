#!/usr/bin/env python3
"""
RESTRUCTURE SCRIPT — FASE 2
Executa reestruturação segura com backup automático
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("🚀 FASE 2: REESTRUTURAÇÃO SEGURA")
print("=" * 70)
print()

# Config
ROOT = Path(".")
BACKUP_DIR = ROOT / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def backup_file(src):
    """Cria backup antes de qualquer operação"""
    if src.exists():
        dst = BACKUP_DIR / src.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        log(f"📦 Backup: {src}")

def create_structure():
    """Cria estrutura de pastas"""
    log("Criando estrutura de pastas...")
    
    dirs = [
        # Core Engine
        "core/engine",
        "core/analysis", 
        "core/graph",
        
        # Data Layer
        "data/raw",
        "data/processed",
        "data/pipelines",
        "data/scrapers",
        
        # API Layer
        "api/catalog",
        "api/investigation",
        
        # Frontend (mantém)
        "frontend/v1",
        "frontend/v2",
        "frontend/dashboard",
        
        # Experimental
        "experiments/v32",
        "experiments/v33",
        "experiments/v34",
        "experiments/v37",
        "experiments/v40",
        "experiments/v41",
        "experiments/simulations",
        
        # Legacy
        "legacy/old_scripts",
        
        # Deploy
        "deploy/railway",
        "deploy/vercel",
        "deploy/render",
        
        # Tests
        "tests/unit",
        "tests/integration",
    ]
    
    for d in dirs:
        (ROOT / d).mkdir(parents=True, exist_ok=True)
        log(f"  ✅ {d}")

def copy_data_layer():
    """Copia DATA LAYER"""
    log("\n📁 FASE 2A: DATA LAYER")
    
    mappings = [
        ("scrapers/amostra_csv.py", "data/scrapers/"),
        ("scrapers/buscar_sp_datasets.py", "data/scrapers/"),
        ("scrapers/fortaleza_scraper.py", "data/scrapers/"),
        ("scrapers/inspecionar_dataset.py", "data/scrapers/"),
        ("scrapers/inspecionar_schema.py", "data/scrapers/"),
        ("scripts/ingest.py", "data/pipelines/"),
        ("scripts/normalizador.py", "data/pipelines/"),
        ("scripts/portal_discovery.py", "data/scrapers/"),
        ("scripts/dadosgov_crawler.py", "data/scrapers/"),
        ("scripts/generate_baseline.py", "data/pipelines/"),
        ("listar_nordeste.py", "data/scrapers/"),
        ("temporal.py", "data/pipelines/"),
    ]
    
    for src, dst in mappings:
        src_path = ROOT / src
        if src_path.exists():
            backup_file(src_path)
            dst_path = ROOT / dst / src_path.name
            shutil.copy2(src_path, dst_path)
            log(f"  ✅ {src} → {dst}")

def copy_core_engine():
    """Copia CORE ENGINE"""
    log("\n🔬 FASE 2B: CORE ENGINE")
    
    mappings = [
        ("motor_regras.py", "core/engine/"),
        ("motor_regras_v2.py", "core/engine/"),
        ("cruzador.py", "core/analysis/"),
        ("scripts/cerebro_digital.py", "core/analysis/"),
    ]
    
    for src, dst in mappings:
        src_path = ROOT / src
        if src_path.exists():
            backup_file(src_path)
            dst_path = ROOT / dst / src_path.name
            shutil.copy2(src_path, dst_path)
            log(f"  ✅ {src} → {dst}")

def copy_api_layer():
    """Copia API LAYER (unificado)"""
    log("\n🔌 FASE 2C: API LAYER")
    
    # API de catálogo (produção)
    catalog_apis = [
        ("api/buscar.py", "api/catalog/"),
        ("api/index.py", "api/catalog/"),
    ]
    
    # API de investigação
    investigation_apis = [
        ("scripts/api_cerebro.py", "api/investigation/cerebro.py"),
    ]
    
    for src, dst in catalog_apis:
        src_path = ROOT / src
        if src_path.exists():
            backup_file(src_path)
            dst_path = ROOT / dst / Path(src).name
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            log(f"  ✅ {src} → {dst}")

def move_experimental():
    """Move código experimental"""
    log("\n🧪 FASE 2D: EXPERIMENTAL")
    
    experimental_files = [
        ("v32_grafo_competitivo.sh", "experiments/v32/"),
        ("v32_simples.sh", "experiments/v32/"),
        ("v33_nao_destilado.sh", "experiments/v33/"),
        ("v34_baseline_temporal.sh", "experiments/v34/"),
        ("v34_execucao.py", "experiments/v34/"),
        ("v36_execucao.py", "experiments/v34/"),
        ("v37_causal.sh", "experiments/v37/"),
        ("v371_calibracao.sh", "experiments/v37/"),
        ("v40_structural.sh", "experiments/v40/"),
        ("v40_taxonomia.sh", "experiments/v40/"),
        ("v41_corrigido.sh", "experiments/v41/"),
        ("sim_v2.py", "experiments/simulations/"),
        ("simulacao_corrigida.sh", "experiments/simulations/"),
        ("simulacao_fraude.sh", "experiments/simulations/"),
    ]
    
    for src, dst in experimental_files:
        src_path = ROOT / src
        if src_path.exists():
            backup_file(src_path)
            dst_path = ROOT / dst / src_path.name
            shutil.copy2(src_path, dst_path)
            log(f"  ✅ {src} → {dst}")

def move_legacy():
    """Move código legado"""
    log("\n📦 FASE 2E: LEGACY")
    
    legacy_files = [
        ("api_search.py", "legacy/"),
        ("api_search_simples.py", "legacy/"),
        ("api_sem_banco.py", "legacy/"),
        ("api_cruzamento.py", "legacy/"),
    ]
    
    for src, dst in legacy_files:
        src_path = ROOT / src
        if src_path.exists():
            backup_file(src_path)
            dst_path = ROOT / dst / src_path.name
            shutil.copy2(src_path, dst_path)
            log(f"  ✅ {src} → {dst}")

def create_init_files():
    """Cria __init__.py em todos os módulos"""
    log("\n📝 FASE 2F: CRIANDO __init__.py")
    
    modules = [
        "core", "core/engine", "core/analysis", "core/graph",
        "data", "data/pipelines", "data/scrapers",
        "api", "api/catalog", "api/investigation",
    ]
    
    for mod in modules:
        init_file = ROOT / mod / "__init__.py"
        init_file.write_text(f'"""{mod.replace("/", ".")} module."""\n')
        log(f"  ✅ {mod}/__init__.py")

def create_gateway():
    """Cria gateway unificado de APIs"""
    log("\n🌐 FASE 2G: GATEWAY API")
    
    gateway_code = '''#!/usr/bin/env python3
"""
API Gateway Unificado
Roteia entre API de Catálogo e API de Investigação
"""

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Import APIs
from api.catalog import buscar as catalog_buscar
from api.investigation import cerebro as investigation_cerebro

@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "services": {
            "catalog": "/api/catalog/*",
            "investigation": "/api/investigation/*"
        }
    })

# Catalog Routes
@app.route('/api/buscar')
def buscar():
    return catalog_buscar.buscar(request.args.get('q'))

# Investigation Routes  
@app.route('/api/analise')
def analise():
    return investigation_cerebro.analisar(request.json)

if __name__ == '__main__':
    app.run(debug=True)
'''
    
    gateway_path = ROOT / "api/gateway.py"
    gateway_path.write_text(gateway_code)
    log(f"  ✅ api/gateway.py criado")

def main():
    """Executa reestruturação completa"""
    
    # Criar backup
    log("Criando diretório de backup...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Executar fases
    create_structure()
    copy_data_layer()
    copy_core_engine()
    copy_api_layer()
    move_experimental()
    move_legacy()
    create_init_files()
    create_gateway()
    
    log("\n" + "=" * 70)
    log("✅ REESTRUTURAÇÃO COMPLETA")
    log(f"📦 Backup em: {BACKUP_DIR}")
    log("=" * 70)
    log("\nPRÓXIMOS PASSOS:")
    log("1. Validar imports (python -m api.catalog)")
    log("2. Testar gateway (python api/gateway.py)")
    log("3. Commit: git add . && git commit -m 'restructure: fase 2'")
    log("4. Deploy seguro")

if __name__ == "__main__":
    main()
