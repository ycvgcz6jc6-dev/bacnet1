# BACnet Reader MCT — Phase 1

Base issue de `ycvgcz6jc6-dev/bacnet1`, conservée en **READ ONLY**.

## Phase 1
- cache `objectList` et métadonnées ;
- métadonnées BACnet enrichies : description, unités, fiabilité, statusFlags, outOfService ;
- `stateText` et `numberOfStates` pour les multi-state ;
- classification MCT : Grande Salle, Petite Salle, Communs, Bureaux administratifs, ECS, Chaufferie, Technique ;
- sous-système ventilation/CTA, chauffage, ECS, alarmes/sécurité ;
- détection de candidats M-Bus/Modbus/comptage ;
- inventaire `/data/inventory.json` enrichi ;
- publication MQTT Home Assistant conservée ;
- aucune implémentation WriteProperty.

Les modes spectacle, commandes de température et écritures BACnet ne font volontairement pas partie de cette phase.
