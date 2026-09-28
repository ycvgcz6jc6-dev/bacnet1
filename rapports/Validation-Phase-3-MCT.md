# Validation Phase 3 — BACnet Reader MCT v0.5.0

Livraison locale préparée le 27 septembre 2026. Publiée sur la branche phase3-0.5.0 et proposée en revue : https://github.com/ycvgcz6jc6-dev/bacnet1/pull/1. Non installée sur Home Assistant. Dernière version validée sur HA : 0.4.0.

## Résultat

Interface sombre PC/tablette avec logo officiel et trois photos originales, navigation par zones, valeurs et identifiants BACnet, consultation des alarmes et horaires, explorateur, diagnostics et paramètres en lecture seule. Console technique précédente conservée à l’identique. Aucune commande BACnet ajoutée.

## Vérifications

- 19 tests Python et 9 tests JavaScript réussis, relancés le 27 septembre.
- Vérifications visuelles déjà réalisées sur PC, tablette paysage 1024 × 768, portrait 768 × 1024 et petit écran 390 × 844.
- Navigation, filtres, pagination, détails, perte de connexion et demandes de polling limitées aux points visibles contrôlés dans l’aperçu local.
- Formats des horaires, annotations structurées, événements et priorités comparés aux données réelles en lecture seule lors de la préparation.
- Console mct.html comparée octet par octet à la base 0.4.0 : identique.
- Archive vérifiée et empreintes de chaque fichier jointes.

## Limites et installation

L’aperçu utilise des données simulées explicitement signalées ; il ne contacte pas le CPO. La construction de l’image Home Assistant et la recette de la version installée restent à réaliser. Les métadonnées d’alarmes restent actualisées à 1800 secondes ; aucun acquittement ni fonction de sécurité ajouté. Aucun état d’occupation ou de spectacle déduit.

## Contenu à publier

L’archive contient uniquement le dossier de l’extension, ses documents, tests et quatre visuels. Aucun inventaire réel, export HA, identifiant d’accès, journal d’exploitation ou serveur d’aperçu n’y est inclus. La configuration conserve les adresses locales déjà présentes dans le dépôt public ; seules sa version et sa description changent.

Publication autorisée explicitement par Cyprien et effectuée le 27 septembre 2026. Commit final : def6a97a3e2f4aa69c018af7b9b35613cdbd3270. Les empreintes Git des 24 fichiers de livraison correspondent toutes aux fichiers publiés ; 19 fichiers ajoutés ou modifiés, aucun fichier supprimé. Base main inchangée : d9224f3dd15d1afeb2936ff3887efc25bd21ca61.

## Fichiers de l’archive

- `bacnet_reader/CHANGELOG.md`
- `bacnet_reader/DOCS.md`
- `bacnet_reader/Dockerfile`
- `bacnet_reader/PHASE3.md`
- `bacnet_reader/assets/MCT_Logo_Ver_Blanc.png`
- `bacnet_reader/assets/batiment.jpg`
- `bacnet_reader/assets/grande-salle.jpeg`
- `bacnet_reader/assets/petite-salle.jpg`
- `bacnet_reader/bacnet_reader.py`
- `bacnet_reader/build.yaml`
- `bacnet_reader/config.yaml`
- `bacnet_reader/exploitation.css`
- `bacnet_reader/exploitation.html`
- `bacnet_reader/exploitation.js`
- `bacnet_reader/mct.html`
- `bacnet_reader/phase2.py`
- `bacnet_reader/phase3.py`
- `bacnet_reader/presentation.js`
- `bacnet_reader/requirements.txt`
- `bacnet_reader/run.sh`
- `bacnet_reader/test_phase1.py`
- `bacnet_reader/test_phase2.py`
- `bacnet_reader/test_phase3.py`
- `bacnet_reader/test_presentation.cjs`
