# Préparation intégration Phases 4 et 5

Décision de Cyprien : déclenchement manuel uniquement, principalement pour les concerts classiques. Aucun lancement par horaire, calendrier ou présence. L'expiration termine une demande manuelle ; elle ne planifie pas un spectacle. Chauffage uniquement, aucune climatisation. Ventilation Petite Salle/bar reportée.

## Raccordements préparés

phase5_contract.py définit les quatre fonctions, les candidats chauffage et les observations ventilation, avec vérification stricte Device 130 / identifiant / nom CPO / présence dans l'inventaire. Toute correspondance conserve allowed=false. Les demandes ventilation restent non renseignées : Vmin et sorties variateurs ne deviennent pas des commandes par supposition.

Navigation future : Grande Salle → chauffage, concert classique, évacuation du brouillard ; Petite Salle → chauffage. Conserver toutes les vues existantes. Page prévue commands/, retours relatifs ../#grande et ../#petite. API prévue sous commands/api/ : session, password, status, start, stop, journal. Ces routes ne sont pas encore présentes dans HA.

Les liens doivent être relatifs au préfixe Ingress, jamais localhost. Le contrôle d'origine, les cookies et leur chemin doivent être adaptés au proxy HA. Stocker mot de passe haché, état et journal sous /data ; aucun secret dans les assets ou GitHub. Séparer adaptateurs simulation et réel ; activation réelle désactivée par défaut. Le prototype local n'est pas un serveur de commandes de production.

## Séquence à implémenter pour les commandes réelles

Démarrage manuel → vérifier données fraîches, identité, sécurités et priorités → journal persistant → écriture autorisée → lecture de confirmation → session active. Un accusé réseau ne suffit pas à prouver un effet physique.

Fin manuelle ou expiration → libérer uniquement la priorité réservée → confirmer par lecture → retour confirmé. En cas d'échec, afficher « retour non confirmé » et une alerte, conserver l'état nécessaire à la récupération. Ne jamais restaurer aveuglément une ancienne valeur. La disparition locale d'une session ne prouve pas le retour au CPO.

La perte de HA nécessite un mécanisme d'expiration validé dans le CPO. Au redémarrage, réconcilier les demandes persistantes sans relancer un spectacle. Une déconnexion utilisateur n'annule pas silencieusement une temporisation.

Ventilation réduite et évacuation du brouillard sont incompatibles. Libérer et confirmer la fin du premier mode avant d'en démarrer un autre. Aucun lancement automatique d'évacuation après un concert. FireMode, ArrInc et Night Purge ne sont pas des substituts à la commande d'exploitation demandée.

## Validation restante

Confirmer sémantique, zone physique, bornes, priorité réservée, libération et expiration CPO pour chaque fonction. Tester derrière Ingress : accès anonyme, session expirée, changement de mot de passe, requêtes répétées/concurrentes, limites, valeurs périmées, priorité occupée, échecs d'écriture/libération, perte réseau, redémarrage et journal persistant. Puis essais physiques par fonction avec le mainteneur CPO.

La préparation et les tests locaux ne constituent pas une validation des commandes réelles. Aucune intégration dans HA ni écriture CPO effectuée.
