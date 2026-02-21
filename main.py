import time
import requests
import firebase_admin
from firebase_admin import db
import functions_framework
import re

VERSION_TAG = "V15-SCRAPING-BYPASS"

if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://airy-rock-462023-h2-default-rtdb.firebaseio.com/' 
    })

# URLs alternativas para evitar o bloqueio direto do RSS principal
SOURCES = [
    {"name": "G1-DF", "url": "https://g1.globo.com/rss/df/"},
    {"name": "Metrópoles", "url": "https://www.metropoles.com/distrito-federal/feed"},
    {"name": "Agência Brasília", "url": "https://www.agenciabrasilia.df.gov.br/feed/"}
]

def get_with_retry(url):
    """Tenta baixar o conteúdo simulando diferentes origens"""
    headers_list = [
        {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'},
        {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'},
        {'User-Agent': 'Googlebot/2.1 (+http://www.google.com/bot.html)'} # Às vezes fingir ser o Google Bot libera o RSS
    ]
    
    for headers in headers_list:
        try:
            # Adicionamos um parâmetro aleatório na URL para evitar cache do servidor deles
            bust_url = f"{url}?t={int(time.time())}"
            response = requests.get(bust_url, headers=headers, timeout=10)
            if response.status_code == 200 and len(response.text) > 1000:
                return response.text
        except:
            continue
    return None

@functions_framework.http
def process_data(request):
    print(f"🛰️ [RADAR] Versão: {VERSION_TAG}")
    ref = db.reference('alertas_seguranca')
    total_count = 0

    for source in SOURCES:
        content = get_with_retry(source['url'])
        
        if content:
            print(f"✅ {source['name']} ACESSADO | {len(content)} bytes")
            # Busca os itens no XML/HTML
            items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL | re.IGNORECASE)
            
            for i, item_content in enumerate(items):
                if i >= 5: break
                title_match = re.search(r'<title>(.*?)</title>', item_content, re.IGNORECASE | re.DOTALL)
                if title_match:
                    titulo = title_match.group(1).replace('<![CDATA[', '').replace(']]>', '').strip()
                    
                    # REGEX para achar menção a bairros do DF no título
                    regiao = "Distrito Federal"
                    for bairro in ["Taguatinga", "Ceilândia", "Guará", "Gama", "SIA", "Asa Norte", "Asa Sul"]:
                        if bairro.lower() in titulo.lower():
                            regiao = bairro
                            break

                    ref.push({
                        'regiao': regiao.upper(),
                        'mensagem': f"[{source['name']}] {titulo}",
                        'nivel_risco': 1.0 if any(k in titulo.lower() for k in ['tiro', 'morte', 'preso', 'crime']) else 0.7,
                        'categoria': 'seguranca',
                        'lat': -15.8322 if "Taguatinga" in regiao else -15.7941,
                        'lng': -48.0511 if "Taguatinga" in regiao else -47.8825,
                        'timestamp': int(time.time() * 1000)
                    })
                    total_count += 1
        else:
            print(f"❌ {source['name']} BLOQUEADO TOTALMENTE")

    return f"Status: {VERSION_TAG} | Injetados: {total_count}", 200
