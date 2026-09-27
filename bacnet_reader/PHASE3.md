# Phase 3 — v0.5.0, panneau exploitation MCT

Base : commit d9224f3dd15d1afeb2936ff3887efc25bd21ca61 (0.4.0 validée sur site).

## Interface

Le panneau exploitation devient la page d’accueil Ingress. La console Phase 2 reste intacte à `technical` et `mct.html`. Les fonctions de collecte, entités MQTT, identifiants, classification et export existants sont conservés.

Navigation : Vue générale, Grande Salle, Petite Salle, Communs, Bureaux, CTA, Chaufferie, ECS, Comptages, Alarmes, Horaires, BACnet Explorer, Diagnostic et Paramètres (consultation).

Le logo PNG et les trois photos sont les fichiers originaux fournis par Cyprien. Grande Salle = sièges orange ; Petite Salle = plateau/gradin. Le bâtiment reçoit un traitement sombre bleu par CSS ; aucune modification architecturale ni régénération du logo. Toutes les ressources sont locales, sans police ou script tiers.

Les cartes sont issues de l’inventaire, avec valeurs, unités, libellés CPO et dates réelles. Les annotations des structured-view sont utilisées uniquement pour une référence BACnet locale exacte et un libellé non ambigu. Le nom brut reste visible. Les affectations de zones existantes restent des propositions à confirmer.

## Lecture et fraîcheur

Le panneau demande le polling rapide seulement pour les points visibles à l’écran, hors bandeaux, et uniquement pour le point inspecté quand une fenêtre de détails est ouverte. Il relâche ses demandes lorsqu’il est caché, quitte la page, change de filtre ou de vue. Les limites et délais de Phase 2 restent applicables. LIVE indique une demande d’accélération acceptée, pas une garantie de délai ni une modification du CPO.

L’état global décrit la communication et la couverture des données. Il ne déduit ni occupation, ni spectacle, ni sécurité incendie. Un état d’alarme périmé ou non lu ne permet pas d’affirmer l’absence d’événement. Les cinq propriétés indisponibles constatées en Phase 2 restent explicitement indisponibles.

Les événements utilisent eventState BACnet (normal = 0, d’après l’énumération BACnet), les notification-class réelles et leurs tableaux de priorités bruts. Les statusFlags.in-alarm sont présentés séparément, sans prétendre dédupliquer les sources. Les qualités/événements restent des métadonnées à 1800 s : ce panneau n’est pas un système de sécurité ni une alerte instantanée. Aucun acquittement.

Les programmes hebdomadaires affichent les transitions et valeurs BACnet brutes. Les exceptions, périodes et références sont accessibles dans les détails. Aucune conversion supposée en occupé/inoccupé.

Les candidats comptage ne deviennent pas des compteurs confirmés. Aucun cumul, graphique historique ou consommation n’est inventé.

## Protection et préparation Phase 4

L’accès conserve la restriction au proxy Ingress. Les fichiers servis proviennent d’une allowlist exacte, sans chemin arbitraire. Aucun endpoint de commande, d’écriture, de purge, d’horaire ou d’acquittement n’est ajouté. Le seul POST demeure le heartbeat.

`ZONE_CAPABILITIES` documente les futures capacités : Grande/Petite Salle peuvent être préparées ; partout, `control_enabled` et `write_enabled` restent faux. La Phase 4 nécessitera sa propre validation, l’audit priorityArray/relinquishDefault et une allowlist. Aucun moteur d’écriture anticipé n’est installé.

## Recette avant installation

- `python -m unittest discover -p 'test_phase*.py' -v`
- `node --test test_presentation.cjs`
- Vérification visuelle du panneau avec transports simulés explicitement signalés : PC, tablette paysage/portrait et petit écran.
- Comparaison du format réel des horaires, annotations structurées, eventState et priorités au CPO 0.4.0 en lecture seule.
- L’aperçu local ne contacte pas le CPO. Les données de test ne font pas partie de l’image installée.

La livraison 0.5.0 est préparée pour contrôle avant installation, conformément à l’enchaînement du chat de référence. La validation locale ne remplace pas la recette finale de la 0.5.0 installée sur HA.
