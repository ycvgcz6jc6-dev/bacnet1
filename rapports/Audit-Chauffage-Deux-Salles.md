# Chauffage des deux salles — relevé du 27 septembre 2026

Source : inventaire réel 0.5.1-audit, Device 130 TE_01_CH, horodaté 15:19:15 UTC. Lecture seule. Aucune commande, installation ou modification du CPO effectuée pendant ce relevé.

Cyprien confirme : aucune climatisation dans le bâtiment ; chauffage et ventilation uniquement. Priorité à la Grande Salle pour la réduction de ventilation. La Petite Salle est liée au bar pour la ventilation. Ces informations ne changent pas automatiquement l'affectation des objets BACnet.

## Circuits de chauffage

Bloc A et Bloc B sont respectivement les candidats Grande Salle et Petite Salle de la classification existante ; leur périmètre physique complet reste à confirmer.

| Fonction CPO | Bloc A | Bloc B |
|---|---|---|
| Consigne modifiable température ambiante minimale | analog-value_29, Rad_BlocA_PcmTmpAmbMin : 20 °C | analog-value_19, Rad_BlocB_PcmTmpAmbMin : 20 °C |
| Paramètre réduction de nuit | analog-value_32 : 20 °C | analog-value_21 : 20 °C |
| Point interne TmpAmb_i, pas une sonde confirmée | analog-value_12 : 20 °C | analog-value_15 : 20 °C |
| Température départ circuit | analog-input_4, Rad_Rad_BlocA_TmpDep : 23,46 °C | analog-input_17 : 25,35 °C |
| Température retour circuit | analog-input_5, Rad_Rad_BlocA_TmpRt : 23,93 °C | analog-input_9 : 26,87 °C |
| Mode indiqué par CPO | multi-state-value_4 : 7, « Arrêt par la temp ex » | multi-state-value_6 : 7, même texte |
| Dérogation | multi-state-value_5 : 2, « Auto » | multi-state-value_7 : 2, « Auto » |
| Commande pompe et modulation vanne | 0 et 0 % | 0 et 0 % |

Les deux consignes minimales et les deux paramètres de nuit ont 16 emplacements priorityArray nuls et relinquishDefault = 20. Ce constat ne prouve pas qu'une modification est autorisée, ni qu'il s'agit d'un thermostat classique. Les dérogations ont stateText = Off / Auto / On, 16 emplacements nuls et relinquishDefault = 2. Ne pas confondre ces dérogations de chauffage avec la réduction de ventilation.

Les deux points internes TmpAmb_i ont une valeur 20 à la priorité 15 et un repli 20. Aucune sonde d'ambiance indépendante clairement identifiée dans les noms/descriptions examinés. Ne pas afficher ces valeurs internes comme mesures de température des salles.

## Grande Salle : air soufflé et repris

- analog-input_36, TCGP1_TmpPul : 24,33 °C, température de pulsion.
- analog-input_37, TCGP1_TmpRep : 21,74 °C, température d'extraction. Ce n'est pas une mesure confirmée à hauteur du public.
- analog-value_82, TCGP1_PcTmpRep : 23 °C à la priorité 8, repli 22 °C. Le nom évoque la reprise, mais la description annonce « Point de Consigne modifiable Air Extérieur Mimnimum Pour Compensation ». Rôle ambigu : ne pas renommer ce point en thermostat ni toucher à la priorité 8 existante.

## Horaire et priorité existante

binary-value_59 Rad_BlocA_Hor vaut 1 (« Marche »), avec priorité 8 = 1 et priorité 15 = 0. Origine de la priorité 8 inconnue. Le circuit indique malgré cela « Arrêt par la temp ex » : une demande horaire ne garantit pas la mise en chauffe. Ne pas effacer cette priorité existante.

binary-value_22 Rad_BlocB_Hor vaut 0 (« Arret »), priorité 15 = 0. Ne pas modifier les horaires pour simuler une consigne de température.

## Suite de mise en service

1. Confirmer le périmètre physique Bloc A / Bloc B et l'existence des sondes d'ambiance ; garder dans l'interface les libellés précis départ, retour, extraction et point interne.
2. Faire confirmer le rôle des consignes minimales AV29 / AV19, leurs bornes et leur interaction avec la courbe de chauffe, le mode nuit et l'arrêt extérieur.
3. Définir la priorité réservée à HA et le mécanisme de libération, en préservant les priorités existantes. Aucune priorité arbitraire choisie.
4. Après validation, tester un seul circuit à la fois : lecture initiale, modification bornée, lecture de confirmation, observation réelle et libération. Ne pas commander directement vannes ou pompes.

La lecture des températures et paramètres peut être utilisée dès maintenant. L'activation d'un réglage utilisateur reste en attente de ces validations ; aucune commande de refroidissement à prévoir.
