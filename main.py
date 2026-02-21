import os
import time
import requests
import firebase_admin
from firebase_admin import db
import functions_framework
from bs4 import BeautifulSoup
import re

# =============================================================================
# PROJETO: PANDORA OS (V12) - NÚCLEO DE INGESTÃO OSINT TRIPLE-SOURCE
# FONTES: Metrópoles, Agência Brasília e G1 DF
# STATUS: RELEASE GOLD - CONGELADA
# =============================================================================

if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

# Cérebro Tático: Definição de Pesos e Cores
TACTICAL_KEYWORDS = {
    'danger': (r'tiroteio|assalto|furto|crime|preso|morte|homicídio|facada|polícia|pmdf', 1.0),
    'traffic': (r'acidente|capotamento|atropelamento|engavetamento|colisão|congestionamento', 0.6),
    'infra': (r'buraco|obras|interdição|alagamento|pista fechada|manutenção', 0.4)
}

SOURCES = [
    {"name": "G1-DF", "url": "https://g1.globo.com/rss/df/", "type": "xml"},
    {"name": "Metrópoles", "url": "https://www.metropoles.com/distrito-federal/seguranca/feed", "type": "xml"},
    {"name": "Agência Brasília", "url": "https://www.agenciabrasilia.df.gov.br/feed/", "type": "xml"}
]

@functions_framework.http
def process_data(request):
    request_json = request.get_json(silent=True)
    
    # SCAN AUTOMÁTICO (Via Cloud Scheduler)
    if not request_json or request_json.get('action') == 'scan':
        return run_osint_pipeline()

    # INGESTÃO MANUAL (Via CURL)
    return manual_ingestion(request_json)

def run_osint_pipeline():
    total_count = 0
    seen_titles = set()

    try:
        for source in SOURCES:
            response = requests.get(source['url'], timeout=15)
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item', limit=10) # 10 últimas notícias por fonte

            for item in items:
                titulo = item.title.text
                if titulo in seen_titles: continue
                
                risk_level = 0.3 
                category = "info"
                
                text_to_analyze = titulo.lower()
                for key, (pattern, weight) in TACTICAL_KEYWORDS.items():
                    if re.search(pattern, text_to_analyze):
                        risk_level = weight
                        category = key
                        break
                
                # Se for relevante, geolocaliza e salva
                if risk_level > 0.3:
                    partes = titulo.split(" em ")
                    local_raw = partes[-1] if len(partes) > 1 else "Distrito Federal"
                    
                    lat, lng = resolve_geo_df(local_raw)
                    
                    save_to_rtdb({
                        'regiao': local_raw,
                        'mensagem': f"[{source['name']}] {titulo}",
                        'nivel_risco': risk_level,
                        'categoria': category,
                        'lat': lat,
                        'lng': lng,
                        'timestamp': int(time.time() * 1000)
                    })
                    seen_titles.add(titulo)
                    total_count += 1
        
        return f"Pipeline V12-Gold: {total_count} alertas injetados.", 200
    except Exception as e:
        return f"Erro na Pipeline: {str(e)}", 500

def resolve_geo_df(localizacao):
    """Geolocalização Nominatim para o contexto de Brasília"""
    try:
        local_clean = localizacao.split(",")[0].split("-")[0].strip()
        query = f"{local_clean}, Distrito Federal, Brazil"
        url = "https://nominatim.openstreetmap.org/search"
        headers = {'User-Agent': 'Pandora_OS_Sovereign_v12'}
        
        time.sleep(1.1) # Respeito ao limite da API
        res = requests.get(url, params={'q': query, 'format': 'json', 'limit': 1}, headers=headers)
        data = res.json()
        
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except:
        pass
    return -15.7941, -47.8825 

def manual_ingestion(data):
    regiao = data.get('regiao', 'Distrito Federal')
    lat, lng = data.get('lat'), data.get('lng')
    if lat is None or lng is None: lat, lng = resolve_geo_df(regiao)

    save_to_rtdb({
        'regiao': regiao,
        'mensagem': data.get('mensagem', 'Alerta manual'),
        'nivel_risco': float(data.get('nivel_risco', 0.5)),
        'lat': lat,
        'lng': lng,
        'timestamp': int(time.time() * 1000)
    })
    return "OK", 200

def save_to_rtdb(payload):
    ref = db.reference('alertas_seguranca')
    ref.push(payload)
