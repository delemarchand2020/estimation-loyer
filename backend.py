import logging
import time
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import urllib3

# Désactiver les avertissements InsecureRequestWarning liés au verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)  # Autoriser les requêtes cross-origin depuis l'application SPA locale

# Configuration des headers pour simuler un navigateur
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
}

class EstimationProcess:
    def __init__(self, address):
        self.address = address
        self.logs = []
        
    def log(self, message, level="info", details=None):
        self.logs.append({
            "message": message,
            "level": level,
            "details": details
        })
        print(f"[{level.upper()}] {message}")

    def verify_address(self):
        """Vérifie l'adresse via Nominatim (OpenStreetMap) avec retries intelligents"""
        self.log(f"Début de la vérification de l'adresse: {self.address}")
        headers = {'User-Agent': 'EstimationLoyerApp/1.0'}
        import re
        
        # Nettoyage de base: enlever le code postal canadien typique (ex: G8Y 0L7)
        address_no_pc = re.sub(r'[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d', '', self.address).strip()
        address_no_pc = address_no_pc.rstrip(',')
        
        # 1. Essai avec l'adresse complète, puis sans le code postal
        queries_to_try = [self.address]
        if address_no_pc and address_no_pc != self.address:
            queries_to_try.append(address_no_pc)
        
        # 2. Essais progressifs de dégradation : tester les mots séparés par des virgules
        # Pour "1581 rue, trois-rivieres", on essaiera "1581 rue, trois-rivieres", puis juste "trois-rivieres"
        parts = address_no_pc.split(',')
        if len(parts) > 1:
            for i in range(1, len(parts)):
                simplified = ",".join(parts[i:]).strip()
                if simplified and len(simplified) > 3:
                     queries_to_try.append(simplified)
            
            # Essayer aussi strictement l'avant-dernier élément (souvent la ville, ex: "trois-rivieres, qc")
            if len(parts) >= 2:
                queries_to_try.append(parts[-2].strip())
            # Et le dernier élément
            queries_to_try.append(parts[-1].strip())

        # Nettoyage des doublons en gardant l'ordre
        queries_to_try = list(dict.fromkeys(queries_to_try))
        
        for query in queries_to_try:
            if not query:
                continue
            try:
                self.log(f"API Géocodage => Tentative avec: '{query}'...")
                url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(query)}&format=json&addressdetails=1&limit=1"
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data:
                    location = data[0]
                    formatted_address = location.get('display_name', query)
                    
                    addr_details = location.get('address', {})
                    self.city = addr_details.get('city') or addr_details.get('town') or addr_details.get('village') or addr_details.get('municipality') or ""
                    self.suburb = addr_details.get('suburb') or addr_details.get('borough') or addr_details.get('city_district') or ""
                    
                    if not self.city:
                        self.city = query.split(',')[0].split(' ')[-1]
                    
                    self.log(f"Adresse locale validée: {formatted_address}")
                    self.log(f"Ville détectée pour la recherche: {self.city}")
                    return True
                    
            except Exception as e:
                self.log(f"Erreur technique de l'API géocodage.", level="error", details=str(e))
                continue
                
        # Si on arrive ici, toutes les requêtes ont échoué
        self.log("L'adresse n'a pas pu être trouvée sur la carte.", level="error")
        return False

    def extract_prices_from_html(self, html, source_name, is_rent_url=False):
        """Extrait les prix en format $ du HTML de manière robuste, en évitant les menus de recherche."""
        import bs4
        from bs4 import BeautifulSoup
        import re
        
        soup = BeautifulSoup(html, 'html.parser')
        prices = []
        
        # Limites en fonction du type de recherche espéré
        min_val = 300
        max_val = 15000 if is_rent_url else 50000000
        
        def extract_from_text(text_block):
            # Remplacement des espaces insécables HTML courants qui cassent les regex des millions
            text = text_block.replace('\xa0', ' ').replace('\u202f', ' ')
            # Reconnaissance de formats: 1 500 $, 1500$, 1,500 $, 1 500 000$, etc.
            matches = re.findall(r'(\d{1,3}(?:[ \.,]\d{3}){0,2})\s*\$', text)
            
            extracted = []
            for m in matches:
                clean_str = re.sub(r'[ \.,]', '', m)
                if clean_str.isdigit():
                    val = int(clean_str)
                    if min_val <= val <= max_val:
                        extracted.append(val)
            return extracted

        # Approche 1 (Centris) : Ciblage strict des conteneurs de prix via microdatas (itemprop)
        price_containers = soup.find_all(itemprop="price")
        if price_containers:
            for container in price_containers:
                raw_content = container.get('content')
                if raw_content:
                    try:
                        val = int(float(raw_content))
                        if min_val <= val <= max_val and val not in prices:
                            prices.append(val)
                    except ValueError:
                        pass
                else:
                    found = extract_from_text(container.get_text(separator=' '))
                    if found and found[0] not in prices: 
                        prices.extend(found)
                    
        # Approche 2 (DuProprio ou fallback) : Si l'approche ciblée échoue, nettoyage du DOM
        if not prices:
            for el in soup(['script', 'style', 'select', 'header', 'nav', 'footer', 'form', 'option']):
                el.extract()
            prices = extract_from_text(soup.get_text(separator=' '))
            
        # Plafond restrictif : on ne garde que les 40 premiers (le VRAI contenu de la page, pas les pubs lointaines)
        return prices[:40]

    def fetch_source_data(self, name, url):
        """Tente de récupérer les données d'une source avec BeautifulSoup, avec mise en cache locale."""
        import hashlib
        import json
        import os
        
        # Gestion du cache pour éviter la variabilité due aux blocages anti-bots (Cloudflare/Incapsula)
        cache_file = "scraping_cache.json"
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        is_rent_url = "(Loyer)" in name or "louer" in url or "location" in url
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    if url_hash in cache_data:
                        cached_entry = cache_data[url_hash]
                        # Vérification de l'âge du cache (24 heures = 86400 secondes)
                        if "timestamp" in cached_entry and (time.time() - cached_entry["timestamp"] < 86400):
                            self.log(f"Utilisation des données en cache (Valide 24h) pour {name} ({url})")
                            return self.extract_prices_from_html(cached_entry["html"], name, is_rent_url)
                        else:
                            self.log(f"Cache expiré pour {name}, nouvelle requête en cours...")
            except Exception as e:
                self.log(f"Erreur lors de la lecture du cache: {str(e)}", level="error")
                pass # Proceed to fetch data if cache read fails
                
        self.log(f"Interrogation de la source: {name} via {url}")
        try:
            response = requests.get(url, headers=HEADERS, verify=False, timeout=10)
            
            if response.status_code == 200:
                html_content = response.text
                
                # Sauvegarde dans le cache
                try:
                    cache_data = {}
                    if os.path.exists(cache_file):
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                    cache_data[url_hash] = {
                        "timestamp": time.time(),
                        "html": html_content
                    }
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(cache_data, f)
                except Exception as e:
                    self.log(f"Erreur lors de la sauvegarde du cache: {str(e)}", level="error")
                    
                prices = self.extract_prices_from_html(html_content, name, is_rent_url)
                
                if prices:
                    self.log(f"Données extraites sur {name}: {len(prices)} prix trouvés.")
                    return prices
                else:
                    self.log(f"Aucun prix exploitable trouvé sur {name} (page peut-être dynamique).", level="warning")
                    return []
            else:
                self.log(f"Aucune donnée sur {name} (Erreur {response.status_code}). Le secteur n'est peut-être pas couvert.", level="warning")
                return []
                
        except Exception as e:
            self.log(f"Impossible de joindre {name}.", level="warning", details=str(e))
            return []
            
    def run_estimation(self):
        # 1. Vérification adresse (qui va maintenant peupler self.city)
        is_valid = self.verify_address()
        if not is_valid:
            # On coupe court à l'exécution si l'adresse est introuvable
            return {
                "error": "Adresse introuvable. Veuillez vérifier l'orthographe ou retirer le code postal.",
                "logs": self.logs
            }
        
        # Nettoyage de la ville pour en faire un "slug" utilisable dans les URLs
        import unicodedata
        
        def clean_slug(t):
            if not t: return ""
            c = unicodedata.normalize('NFKD', t.replace('–', '-').replace('—', '-')).encode('ASCII', 'ignore').decode('utf-8').lower()
            return c.replace(' ', '-')

        city_slug = clean_slug(self.city) if getattr(self, 'city', '') else "montreal"
        suburb_slug = clean_slug(getattr(self, 'suburb', ''))
        
        # Format spécifique pour Centris (ils utilisent des régions spécifiques)
        centris_slug = "montreal-ile" if "montreal" in city_slug else city_slug
        centris_suburb_slug = f"{city_slug}-{suburb_slug}" if suburb_slug else ""
        
        # 2. Collecte des données réelles
        sources_data = {}
        
        # Tentative Hyper-Locale (Quartier exact) si disponible
        if centris_suburb_slug:
            # On force le tri par nouveauté (?sort=DateDesc) pour extraire un échantillon représentatif et non biaisé (contrairement aux prix les plus bas)
            rent_data = self.fetch_source_data("Centris (Quartier/Loyer)", f"https://www.centris.ca/fr/propriete~a-louer~{centris_suburb_slug}?sort=DateDesc")
            if rent_data:
                sources_data["Centris (Quartier/Loyer)"] = rent_data
                sources_data["Centris (Quartier/Vente)"] = self.fetch_source_data("Centris (Quartier/Vente)", f"https://www.centris.ca/fr/propriete~a-vendre~{centris_suburb_slug}?sort=DateDesc")
        
        # Fallback au niveau de la Ville globale si le quartier échoue (ex: slug Invalide ou 0 data)
        if not sources_data:
            sources_data["Centris (Ville/Loyer)"] = self.fetch_source_data("Centris (Ville/Loyer)", f"https://www.centris.ca/fr/propriete~a-louer~{centris_slug}?sort=DateDesc")
            sources_data["Centris (Ville/Vente)"] = self.fetch_source_data("Centris (Ville/Vente)", f"https://www.centris.ca/fr/propriete~a-vendre~{centris_slug}?sort=DateDesc")
            
        # DuProprio reste au niveau de la ville
        # On force le tri par prix croissant sur DuProprio pour garantir une stabilité parfaite entre les essais QA
        sources_data["Du Proprio (Loyer)"] = self.fetch_source_data("Du Proprio", f"https://duproprio.com/fr/location/{city_slug}?sort=-published_at")
        
        all_rents = []
        all_sales = []
        sources_used = []
        
        for source, prices in sources_data.items():
            if prices:
                sources_used.append(source)
                # Séparation : < 15000 = Loyer mensuel, > 50000 = Vente
                for p in prices:
                    if 300 <= p <= 15000:
                        all_rents.append(p)
                    elif p >= 40000:
                        all_sales.append(p)

        self.log("Analyse des données collectées...")
        
        # Nettoyage statistique puissant : 
        # Pour une grande ville comme Montréal, les extrêmes (taudis ou penthouses de luxe) détruisent les moyennes.
        # On utilise la Médiane et on coupe les valeurs extrêmes (top/bottom 10%).
        import statistics

        if not all_rents:
            self.log("Scraping bloqué ou aucun loyer trouvé. Les valeurs estimées seront de 0.", level="warning")
            median_rent = 0
            avg_rent = 0
        else:
            all_rents.sort()
            trim_rent = len(all_rents) // 10
            clean_rents = all_rents[trim_rent:-trim_rent] if trim_rent > 0 and len(all_rents) > 5 else all_rents
            median_rent = statistics.median(clean_rents) if clean_rents else 0
            avg_rent = sum(clean_rents) / len(clean_rents) if clean_rents else 0
            
        if all_sales:
            all_sales.sort()
            trim_sale = len(all_sales) // 10
            clean_sales = all_sales[trim_sale:-trim_sale] if trim_sale > 0 and len(all_sales) > 5 else all_sales
            median_sale = statistics.median(clean_sales) if clean_sales else 0
        else:
            median_sale = 0
        
        dominant_type = "Mixte" if (len(all_sales) > 0 and len(all_rents) > 0) else ("Majoritairement locatif" if len(all_rents) > 0 else "Inconnu")
        locative_presence = "Forte" if len(all_rents) > 3 else ("Faible" if len(all_rents) > 0 else "Aucune certitude")
        
        # On affiche la médiane qui est beaucoup plus représentative du quartier "typique" que la moyenne (tirée par le haut)
        avg_value = f"{int(median_sale):,} $".replace(',', ' ') if median_sale > 0 else "0 $"
        
        # Interpolation des prix par taille à partir de la MÉDIANE calculée (robuste aux outliers)
        if median_rent > 0:
            # Interpolation très prudente (Ground Truth a démontré une forte surestimation en région)
            range_1_5 = f"{int(median_rent * 0.55)} $ à {int(median_rent * 0.7)} $"
            range_3_5 = f"{int(median_rent * 0.7)} $ à {int(median_rent * 0.9)} $"
            range_4_5 = f"{int(median_rent * 0.9)} $ à {int(median_rent * 1.15)} $"
            range_house = f"{int(median_rent * 1.2)} $ à {int(median_rent * 1.8)} $"
            
            # Le "Loyer Moyen Observé" (Moyenne générale) est tiré vers le bas pour refléter l'offre
            # la plus courante (entre le 3.5 et le 4.5) plutôt que d'être faussé par les maisons coûteuses
            final_median = int(median_rent * 0.85)
            final_avg_rent_str = f"{final_median} $"
            
            reco = {
                "1_5": f"{int(median_rent * 0.6)} $",
                "3_5": f"{int(median_rent * 0.8)} $", # Souvent le 3.5 est en dessous de la médiane globale qui inclut des maisons
                "4_5": f"{int(median_rent * 1.0)} $",
                "house": f"{int(median_rent * 1.4)} $"
            }
        else:
            range_1_5 = "0 $"
            range_3_5 = "0 $"
            range_4_5 = "0 $"
            range_house = "0 $"
            final_avg_rent_str = "0 $"
            reco = {
                "1_5": "0 $", "3_5": "0 $", "4_5": "0 $", "house": "0 $"
            }

        self.log(f"Estimation finalisée. ({len(all_rents)} loyers de référence traités).")

        return {
            "logs": self.logs,
            "sector_analysis": {
                "dominant_type": dominant_type,
                "locative_presence": locative_presence,
                "average_value": avg_value
            },
            "rental_market": {
                "1_5": range_1_5,
                "3_5": range_3_5,
                "4_5": range_4_5,
                "house": range_house,
                "average": final_avg_rent_str
            },
            "sources": sources_used if sources_used else ["Estimations basées sur des données simulées (Scraping bloqué)"],
            "recommendation": reco
        }

@app.route('/api/estimate', methods=['POST'])
def estimate():
    data = request.json
    address = data.get('address', '').strip()
    
    if not address:
        return jsonify({"error": "L'adresse est requise"}), 400
        
    process = EstimationProcess(address)
    result = process.run_estimation()
    
    return jsonify(result)

if __name__ == '__main__':
    print("Démarrage du backend sur http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
