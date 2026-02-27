import time
import json
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Chemin absolu vers le fichier index.html
current_dir = os.path.dirname(os.path.abspath(__file__))
index_html_path = "file:///" + os.path.join(current_dir, "index.html").replace("\\", "/")

addresses = [
    "4958 avenue grosvenor montreal h3w2m1",
    "77 avenue sunnyside westmount",
    "1581 rue du vivandier, trois-rivières, QC G8Y0L7"
]

runs = 3
report = {}

# Configuration du navigateur (Mode Headless)
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')

print("Démarrage des tests E2E via le navigateur (Chrome Headless)...")
driver = webdriver.Chrome(options=options)

try:
    for addr in addresses:
        report[addr] = []
        print(f"\nTest de l'adresse: {addr}")
        
        for i in range(runs):
            driver.get(index_html_path)
            
            # Saisie de l'adresse
            input_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "addressInput"))
            )
            input_box.clear()
            input_box.send_keys(addr)
            
            # Clic estimer
            btn = driver.find_element(By.ID, "estimateBtn")
            btn.click()
            
            # Attendre que le loader disparaisse
            # Initialement il s'affiche, puis il disparaît (display: none)
            WebDriverWait(driver, 60).until(
                EC.invisibility_of_element_located((By.ID, "btnLoader"))
            )
            
            # Extraction des données UI
            # Analyse Secteur
            valeur_moyenne = driver.find_element(By.ID, "resAverageValue").text
            
            # Recommandations
            loyer_moyen_observe = driver.find_element(By.ID, "resAverage").text
            
            print(f"   [Run {i+1}] Valeur: {valeur_moyenne} | Loyer: {loyer_moyen_observe}")
            
            report[addr].append({
                "run": i+1,
                "valeur_ui": valeur_moyenne,
                "loyer_ui": loyer_moyen_observe
            })
            
            time.sleep(1)

finally:
    driver.quit()

with open("qa_report_from_ui.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=4)

print("\nReport generated: qa_report_from_ui.json")
