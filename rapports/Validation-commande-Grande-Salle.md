# Commande temporaire de ventilation — Grande Salle MCT

État : identification fonctionnelle à compléter ; aucune commande autorisée.

## Besoin confirmé par Cyprien

Réduire temporairement le bruit de ventilation pendant un spectacle dans la Grande Salle, puis rendre automatiquement la main au CPO. La Petite Salle, liée à la ventilation du bar selon Cyprien, est reportée. Conserver toutes les fonctions existantes et la priorité des sécurités CPO.

## Vérification réelle du 27 septembre 2026 à 15:14 UTC

Source : inventaire 0.5.1-audit, Device 130, TE_01_CH, vue GPGE1_Salle_A. Les états ci-dessous sont les libellés du CPO, sans réinterprétation.

| Point | Rôle / constat |
|---|---|
| analog-value_84 — TCGP1_VPuVExVmin | Paramètre « Vitesse réduite », 10 000 m³/h ; ne prouve pas un déclencheur |
| analog-value_70 — TCGP1_VPuVExVmax | Paramètre « Vitesse maximale », 30 000 m³/h |
| analog-value_87 — TCGP1_PccDebit | Consigne calculée, 30 000 m³/h |
| analog-value_73 / 74 | Débits pulsion / reprise, environ 28 627 / 29 096 m³/h |
| binary-value_40 — TCGP1_Hor | 0 = « Inoccupation » ; 1 = « Occupation » |
| schedule_9 — GPGE1 | Écrit sur binary-value_40 à la priorité 15 ; aucune exception dans la lecture examinée |
| multi-state-value_13 — TCGP1_DrgHor | 1 = Automatique ; 2 = Fonctionnement permanent ; 3 = Arrêt permanent |
| multi-state-value_15 — TCGP1_PlantMode | État lu : 4 = « Night Purge » ; aucun état explicitement nommé régime réduit |

La coexistence observée d'Inoccupation et de Night Purge avec la consigne à 30 000 m³/h montre qu'il ne faut pas assimiler Inoccupation à une ventilation réduite. Cette observation ne permet pas de reconstruire le programme de régulation.

Attention au point binary-value_41 TCGP1_ArrInc : les textes lus sont 0 = « Arrêt Forcé », 1 = « Auto ». Ne pas déduire « pas d'incendie » de sa seule valeur numérique 0. Ce point et TCGP1_FireMode sont exclus de toute commande d'exploitation.

## Informations exactes nécessaires auprès du mainteneur CPO

1. Existe-t-il une demande native de régime réduit pour GPGE1, éventuellement non exposée dans les objets actuels ? Fournir identifiant BACnet, propriété, valeur d'activation et valeur ou procédure de libération.
2. Quel rôle exact joue TCGP1_VPuVExVmin, et quels modes utilisent Vmin ou Vmax ? Préciser les effets sur Night Purge, occupation, CO2 et sécurités.
3. Quelle priorité d'écriture peut être réservée à HA sans supplanter les sécurités ? Confirmer les autres utilisateurs de cette priorité.
4. Comment la demande expire-t-elle dans le CPO si HA ou le réseau tombe en panne ? Une temporisation côté HA seule ne suffit pas à garantir le retour.
5. Quel débit réduit et quelle durée maximale sont acceptables pour l'occupation de la salle ? La valeur actuelle de Vmin ne constitue pas à elle seule cette validation.
6. Examiner l'indicateur in-alarm de TCGP1_PrsPul observé lors de l'audit précédent et confirmer les conditions d'essai.

## Recette à effectuer une fois ces réponses validées

- Enregistrer les valeurs, qualités et priorités initiales ; refuser un démarrage si les données requises sont absentes, périmées ou incompatibles avec l'essai.
- Activer exclusivement la demande approuvée, pour une durée approuvée, et vérifier son retour de lecture.
- Vérifier les débits réels de pulsion et reprise, les alarmes et l'effet acoustique sur place.
- Vérifier la libération manuelle et à expiration, sans écraser les autres priorités ni restaurer aveuglément une ancienne valeur.
- Vérifier la reprise après redémarrage HA et la perte de communication selon le mécanisme CPO approuvé.
- Faire valider la priorité des sécurités par le mainteneur ; aucun déclenchement incendie improvisé depuis HA.

Après recette seulement : activer le bouton de réduction temporaire, le temps restant et le retour à la régulation dans l'interface. Aucun bouton opérationnel n'est annoncé avant cela.
