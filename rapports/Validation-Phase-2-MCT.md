# BACnet Reader MCT — validation Phase 2

Validation sur Home Assistant MCT le 26 septembre 2026, vers 22 h 03 (Europe/Brussels).

## Livraison

- Version 0.4.0 installée et démarrée dans Home Assistant ; sauvegarde de la version précédente demandée par l'option de mise à jour.
- Dépôt : https://github.com/ycvgcz6jc6-dev/bacnet1/commit/d9224f3dd15d1afeb2936ff3887efc25bd21ca61
- Console : https://8j9ryyq5jetclrwgifusjxfxjjgxmofo.ui.nabu.casa/app/bb4bdef3_bacnet-reader
- Lecture seule BACnet ; aucune commande, acquittement ou modification d'horaire effectué.
- Fonctions antérieures conservées. MQTT indépendant du démarrage BACnet.

## Résultats réels

Le CPO Honeywell CPO-PC400, TE_01_CH, Device 130, répond à l'adresse 192.168.0.249. MQTT est connecté. L'inventaire contient 358 objets et les 261 points de valeur sont disponibles. Les entités et leurs valeurs ont été vérifiées dans Home Assistant sur l'appareil TE_01_CH.

La collecte enrichie s'est terminée à 22:02:57 : aucune propriété en attente. Les données exportables comprennent les identifiants bruts, les noms/descriptions disponibles, unités, statusFlags, reliability, outOfService, ainsi que :

- 19 objets multistates avec stateText ;
- 109 objets binaires avec libellés ;
- 7 horaires : Gen_AntiGrippage, Horaire_ECS, Bloc_A, Bloc_B, Bloc_C_D, Bloc_Extension, GPGE1 ;
- 3 classes de notification : URGENT, HIGH, LOW ;
- 28 event-enrollment ;
- 2 vues structurées : GPGE1_Salle_A et Raditaeur.

Exemple de sémantique vérifiée : multi-state-value:4, Rad_BlocA_Mode, valeur brute 7, libellé CPO « Arrêt par la temp  ex ». Aucun sens supplémentaire attribué.

## Vérifications

14 tests automatisés passés avant publication : fonctionnement sans MQTT, conservation de la dernière valeur et de son âge lors d'une erreur, expiration des vues actives, équité du polling, libellés strictement issus du CPO, propriétés absentes, timeout et protection de charge, inventaire technique et restriction Ingress.

En production : démarrage 0.4.0, connexion MQTT, inventaire complet, entités HA, collecte progressive sans interruption des valeurs, recherche et navigation de la console vérifiés. Un point visible est resté récent pendant qu'un point hors vue conservait sa lecture précédente sur une observation de 19 secondes. Le diagnostic est également revenu à zéro point actif lors de la sortie de la console. Les cadences configurées sont 2 s / 30 s / 1800 s, avec timeout de lecture 15 s, expiration de présence 15 s, une requête à la fois et plafond de 20 lectures/s. Ce sont des cibles : la charge et les délais de réponse peuvent allonger un cycle (environ 35 s observés pendant la collecte initiale).

## Limites explicites

Cinq propriétés indisponibles sont conservées comme telles : objectName sur file:50, file:52 et event-log:1 ; represents sur les deux structured-view. Les trois premières ont produit ValueError ; les deux dernières sont signalées comme propriétés absentes. Aucun nom de remplacement sémantique n'a été inventé.

Le classement par espace reprend les règles existantes basées sur les noms/descriptions et reste proposé à validation. Les 9 candidats comptage incluent des débits de ventilation et des fichiers M-Bus/Modbus : ce ne sont pas 9 compteurs confirmés. Aucun bus M-Bus/Modbus n'a été sondé directement.

Les qualités sont horodatées et collectées avec les métadonnées (1800 s), donc ne constituent pas une surveillance d'alarme à 2 s. La Phase 2 ne remplace pas les sécurités CPO.

L'inventaire réel complet est disponible via « Exporter l'inventaire » dans la console et enregistré dans /data/inventory.json de l'application. Il n'a pas été publié sur GitHub. La console sombre est une interface d'inspection ; le graphisme final Phase 3 et les commandes Phase 4 restent distincts.
