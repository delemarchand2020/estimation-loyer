import backend
import time
import json

addresses = [
    "4958 avenue grosvenor montreal h3w2m1",
    "77 avenue sunnyside westmount",
    "1581 rue du vivandier, trois-rivières, QC G8Y0L7"
]

runs = 3
report = {}

for addr in addresses:
    report[addr] = []
    for i in range(runs):
        ep = backend.EstimationProcess(addr)
        res = ep.run_estimation()
        
        valeur = res.get("sector_analysis", {}).get("average_value")
        loyer = res.get("rental_market", {}).get("average")
        
        report[addr].append({
            "run": i+1,
            "valeur": valeur,
            "loyer": loyer
        })
        time.sleep(1)

with open("qa_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=4)
print("Report generated: qa_report.json")
