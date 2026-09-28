# Phase 4 : moteur de simulation hors ligne

Module ajouté : command_simulation.py. Il n'est importé ni par le service HA, ni par son interface. Aucun transport réseau, identifiant BACnet ou chemin d'écriture réelle. La version installée reste 0.5.1-audit.

Fonctions : chauffage Grande Salle, chauffage Petite Salle, ventilation réduite Grande Salle et évacuation du brouillard Grande Salle. Aucun mode climatisation. Petite Salle/bar reportés pour la ventilation.

Chaque fonction nécessite une politique explicite de minimum, maximum et durée maximale. Les limites des tests sont artificielles ; elles ne constituent pas des réglages proposés pour le bâtiment. Les fonctions absentes de la liste sont refusées. Les deux modes de ventilation sont incompatibles ; les chauffages sont indépendants. Une session active ne peut pas être remplacée silencieusement.

Le journal mémoire conserve démarrages, refus, annulations et expirations. snapshot() fournit une copie exportable. Aucun stockage persistant automatique n'est encore branché. À réception d'un checkpoint, le moteur annule les sessions précédentes sans rejouer de commande.

L'horloge injectée doit être monotone. L'expiration est exécutée par tick(), pas par un service en arrière-plan. Une perte de communication ou une sécurité simulée annule la session sans reprise automatique. Une annulation simulée ne confirme jamais un retour physique du CPO. Le mécanisme d'expiration autonome du CPO reste à valider avant toute connexion réelle.

Validation : 7 nouveaux tests de simulation, 24 tests Python existants. La connexion à une interface de démonstration et le stockage persistant restent des étapes ultérieures ; aucun bouton de commande réel n'est activé.

## Interface de démonstration ajoutée

work/preview_phase4.py sert work/phase4-demo.html sur 127.0.0.1:8767. Le serveur utilise le moteur ci-dessus sous verrou et appelle tick toutes les 200 ms, indépendamment de la présence du navigateur. Les requêtes de commande vérifient l'origine locale et la taille du corps. Le journal est exportable en JSON ; il reste en mémoire et disparaît à l'arrêt du serveur. Le bouton de redémarrage simule une reconstruction du moteur sans relancer les sessions.

Recette navigateur réalisée : démarrage ventilation réduite ; refus simultané de l'évacuation du brouillard ; annulation par perte de communication ; évacuation du brouillard puis expiration à 5 secondes ; chauffage puis annulation au redémarrage. Tous ces événements ont été vérifiés dans le journal affiché. Aucun branchement au CPO ni changement de l'interface HA existante.
