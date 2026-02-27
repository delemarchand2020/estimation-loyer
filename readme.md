# Estimateur de Loyer Automatisé

Ce projet fournit une application web légère (SPA) propulsée par un backend Python, qui analyse l'adresse saisie par l'utilisateur pour estimer la viabilité d'un loyer sur le secteur. L'objectif est de vérifier la demande, le type de secteur et les tarifs moyens via l'agrégation de plusieurs sources.

## Fichiers Inclus
- `index.html` : L'interface utilisateur Web (Frontend SPA). Gère l'expérience utilisateur, l'affichage du rapport et des logs.
- `backend.py` : Serveur Flask servant d'API métier. Il contient toute la logique de requêtage avec `requests` (et contourne ainsi les limitations CORS du navigateur) pour interroger différentes sources.
- `plan.md` : Documente l'architecture, le développement et la feuille de route des corrections. 
- `readme.md` : Cette documentation technique.

## Installation et Utilisation

### Prérequis
- **Python 3.x**
- Les librairies suivantes sont nécessaires pour lancer le serveur local :
  ```bash
  pip install flask flask-cors requests beautifulsoup4
  ```

### Lancement
1. Exécutez le backend Python depuis l'invite de commande:
   ```bash
   python backend.py
   ```
   *Ce script lancera un serveur local sur le port 5000 (ex: http://127.0.0.1:5000).*

2. Ouvrez simplement le fichier `index.html` dans votre navigateur web moderne (Chrome, Firefox, Safari, Edge).

3. Entrez l'adresse de la propriété à évaluer dans la barre de recherche. L'analyse débutera et une fois complétée, affichera le rapport ainsi qu'un panneau déroulant d'exécutions (logs).

## Notes Techniques
- Les requêtes sortantes vers des sites tiers utilisent explicitement `verify=False` pour contourner certains problèmes de certificats.
- La complexité de scraper des sites d'annonces immobilières fortement protégés (captchas/WAF) signifie qu'une logique de repli (et des logs d'erreurs lisibles) est implémentée pour garantir la continuité du parcours utilisateur.
