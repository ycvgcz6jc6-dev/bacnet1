# 0.4.0

- Phase 2 READ ONLY : collecte enrichie horodatée, textes d’état CPO sans substitutions, objets techniques conservés et export JSON privé via Ingress HA.
- Polling adaptatif 2 s / 30 s / 1800 s, expiration des vues après 15 s, timeout 15 s, limitation du débit et pauses sur erreurs.
- Conservation de la dernière bonne valeur, indisponibilité après expiration ; identifiants MQTT conservés.
- Interface sombre de supervision par zones et sous-systèmes, recherche, détails BACnet et export ; aucune commande.
- Mode Phase 1 conservé et sélectionnable. Tests automatisés avec transports simulés ; recette CPO distincte.

# 0.3.2

- Démarrage BACnet et inventaire local indépendants de la disponibilité MQTT.
- Nouvelle tentative MQTT en arrière-plan toutes les 15 secondes ; service facultatif `mqtt:want` déclaré.
- Rafraîchissement réel des métadonnées selon `metadata_refresh`.
- Version du journal de démarrage cohérente et image de base explicite pour les constructions Supervisor récentes.
- Inventaire, classification, candidats M-Bus/Modbus, identifiants MQTT et lecture seule conservés.

Validation locale : démarrage sans MQTT, inventaire sans broker incluant les objets techniques, expiration du cache et états inconnus. Validation sur CPO à effectuer après installation.
