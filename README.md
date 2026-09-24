# BACnet Reader for Home Assistant

Add-on Home Assistant destiné à la découverte et au diagnostic
d'équipements BACnet/IP.

## État

Version expérimentale 0.1.0.

Cette première version a été créée pour tester un système
Honeywell ComfortPoint Open depuis Home Assistant.

Configuration de test initiale :

- Home Assistant : `192.168.0.39/24`
- Honeywell ComfortPoint : `192.168.0.249`
- BACnet/IP : UDP 47808

## Sécurité

Cette version fonctionne volontairement en **READ ONLY**.

Elle effectue :

- BACnet Who-Is
- réception I-Am
- lecture des propriétés Device
- lecture de `objectList`
- lecture de `objectName`
- lecture de `presentValue`
- lecture de `units`

Elle ne contient volontairement aucune implémentation
`WriteProperty`.

Elle ne doit donc pas modifier :

- consignes
- températures
- vannes
- pompes
- ventilateurs
- chauffage
- refroidissement
- automates

## Pourquoi host_network ?

BACnet/IP utilise notamment les broadcasts UDP.

Les add-ons Home Assistant ordinaires sont isolés dans un réseau
Docker `172.30.x.x`.

Cela empêchait BAC0 d'utiliser directement l'interface Home
Assistant :

`192.168.0.39/24`

L'add-on utilise donc :

```yaml
host_network: true
```
afin d'accéder au réseau BACnet réel.

## Installation
Dans Home Assistant :

1. Paramètres
2. Modules complémentaires
3. Boutique des modules complémentaires
4. Menu ⋮
5. Dépôts
6. Ajouter l'URL GitHub de ce repository
7. Installer **BACnet Reader**

## Configuration
Configuration par défaut :

```yaml
local_ip: 192.168.0.39/24
target_ip: 192.168.0.249
bacnet_port: 47808
discovery_interval: 60
read_device_info: true
log_level: INFO
```

## Premier démarrage
Consulter immédiatement le journal de l'add-on.
Le résultat recherché est une réponse BACnet **I-Am** provenant
du contrôleur Honeywell.
Si la cible est détectée, le journal doit afficher notamment :

- adresse BACnet
- Device ID
- nom
- fabricant
- modèle
- firmware
- Vendor ID
- liste des objets BACnet

## Étape suivante
Lorsque la communication avec le ComfortPoint aura été validée,
la V0.2 pourra ajouter :
- classification automatique des objets
- Binary Input / Output / Value
- Analog Input / Output / Value
- Multi-state
- températures, consignes, états HVAC, alarmes, diagnostics
- publication vers Home Assistant

Les commandes BACnet resteront désactivées tant que la couche
de lecture n'aura pas été validée.
