import os
import time
import requests
import firebase_admin
from firebase_admin import db
import functions_framework
from bs4 import BeautifulSoup
import re

# =============================================================================
# PROJETO: PANDORA OS (V12-GOLD)
# MÓDULO: INGESTOR OSINT SOBERANO
# DESCRIÇÃO: Coleta multi-fonte (G1, Metrópoles, Agência BSB) com bypass 
#            de atividade para garantir alimentação constante do Heatmap.
# =============================================================================

if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

# Radar Tático: O que a Pandora busca nos textos
TACTICAL_KEYWORDS = {
    'danger': (r'tiroteio|assalto|furto|crime|preso|morte|homicídio|facada|polícia|pmdf|corpo|detido|roubo|investiga|presos|arma|disparos|baleado', 1.0),
    'traffic': (r'acidente|capotamento|atropelamento|colisão|congestionamento|trânsito|eptg|estrutural|br-020|sia|eixão|parado|km|der|detran', 0.6),
    'infra': (r'obras|interdição|alagamento|manutenção|caesb|energia', 0.4)
}

SOURCES = [
    {"name": "G1-DF", "url": "https://g1.globo.com/rss/df/"},
    {"name": "Metrópoles", "url": "https://www.metropoles.com/distrito-federal/seguranca/feed"},
    {"name": "Agência Brasília", "url": "https://www.agenciabrasilia.df.gov.br/feed/"}
]

def resolve_geo_df(local):
    """Mapeamento Geográfico Rápido para o DF"""
    l = local.lower()
    if "taguatinga" in l: return -15.8322, -48.0511
    if "ceilândia" in l or "ceilandia" in l: return -15.8174, -48.1130
    if "sia" in l: return -15.7941, -47.9584
    if "guará" in l or "guara" in l: return -15.8235, -47.9772
    if "gama" in l: return -16.0125, -48.0674
    if "estrutural" in l: return -15.7761, -47.9942
    if "eptg" in l: return -15.8123, -48.0134
    return -15.7941, -47.8825 # Centro de Brasília

def run_osint_pipeline():
    total_count = 0
    ref = db.reference('alertas_seguranca')
    
    print("🚀 PANDORA: Iniciando varredura tática...")

    for source in SOURCES:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 PandoraOS/12.0'}
            response = requests.get(source['url'], timeout=15, headers=headers)
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')
            
            print(f"📡 {source['name']}: {len(items)} itens encontrados.")

            source_inject_count = 0
            for item in items:
                titulo = item.title.text
                text_to_analyze = titulo.lower()
                matched = False

                # 1. FILTRO DE SEGURANÇA (CRÍTICO)
                for key, (pattern, weight) in TACTICAL_KEYWORDS.items():
                    if re.search(pattern, text_to_analyze):
                        local_match = re.search(r'(?:em|no|na|no\s+o|na\s+a)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', titulo)
                        local_raw = local_match.group(1) if local_match else "Distrito Federal"
                        lat, lng = resolve_geo_df(local_raw)
                        
                        ref.push({
                            'regiao': local_raw,
                            'mensagem': f"[{source['name']}] {titulo}",
                            'nivel_risco': weight,
                            'categoria': key,
                            'lat': lat,
                            'lng': lng,
                            'timestamp': int(time.time() * 1000)
                        })
                        print(f"✅ CRÍTICO: {titulo[:40]}")
                        total_count += 1
                        source_inject_count += 1
                        matched = True
                        break

                # 2. BYPASS DE ATIVIDADE (Garante dados informativos se não houver crimes)
                # Injeta até 3 notícias gerais por fonte para manter o mapa vivo
                if not matched and source_inject_count < 3:
                    lat, lng = -15.7941, -47.8825
                    ref.push({
                        'regiao': "Informativo DF",
                        'mensagem': f"[{source['name']}] {titulo}",
                        'nivel_risco': 0.4,
                        'categoria': 'info',
                        'lat': lat,
                        'lng': lng,
                        'timestamp': int(time.time() * 1000)
                    })
                    print(f"⚠️ BYPASS: {titulo[:40]}")
                    total_count += 1
                    source_inject_count += 1
                
        except Exception as e:
            print(f"❌ ERRO FONTE {source['name']}: {str(e)}")

    return f"Fim. {total_count} registros injetados.", 200

@functions_framework.http
def process_data(request):
    return run_osint_pipeline()
