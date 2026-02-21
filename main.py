import time
import requests
import firebase_admin
from firebase_admin import db
import functions_framework
import re

# TAG DE VERSÃO PARA VOCÊ VER NO CURL
VERSION_TAG = "V13-BRUTE-FORCE-GOLD-001"

if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

SOURCES = [
    {"name": "G1-DF", "url": "https://g1.globo.com/rss/df/"},
    {"name": "Metrópoles", "url": "https://www.metropoles.com/distrito-federal/seguranca/feed"},
    {"name": "Agência Brasília", "url": "https://www.agenciabrasilia.df.gov.br/feed/"}
]

@functions_framework.http
def process_data(request):
    # LOG IMEDIATO PARA SABER QUE O DEPLOY RODOU
    print(f"🔥 [DEPLOY OK] Executando versão: {VERSION_TAG}")
    
    total_count = 0
    ref = db.reference('alertas_seguranca')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    results_summary = []

    for source in SOURCES:
        try:
            print(f"📡 Tentando conectar em: {source['name']}")
            response = requests.get(source['url'], timeout=15, headers=headers)
            content = response.text
            
            # Verificamos se o conteúdo veio
            size = len(content)
            print(f"📦 {source['name']} retornou {size} caracteres.")

            # Busca bruta de itens
            items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL | re.IGNORECASE)
            if not items:
                items = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL | re.IGNORECASE)

            source_count = 0
            for i, item_content in enumerate(items):
                if i >= 3: break # Garantimos 3 de cada fonte
                
                title_match = re.search(r'<title>(.*?)</title>', item_content, re.IGNORECASE | re.DOTALL)
                if title_match:
                    titulo = title_match.group(1).replace('<![CDATA[', '').replace(']]>', '').strip()
                    
                    # GRAVAÇÃO DIRETA NO FIREBASE
                    ref.push({
                        'regiao': "Injeção Forçada V13",
                        'mensagem': f"[{source['name']}] {titulo}",
                        'nivel_risco': 0.9,
                        'categoria': 'seguranca',
                        'lat': -15.8322, # Taguatinga para você ver no mapa
                        'lng': -48.0511,
                        'timestamp': int(time.time() * 1000)
                    })
                    total_count += 1
                    source_count += 1
            
            results_summary.append(f"{source['name']}: {source_count} itens")
                
        except Exception as e:
            print(f"❌ ERRO EM {source['name']}: {str(e)}")

    # RETORNO COM A TAG DE VERSÃO
    return f"Versão: {VERSION_TAG} | {total_count} registros injetados. Detalhes: {results_summary}", 200
