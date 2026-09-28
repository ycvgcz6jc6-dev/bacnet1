# Moyennes par zone — version 0.5.2

Ces moyennes sont des moyennes arithmétiques entre sondes au moment du relevé, pas des moyennes temporelles. Le calcul utilise le cache existant et n'ajoute aucune lecture BACnet. Publication MQTT lors de la sauvegarde périodique de l'inventaire (environ 10 secondes).

17 groupes par défaut : extérieur ; air extrait et soufflé Grande Salle ; ambiance Grande et Petite Salle ; eau départ et retour séparés pour Grande Salle, Petite Salle, Communs, Bureaux administratifs, Chaufferie et ECS. Les regroupements Bloc A/B/C_D/Extension suivent la classification existante et leur périmètre physique reste à confirmer.

Une seule sonde confirmée par groupe actuellement : sa moyenne égale sa valeur. Les deux groupes d'ambiance n'ont PAS de source confirmée et restent indisponibles. Les points internes TmpAmb_i, les consignes, l'air neuf, l'eau et les températures extérieures lissées ne sont pas utilisés comme substituts de sondes ambiantes. La sonde extérieure est analog-input_1 TCPRCH__TmpBL, décrite par le CPO comme Temp Air Extérieure (PRCH).

## Utiliser les valeurs dans Home Assistant

Après installation de la version 0.5.2 et connexion au broker MQTT existant, les nouveaux capteurs apparaissent par MQTT Discovery sous l'appareil BACnet Reader / TE_01_CH. Aucun redémarrage de HA normalement requis pour la découverte. Attendre la collecte initiale de qualité des sources.

Dans Paramètres → Appareils et services → MQTT, retrouver l'appareil et chercher « moyenne ». Dans le tableau de bord → Modifier → Ajouter une carte, choisir ces entités : carte Tuile, Entités ou graphique historique. Les identifiants entity_id sont attribués par HA ; ne pas les deviner à partir du nom. Les unique_id restent stables et se terminent par average_<id_du_groupe>.

Les températures sont publiées avec device_class=temperature, unité °C et state_class=measurement. Les attributs indiquent source_count, configured_count, sources (identifiants BACnet bruts), excluded (motifs), coverage et updated_at. Les sources en erreur, périmées, de mauvaise qualité, dupliquées ou d'unité différente sont exclues. Une moyenne partielle utilise les sources restantes et indique coverage=partial. Aucune source valide : capteur indisponible, jamais zéro inventé. Une perte de MQTT ou l'expiration du capteur rendent également la mesure indisponible.

## Ajouter des sources ou d'autres mesures

L'option de l'add-on average_groups_json accepte un tableau JSON de groupes. Vide : groupes par défaut. Une valeur renseignée remplace cette configuration de groupes, pas les objets ni fonctions BACnet existants. Le fichier average_groups.example.json reproduit les groupes par défaut ; le copier puis ajouter les sources confirmées.

Chaque groupe a id (stable), name, zone, unit (unité BACnet brute), sources (dictionnaire identifiant brut → objectName exact). Ne regrouper que des mesures de même nature et de même unité, pertinentes pour la même zone. Les analog-value peuvent être sélectionnés explicitement si leur rôle de mesure est confirmé ; ne pas y mettre des consignes, compteurs cumulés ou calculs redondants. Les états binaires, modes, alarmes et sorties ne sont pas des mesures à moyenner.

Redémarrer l'add-on après modification des groupes. Si un groupe est retiré, son ancienne entité peut rester dans HA et expirer ; aucune suppression MQTT automatique n'est faite afin de préserver l'existant.

## État de livraison

46 tests Python et 9 tests JavaScript réussis localement, dont calcul, filtrage qualité et découverte/disponibilité MQTT. Non installé sur HA pendant cette livraison ; la découverte réelle dans votre broker reste à vérifier après installation. Toutes les commandes BACnet restent désactivées.
