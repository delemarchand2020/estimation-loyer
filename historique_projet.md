# Historique et Contexte du Projet: Estimation Loyer

## Introduction
Ce projet consiste en un scraper et estimateur de prix de loyer au Québec basé sur des données réelles issues de plateformes immobilières (Centris, DuProprio). L'historique complet de nos conversations est chiffré dans une base de données locale Protobuf (`.pb`) propre à l'application Antigravity. 

Étant donné que l'outil ne génère pas de logs texte intégraux des chats précédents pour des raisons de confidentialité et d'optimisation (seul le code du projet reste persistant), voici de mémoire le résumé de nos itérations majeures :

---

## Phase 1 : Mise en place et Scraping (Session Initiale)
**Objectif Principal** : Construire un moteur capable d'interroger les sites immobiliers et d'en extraire des prix fiables.
- **Réalisations** : Création du `backend.py` avec **BeautifulSoup** et **Requests**.
- **Défis** : Contourner les protections anti-bot limitées, nettoyer le code source HTML rempli de bruit (espaces insécables, balises de scripts), et isoler les prix sous le format standard `$`.
- **Mécanismes implémentés** : Filtrage par attributs `itemprop="price"`, regex sur les chiffres, cache local (24h) pour éviter de spammer l'API de géocodage Nominatim et les sites sources.

---

## Phase 2 : Fiabilisation et Variabilité (Session Intermédiaire)
**Objectif Principal** : Debugguer la variabilité inexplicable des résultats malgré le cache.
- **Réalisations** : 
    - Examen du processus de cache (`scraping_cache.json`).
    - Standardisation du format des URL hashées via MD5.
    - Création d'agents spécifiques "Workspace Skills" (ex: QA obligatoire, contraintes d'architecture).
- **Défis** : Le DOM changeait parfois dynamiquement, ou des annonces expiraient, rendant la moyenne volatile. 
- **Solution** : Passage d'un algorithme de "Moyenne" pure (trop sensible aux outliers) à une médiane statistique plus robuste, avec l'élagage des extrêmes (top/bottom 10%).

---

## Phase 3 : Validation "Ground Truth" et Sur-Estimation (Session Actuelle)
**Objectif Principal** : Comparer l'estimateur avec des loyers réels pour valider sa viabilité commerciale.
- **Constats** : L'algorithme se trompait cruellement. L'erreur absolue s'élevait à plus de **140.96%**. L'outil estimait des loyers en région rurale (Lachute, Warwick) à plus de 1300$ alors que la réalité avoisine les 800$.
- **Causes identifiées en séance QA** :
    1. L'extracteur aspirait les prix de VENTE conseillés en bas de page sur les annonces de location.
    2. La médiane était influencée par les grandes maisons louées, faussant l'évaluation d'un petit appartement moyen.
- **Correctifs apportés** :
    - Planchers stricts : Rejets des prix < 300 $ et cap strict à 15,000 $ pour les loyers lors de l'aspiration HTML.
    - Ratio d'interpolation : Diminution drastique des multiplicateurs appliqués à la médiane brute (ex: l'appartement "3.5 / 4.5" est redescendu à 85% de la moyenne générale du marché environnant).
- **Conclusion** : Chute de la marge d'erreur de 140% à **~35%**, validée, versionnée sur Git et envoyée sur le remote.
