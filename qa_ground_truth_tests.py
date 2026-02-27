import json
import time
import backend

ground_truth = [
    { "address": "14 JOHN-STROM RU, GRANBY, QC J2J0N9", "expected_rent": 1100.00 },
    { "address": "67 SACRE-COEUR-SAGUENAY RU, SACRE-COEUR-SAGUENAY, QC G0T1Y0", "expected_rent": 823.00 },
    { "address": "A-5 NOTRE-DAME RU, WARWICK, QC J0A1M0", "expected_rent": 1425.00 },
    { "address": "4-1841 KIROUAC RU, LONGUEUIL, QC J4G1T6", "expected_rent": 1310.00 },
    { "address": "3-240 GEORGES RU, LACHUTE, QC J8H2A1", "expected_rent": 850.00 }
]

def extract_rent_value(rent_str):
    if not rent_str or rent_str == "0 $" or rent_str == "-":
        return 0
    
    clean_str = rent_str.replace(" $", "").replace(" ", "")
    try:
        return int(clean_str)
    except ValueError:
        return 0

print("Démarrage de la comparaison avec les données réelles (Ground Truth)...\n")
report = []

for item in ground_truth:
    address = item["address"]
    expected = item["expected_rent"]
    
    print(f"Test pour l'adresse : {address}")
    print(f"Loyer réel attendu : {expected} $")
    
    try:
        ep = backend.EstimationProcess(address)
        res = ep.run_estimation()
        
        if "error" in res:
             print(f"Erreur API: {res['error']}\n")
             report.append({
                 "address": address,
                 "expected": expected,
                 "estimated": 0,
                 "difference": -expected,
                 "error": res['error']
             })
             continue
             
        # On prend la moyenne générale recommandée comme point de comparaison
        estimated_str = res.get("rental_market", {}).get("average", "0 $")
        estimated_val = extract_rent_value(estimated_str)
        
        diff = estimated_val - expected
        diff_percent = (diff / expected) * 100 if expected > 0 else 0
        
        print(f"Loyer estimé : {estimated_val} $")
        print(f"Différence : {diff} $ ({diff_percent:.2f}%)\n")
        
        report.append({
            "address": address,
            "expected": expected,
            "estimated": estimated_val,
            "difference": diff,
            "difference_percent": diff_percent,
            "sources": res.get("sources", [])
        })
    except Exception as e:
        print(f"Erreur système: {e}\n")

with open("qa_ground_truth_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=4)

print("Rapport généré : qa_ground_truth_report.json")

# Calcul statistiques globales
valid_results = [r for r in report if r.get("estimated", 0) > 0]
if valid_results:
    avg_diff_percent = sum(abs(r["difference_percent"]) for r in valid_results) / len(valid_results)
    print(f"\n--- Bilan ---")
    print(f"Adresses avec estimation réussie : {len(valid_results)}/{len(ground_truth)}")
    print(f"Marge d'erreur moyenne absolue : {avg_diff_percent:.2f}%")
else:
    print("\nAttention : Aucune estimation n'a abouti à un loyer supérieur à 0.")
