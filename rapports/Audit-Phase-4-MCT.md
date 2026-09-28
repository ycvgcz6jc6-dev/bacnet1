# État de départ Phase 4 — 27 septembre 2026

HA vérifié par rechargement de l’inventaire à 10:22:46 UTC : 0.4.0-phase2. La PR 0.5.0 #1 est ouverte, non fusionnée. Aucun priorityArray disponible dans l’inventaire actuel.

Les sept horaires exposent priorityForWriting=15. Ceci n’autorise pas à choisir une priorité HA.

Points à examiner, non autorisés :

| Objet brut | Nom CPO | Libellés CPO |
|---|---|---|
| multi-state-value_5 | Rad_BlocA_Der | Off / Auto / On |
| multi-state-value_7 | Rad_BlocB_Der | Off / Auto / On |
| multi-state-value_13 | TCGP1_DrgHor | Automatique / Fonctionnement permanent / Arrêt permanent |

multi-state-value_14, TCGP1_FireMode, est exclu des futures commandes d’exploitation. Le libellé Purge sur ce point ne constitue pas une commande de purge scénique.

Prototype 0.5.1-audit préparé localement dans work/phase4-audit, 33 tests réussis. Non publié, non installé. Il collecte les deux propriétés manquantes en lecture seule et maintient toutes les autorisations à faux. La liste des commandes, leurs effets, la priorité et le retour à la régulation restent à valider à partir des données réelles et de la confirmation de l’exploitant.

## Mise à jour après installation — 27 septembre 2026

Les paragraphes ci-dessus décrivent l'état initial, désormais dépassé. La PR #1 a été fusionnée, puis la version 0.5.1 publiée sur main (commit 279e9f3d0f623ed9006805dba4d81759eed652b3). Les 27 fichiers locaux correspondent aux fichiers publiés. Validation avant publication : 24 tests Python et 9 tests JavaScript réussis.

L'installation HA affiche 0.5.1 en cours d'exécution. L'inventaire réel horodaté 2026-09-27T15:08:22.030537+00:00 indique 0.5.1-audit, READ ONLY, 358 objets, 261 valeurs disponibles et les métadonnées complètes. Pour 191 objets, priorityArray et relinquishDefault ont été lus avec succès et sont frais selon le contrôle de l'application. Cela ne prouve ni les droits d'écriture ni la sûreté d'une commande. Aucune écriture BACnet effectuée.

### Ventilation Grande Salle : éléments constatés

Le rattachement provient de la vue structurée GPGE1_Salle_A. Valeurs instantanées, non consignes approuvées :

| Identifiant brut | Nom CPO | Constat | Priorités / repli |
|---|---|---|---|
| analog-output_14 | TCGP1_ModVPu | Modulation pulsion : 100 % | priorité 15 = 100 ; repli 0 |
| analog-output_15 | TCGP1_ModVEx | Modulation extraction : 100 % | priorité 15 = 100 ; repli 0 |
| analog-value_70 | TCGP1_VPuVExVmax | « Vitesse maximale » : 30 000 m³/h | 16 emplacements null ; repli 30 000 |
| analog-value_84 | TCGP1_VPuVExVmin | « Vitesse réduite » : 10 000 m³/h | 16 emplacements null ; repli 10 000 |
| analog-value_87 | TCGP1_PccDebit | « Point de consigne calcule debit » : 30 000 m³/h | priorité 15 = 30 000 ; repli 0 |

Le paramètre Vmin ne constitue pas une demande d'activation du régime réduit. Les tableaux ne révèlent pas la logique du programme ni les interactions incendie. Une commande directe des variateurs ou de la consigne calculée reste donc exclue de la liste autorisée. Aucune priorité HA n'est sélectionnée.

Le point multi-state-value_15 TCGP1_PlantMode vaut 4, avec le texte CPO « Night Purge ». Ne pas assimiler cet état à une purge de fumée scénique. TCGP1_DrgHor expose Automatique / Fonctionnement permanent / Arrêt permanent, sans état explicitement nommé ventilation réduite. Les points FireMode et ArrInc restent exclus.

### Petite Salle et informations manquantes

Les 31 objets classés Petite Salle concernent le chauffage, les pompes et l'horaire Bloc_B. Cette classification est heuristique et non validée. La liste complète des sorties ne permet pas d'identifier une deuxième ventilation : elle comporte les sorties TCGP1, chauffage et ECS. Cela ne démontre pas l'absence d'un équipement indépendant ou d'un autre automate.

À obtenir : identification physique de la ventilation Petite Salle ; programme ou documentation CPO donnant la demande de régime réduit, ses états et sa priorité autorisée ; preuve de la priorité des sécurités ; mécanisme de retour automatique, y compris en cas de perte de HA. Une temporisation uniquement dans HA ne garantit pas ce retour si HA s'arrête.

### Signal CPO à examiner

analog-input_35 TCGP1_PrsPul (pression statique en gaine, pulsion) : 1 278,0001 Pa ; statusFlags = [1,0,0,0], donc indicateur in-alarm présent. reliability = no-fault-detected et outOfService = 0. Aucune cause ni gravité déduite. Aucun event-enrollment correspondant identifié dans l'inventaire examiné. Vérifier le seuil et l'état réel avant un essai de réduction.

### Décision

Audit déployé et réception des données vérifiée. Phase 4 de commande non validée ; toutes les autorisations restent fausses. Prochaine étape : compléter le mapping CPO et définir un essai encadré à partir des informations ci-dessus, sans modifier les paramètres de chauffage ni supprimer de fonctions existantes.
