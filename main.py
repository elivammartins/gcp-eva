import time
import requests
import firebase_admin
from firebase_admin import db
import functions_framework
import re

# PANDORA OS V12 - GOLD RELEASE (BRUTE FORCE EDITION)
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

SOURCES = [
    {"name": "G1-DF", "url": "https://g1.globo.com/rss/df/"},
    {"name": "Metrópoles", "url": "https://www.metropoles.com/distrito-federal/seguranca/feed"},
    {"name": "Agência Brasília", "url": "https://www.agenciabrasilia.df.gov.br/feed/"}
]

def run_osint_pipeline():
    total_count = 0
    ref = db.reference('alertas_seguranca')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    print("🛰️ PANDORA: Iniciando extração Brute Force...")

    for source in SOURCES:
        try:
            response = requests.get(source['url'], timeout=15, headers=headers)
            content = response.text # Lemos como texto bruto
            
            print(f"📡 {source['name']} | Status: {response.status_code} | Tamanho: {len(content)} chars")

            # REGEX para pegar o conteúdo entre <title> e </title> que esteja dentro de um <item>
            # Buscamos o padrão de blocos <item>...</item>
            items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL | re.IGNORECASE)
            
            if not items:
                # Fallback para Atom (Agência Brasília usa muito)
                items = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL | re.IGNORECASE)

            print(f"📰 {source['name']}: {len(items)} blocos brutos encontrados.")

            for i, item_content in enumerate(items):
                if i >= 5: break
                
                # Extrai o título do bloco bruto
                title_match = re.search(r'<title>(.*?)</title>', item_content, re.IGNORECASE | re.DOTALL)
                
                if title_match:
                    # Limpa possíveis tags CDATA
                    titulo = title_match.group(1).replace('<![CDATA[', '').replace(']]>', '').strip()
                    
                    ref.push({
                        'regiao': "Distrito Federal",
                        'mensagem': f"[{source['name']}] {titulo}",
                        'nivel_risco': 0.8,
                        'categoria': 'info',
                        'lat': -15.7941,
                        'lng': -47.8825,
                        'timestamp': int(time.time() * 1000)
                    })
                    total_count += 1
                
        except Exception as e:
            print(f"❌ ERRO {source['name']}: {str(e)}")

    return f"Fim da rodada. {total_count} registros injetados.", 200

@functions_framework.http
def process_data(request):
    return run_osint_pipeline()
