# MCT — Phase 2, lecture seule

La version 0.4.0 conserve les identifiants des entités et topics MQTT existants, l’inventaire `/data/inventory.json`, la classification et les candidats M-Bus/Modbus. La publication MQTT reste facultative. Le mode historique est conservé via `phase2_enabled: false`.

Ouvrir l’interface de l’application dans Home Assistant. Elle offre les vues Grande Salle, Petite Salle, Communs, Bureaux administratifs, CTA, ECS, Chaufferie, Comptages, Alarmes et BACnet technique. Les regroupements par nom sont des propositions, pas des affectations de pièces confirmées. L’interface sombre utilise les seules données collectées. Le logo officiel absent n’est pas reproduit.

## Collecte

Tous les identifiants BACnet bruts sont conservés. `stateText` est indexé à partir de 1. Aucun sens n’est attribué à un numéro inconnu. Les textes binaires sont lus directement par ReadProperty : la valeur de remplacement True/False de BAC0 n’est pas utilisée. Les valeurs binaires HA reflètent seulement active/inactive, sans classe de sécurité inférée.

Les métadonnées incluent les propriétés usuelles, les textes binaires et multi-state, les structured views, schedules, notification classes et event enrollments. Chaque propriété exportée expose son état de lecture et sa date de dernière réussite. Une propriété inaccessible reste marquée indisponible. Les structures BACnet sont sérialisées en JSON quand la bibliothèque le permet, sinon leur représentation brute est conservée. La collecte n’effectue pas de scan direct M-Bus ou Modbus : les objets BACnet pouvant représenter ces compteurs sont des candidats.

Une unité d’énergie ne suffit pas à déclarer un compteur cumulatif : `total_increasing` n’est plus attribué sans validation physique. Les identifiants d’entités demeurent identiques.

## Rafraîchissement et charge

- Valeurs courantes : cible 30 s.
- Points effectivement visibles : cible 2 s, heartbeat multi-client, expiration après 15 s ; maximum 40 points par client et 32 clients.
- Métadonnées : cycle de 1800 s, incluant les propriétés de qualité. Leur horodatage est affiché dans les détails ; elles ne sont pas présumées aussi récentes que la valeur.
- Timeout d’une lecture : 15 s.
- Une seule lecture à la fois ; limite 20 lectures/s par défaut, ralentissement selon la latence et pause progressive jusqu’à 60 s sur erreurs de transport.
- Une opération sur quatre est réservée aux métadonnées lorsque les valeurs occupent la file. Les délais sont des cibles, pas une garantie : la protection du CPO prime.
- Après un échec, la dernière bonne valeur et sa date sont conservées. Disponibilité périmée après 180 s, également via l’expiration MQTT.

## Accès et limites

L’interface utilise Ingress HA ; le serveur n’accepte que le proxy Supervisor 172.30.32.2. Aucun port web public ni nouvelle identité d’accès n’est créé. Le seul POST enregistre les points visibles ; aucun endpoint, topic de commande ou appel WriteProperty n’existe.

L’export JSON contient l’inventaire complet et peut comporter les destinataires techniques des classes de notification. Le conserver dans le contexte privé MCT, pas dans le dépôt public.

La Phase 4 reste conditionnée à la validation explicite de Cyprien, une allowlist et la vérification des priorités. Aucun mode spectacle, purge ou acquittement n’est activé.

## Tests

Depuis le dossier de l’application : `python -m unittest discover -p 'test_phase*.py' -v`.
Les tests utilisent des transports simulés et ne contactent pas le CPO. La recette sur site vérifie séparément découverte, valeurs, textes réels, inventaire complet, heartbeat, expiration et charge.
