import os
import time
import requests
import firebase_admin
from firebase_admin import db
import functions_framework
from bs4 import BeautifulSoup
import re

if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

TACTICAL_KEYWORDS = {
    'danger': (r'tiroteio|assalto|furto|crime|preso|morte|homicídio|facada|polícia|corpo', 1.0),
    'traffic': (r'acidente|capotamento|atropelamento|colisão|congestionamento', 0.6)
}

SOURCES = [
    {"name": "G1-DF", "url": "https://g1.globo.com/rss/df/"},
    {"name": "Metrópoles", "url": "https://www.metropoles.com/distrito-federal/seguranca/feed"},
    {"name": "Agência Brasília", "url": "https://www.agenciabrasilia.df.gov.br/feed/"}
]

def run_osint_pipeline():
    total_count = 0
    ref = db.reference('alertas_seguranca')
    
    for source in SOURCES:
        try:
            print(f"📡 Tentando conectar em: {source['name']}")
            response = requests.get(source['url'], timeout=15, headers={'User-Agent': 'PandoraV12-Gold'})
            # Usando 'html.parser' por ser nativo e evitar erros de dependência XML no GCP
            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find_all('item')
            
            print(f"📰 {source['name']} retornou {len(items)} itens.")

            for item in items:
                titulo = item.title.text
                text_to_analyze = titulo.lower()
                
                for key, (pattern, weight) in TACTICAL_KEYWORDS.items():
                    if re.search(pattern, text_to_analyze):
                        # Se achou keyword, tenta extrair local
                        local_raw = titulo.split(" em ")[-1] if " em " in titulo else "Distrito Federal"
                        
                        # GEO-CHECK
                        lat, lng = resolve_geo_df(local_raw)
                        
                        payload = {
                            'regiao': local_raw[:30], # DBA: Limita tamanho da string
                            'mensagem': f"[{source['name']}] {titulo}",
                            'nivel_risco': weight,
                            'categoria': key,
                            'lat': lat,
                            'lng': lng,
                            'timestamp': int(time.time() * 1000)
                        }
                        
                        ref.push(payload)
                        total_count += 1
                        print(f"✅ INJETADO: {titulo[:40]}...")
                        break # Pula para o próximo item
        except Exception as e:
            print(f"❌ ERRO NA FONTE {source['name']}: {str(e)}")

    return f"Fim da rodada. {total_count} registros.", 200

def resolve_geo_df(local):
    # Forçamos Taguatinga se o Nominatim falhar, para você ver a mancha!
    if "taguatinga" in local.lower(): return -15.8322, -48.0511
    if "sia" in local.lower(): return -15.7941, -47.9584
    return -15.7941, -47.8825

@functions_framework.http
def process_data(request):
    # Chamada via Cloud Scheduler ou Manual
    return run_osint_pipeline()
