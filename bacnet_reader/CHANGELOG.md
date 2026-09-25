# 0.3.2

- Démarrage BACnet et inventaire local indépendants de la disponibilité MQTT.
- Nouvelle tentative MQTT en arrière-plan toutes les 15 secondes ; service facultatif `mqtt:want` déclaré.
- Rafraîchissement réel des métadonnées selon `metadata_refresh`.
- Version du journal de démarrage cohérente et image de base explicite pour les constructions Supervisor récentes.
- Inventaire, classification, candidats M-Bus/Modbus, identifiants MQTT et lecture seule conservés.

Validation locale : démarrage sans MQTT, inventaire sans broker incluant les objets techniques, expiration du cache et états inconnus. Validation sur CPO à effectuer après installation.
