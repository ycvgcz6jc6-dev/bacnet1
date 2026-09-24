import asyncio
import logging
import os
import signal
import socket
import sys

import BAC0


LOCAL_IP = os.getenv("LOCAL_IP", "192.168.0.39/24")
TARGET_IP = os.getenv("TARGET_IP", "192.168.0.249")
BACNET_PORT = int(os.getenv("BACNET_PORT", "47808"))
DISCOVERY_INTERVAL = int(os.getenv("DISCOVERY_INTERVAL", "60"))
READ_DEVICE_INFO = os.getenv(
    "READ_DEVICE_INFO", "true"
).lower() in ("1", "true", "yes")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
)

log = logging.getLogger("BACnetReader")

running = True


def stop_handler(*_):
    global running
    running = False
    log.info("Arrêt demandé.")


signal.signal(signal.SIGTERM, stop_handler)
signal.signal(signal.SIGINT, stop_handler)


def test_ip_connectivity():
    """
    Vérification simple du routage IP.

    Aucun paquet BACnet d'écriture n'est envoyé.
    """
    log.info("Test réseau vers %s ...", TARGET_IP)

    try:
        socket.inet_aton(TARGET_IP)
    except OSError:
        log.error("Adresse cible invalide : %s", TARGET_IP)
        return False

    return True


async def read_property_safe(bacnet, address, obj, instance, prop):
    """
    Lecture BACnet uniquement.

    Cette application ne contient volontairement
    aucune fonction WriteProperty.
    """

    request = f"{address} {obj} {instance} {prop}"

    try:
        result = await bacnet.read(request)
        return result

    except Exception as err:
        log.debug(
            "Lecture impossible [%s]: %s",
            request,
            err,
        )
        return None


async def inspect_device(bacnet, address, device_id):
    log.info("--------------------------------------------")
    log.info("Équipement BACnet détecté")
    log.info("Adresse   : %s", address)
    log.info("Device ID : %s", device_id)

    if not READ_DEVICE_INFO:
        return

    properties = {
        "Nom": "objectName",
        "Fabricant": "vendorName",
        "Modèle": "modelName",
        "Firmware": "firmwareRevision",
        "Application": "applicationSoftwareVersion",
        "Description": "description",
        "Location": "location",
        "Vendor ID": "vendorIdentifier",
        "Protocol version": "protocolVersion",
        "Protocol revision": "protocolRevision",
    }

    for label, prop in properties.items():

        value = await read_property_safe(
            bacnet,
            address,
            "device",
            device_id,
            prop,
        )

        if value is not None:
            log.info("%-18s : %s", label, value)


async def inventory_objects(bacnet, address, device_id):
    """
    Récupération de la liste des objets exposés par
    le contrôleur.

    Toujours READ ONLY.
    """

    log.info("Lecture de objectList...")

    objects = await read_property_safe(
        bacnet,
        address,
        "device",
        device_id,
        "objectList",
    )

    if objects is None:
        log.warning("Impossible de récupérer objectList.")
        return

    log.info("Nombre/objet(s) retourné(s) : %s", len(objects))

    for obj in objects:

        try:
            obj_type = obj[0]
            obj_instance = obj[1]
        except Exception:
            log.debug("Objet non interprété : %s", obj)
            continue

        name = await read_property_safe(
            bacnet,
            address,
            obj_type,
            obj_instance,
            "objectName",
        )

        present_value = await read_property_safe(
            bacnet,
            address,
            obj_type,
            obj_instance,
            "presentValue",
        )

        units = await read_property_safe(
            bacnet,
            address,
            obj_type,
            obj_instance,
            "units",
        )

        log.info(
            "OBJECT | %-20s | %6s | %-35s | value=%s | units=%s",
            obj_type,
            obj_instance,
            name,
            present_value,
            units,
        )


def normalize_discovered_device(device):
    """
    BAC0 peut faire évoluer légèrement la représentation
    des équipements découverts.

    On évite donc de supposer un format unique.
    """

    try:

        # BAC0 2026.7.25 returns IAmRequest objects from who_is().
        if hasattr(device, "iAmDeviceIdentifier"):
            return str(device.pduSource), int(device.iAmDeviceIdentifier[1])

        if isinstance(device, (tuple, list)):

            if len(device) >= 2:
                return str(device[0]), int(device[1])

        if isinstance(device, dict):

            address = (
                device.get("address")
                or device.get("Address")
                or device.get("ip")
            )

            device_id = next(
                (device[key] for key in ("device_id", "deviceId", "instance")
                 if device.get(key) is not None), None
            )
            if device_id is None and device.get("object_instance") is not None:
                device_id = device["object_instance"][1]

            if address is not None and device_id is not None:
                return str(address), int(device_id)

    except Exception:
        pass

    return None, None


async def discovery_cycle(bacnet):
    log.info("")
    log.info("========== BACnet discovery ==========")
    log.info("Envoi Who-Is...")

    try:
        # Explicit local broadcast; consume the actual I-Am responses.
        # whois() and the discoveredDevices cache are not this API.
        discovered = await bacnet.who_is(address="*", timeout=3)
    except Exception as err:
        log.warning("Who-Is : %s", err)
        discovered = []

    if not any(
        (normalize_discovered_device(device)[0] or "").split(":")[0] == TARGET_IP
        for device in discovered
    ):
        try:
            directed = await bacnet.who_is(
                address=f"{TARGET_IP}:{BACNET_PORT}", timeout=3
            )
            discovered = list(discovered) + list(directed)
        except Exception as err:
            log.warning("Who-Is ciblé : %s", err)

    if not discovered:
        log.warning("Aucun équipement BACnet découvert.")
        return

    log.info(
        "%s équipement(s) découvert(s).",
        len(discovered),
    )

    target_found = False

    for device in discovered:

        log.debug("Réponse brute : %r", device)

        address, device_id = normalize_discovered_device(device)

        if address is None:
            log.warning(
                "Réponse BACnet non interprétée : %r",
                device,
            )
            continue

        await inspect_device(
            bacnet,
            address,
            device_id,
        )

        # Certains stacks renvoient adresse:port.
        clean_address = address.split(":")[0]

        if clean_address == TARGET_IP:

            target_found = True

            log.info("")
            log.info("**************************************")
            log.info(" CIBLE BACnet TROUVÉE : %s", TARGET_IP)
            log.info("**************************************")

            await inventory_objects(
                bacnet,
                address,
                device_id,
            )

    if not target_found:

        log.warning(
            "Le contrôleur cible %s n'a pas encore "
            "été identifié parmi les réponses.",
            TARGET_IP,
        )


async def main():

    log.info("BACnet Reader démarré.")
    log.info("VERSION : 0.1.1")
    log.info("MODE    : READ ONLY")

    if not test_ip_connectivity():
        sys.exit(1)

    log.info(
        "Ouverture BACnet/IP sur %s",
        LOCAL_IP,
    )

    try:

        async with BAC0.start(
            ip=LOCAL_IP, port=BACNET_PORT
        ) as bacnet:

            log.info("BACnet/IP initialisé.")
            log.info(
                "Recherche de la cible %s...",
                TARGET_IP,
            )

            while running:

                try:
                    await discovery_cycle(bacnet)

                except Exception:
                    log.exception(
                        "Erreur pendant le cycle de découverte."
                    )

                for _ in range(DISCOVERY_INTERVAL):

                    if not running:
                        break

                    await asyncio.sleep(1)

    except Exception:
        log.exception(
            "Impossible d'initialiser BACnet/IP."
        )
        sys.exit(2)

    log.info("BACnet Reader arrêté.")


if __name__ == "__main__":
    asyncio.run(main())
