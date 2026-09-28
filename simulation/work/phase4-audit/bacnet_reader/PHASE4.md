# Phase 4 — étape d’audit en lecture seule, 0.5.1

Cette étape prépare les commandes ; elle ne les active pas.

Ajout de priorityArray et relinquishDefault aux métadonnées des objets analog/binary/multi-state output et value. Le type output ne constitue jamais une autorisation. Le circuit de lecture existant conserve sérialisation, timeout, limite de débit et recul sur erreur. Les lectures supplémentaires suivent la cadence des métadonnées, pas le polling rapide.

L’export expose command_audit : statut, horodatage et contenu brut pour chaque propriété. Une lecture complète ne prouve ni les droits d’écriture ni la sécurité d’une commande. allowed reste faux, write_permission reste unverified, write_priority reste null. Aucune route ni fonction d’écriture ajoutée.

Validation locale : 24 tests Python et 9 tests JavaScript réussis. Construction et recette sur HA encore à réaliser. Aucune fonction ni vue existante supprimée.

Avant toute activation : identifier explicitement objet/propriété et zone ; confirmer la sémantique auprès de l’exploitant/intégrateur ; examiner les 16 priorités et relinquishDefault ; documenter les interverrouillages CPO ; fixer limites, priorité exclusive, temporisation et retour à la régulation ; tester perte HA/CPO et redémarrage. Une expiration côté HA ne garantit pas le retour automatique si HA est arrêté : prévoir un mécanisme CPO validé avant les modes temporisés.

Les points de sécurité/incendie sont exclus des futures commandes d’exploitation. L’état Auto d’un objet n’est pas assimilé à une libération de priorité. Aucun essai WriteProperty pour découvrir si un point est inscriptible.

## Périmètre confirmé

Réduction temporaire de ventilation pour limiter le bruit, indépendante Grande/Petite Salle, puis retour à la régulation CPO. Les dérogations radiateurs ne répondent pas à ce besoin. Les points vitesse/débit, limites admissibles et mécanisme de retour restent à valider. Aucun choix de priorité ni activation de commande à ce stade.
