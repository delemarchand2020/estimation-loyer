# Plan de Développement - Estimateur de loyer automatisé

Ce fichier trace le plan de développement et de maintenance de l'application.

## Architecture
Une solution compacte axée sur deux fichiers principaux pour éviter la configuration d'un environnement lourd :
1. **`index.html`** : Une application SPA (Single Page Application) gérant l'interface, les appels à l'API et l'affichage des logs.
2. **`backend.py`** : Une API Python utilisant Flask et gérant les requêtes web (contournement CORS, requêtage direct via `requests.get(verify=False)`).

## Spécifications Fonctionnelles
- L'utilisateur entre une adresse. L'application vérifie globalement son existence.
- Le backend effectue une série de requêtes vers les plateformes cibles (Centris, Du Proprio, Les PAC, StatsCan) pour récupérer des évaluations immobilières et locatives.
- Pendant le traitement, ou en réponse de celui-ci, le frontend reçoit une trace d'exécution.
- La trace affiche en clair: `Étape 1 réussie`, `Étape 2: Source DuProprio indisponible`. 
- Si une case "version avancée" est cochée, l'UI montre la trace d'erreur Python (stacktrace) formatée.
- Le résultat comprend l'analyse du secteur (Type, Présence Locatif, Valeur Moyenne), le marché locatif, les sources, et une recommandation finale d'investissement locatif prudent.

## Étapes de code
1. Initialisation projet (Création de `index.html`, `backend.py`, `plan.md`, `readme.md`). [Terminé]
2. Coder la logique du `backend.py` (Routage Flask, CORS, fonction scraping `requests`).
3. Coder l'Interface `index.html` avec requêtage `fetch` JS.
4. Intégrer la logique de logs et la bascule technique/simple.
5. Tests locaux.
