import asyncio
import logging
import os
import signal
import socket
import sys
import time

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



# MQTT is used only to publish measurements. No command topics are subscribed.
import json
import math
import threading
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import paho.mqtt.client as mqtt

VALUE_TYPES = {
    "analog-input", "analog-output", "analog-value",
    "binary-input", "binary-output", "binary-value",
    "multi-state-input", "multi-state-output", "multi-state-value",
}
UNITS = {
    "degrees-celsius": ("°C", "temperature"),
    "degrees-fahrenheit": ("°F", "temperature"),
    "degrees-kelvin": ("K", "temperature"),
    "percent": ("%", None), "percent-relative-humidity": ("%", "humidity"),
    "pascals": ("Pa", "pressure"), "hectopascals": ("hPa", "pressure"),
    "kilopascals": ("kPa", "pressure"), "bars": ("bar", "pressure"),
    "millibars": ("mbar", "pressure"),
    "watts": ("W", "power"), "kilowatts": ("kW", "power"),
    "watt-hours": ("Wh", "energy"), "kilowatt-hours": ("kWh", "energy"),
    "volts": ("V", "voltage"), "amperes": ("A", "current"),
    "hertz": ("Hz", "frequency"), "seconds": ("s", "duration"),
    "minutes": ("min", "duration"), "hours": ("h", "duration"),
    "liters-per-second": ("L/s", "volume_flow_rate"),
    "liters-per-minute": ("L/min", "volume_flow_rate"),
    "cubic-meters-per-hour": ("m³/h", "volume_flow_rate"),
    "meters-per-second": ("m/s", "speed"),
}
metadata_cache = {}
bridge = None


class MQTTBridge:
    def __init__(self):
        # Supervisor supplies local service credentials; never log or persist them.
        request = urllib.request.Request(
            "http://supervisor/services/mqtt",
            headers={"Authorization": "Bearer " + os.environ["SUPERVISOR_TOKEN"]},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.load(response)
        if result.get("result") != "ok":
            raise RuntimeError("Service MQTT indisponible")
        service = result["data"]
        self.root = "bacnet_reader/" + TARGET_IP.replace(".", "_")
        self.availability = self.root + "/availability"
        self.connected = threading.Event()
        self.configs = {}
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="bacnet_reader_" + TARGET_IP.replace(".", "_"),
            protocol=mqtt.MQTTv5,
        )
        self.client.username_pw_set(service["username"], service["password"])
        if service.get("ssl"):
            self.client.tls_set()
        self.client.will_set(self.availability, "offline", qos=1, retain=True)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.reconnect_delay_set(1, 60)
        self.client.max_queued_messages_set(2000)
        self.client.connect_async(service["host"], int(service["port"]), 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("Connexion MQTT refusée : %s", reason_code)
            return
        self.configs.clear()
        self.connected.set()
        client.publish(self.availability, "online", qos=1, retain=True)
        log.info("MQTT connecté : publication des entités Home Assistant active.")

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.connected.clear()

    def publish(self, topic, payload, retain=False):
        if not self.connected.is_set():
            return False
        if isinstance(payload, dict):
            payload = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        return self.client.publish(topic, payload, qos=1, retain=retain).rc == mqtt.MQTT_ERR_SUCCESS

    def device(self, device_id, info):
        return {
            "identifiers": [f"bacnet_reader_{TARGET_IP}_{device_id}"],
            "name": info.get("objectName") or f"CPO {device_id}",
            "manufacturer": info.get("vendorName") or "BACnet",
            "model": info.get("modelName") or "BACnet/IP",
            "sw_version": info.get("firmwareRevision") or "unknown",
        }

    def sensor(self, device_id, info, key, name, value, attrs=None,
               binary=False, unit=None, device_class=None, diagnostic=False):
        component = "binary_sensor" if binary else "sensor"
        unique = f"bacnet_{TARGET_IP.replace('.', '_')}_{device_id}_{key}"
        topic = f"{self.root}/{device_id}/{key}"
        config = {
            "name": name, "unique_id": unique, "state_topic": topic + "/state",
            "device": self.device(device_id, info),
            "availability_topic": self.availability,
            "expire_after": max(180, DISCOVERY_INTERVAL * 3),
            "origin": {"name": "BACnet Reader", "sw_version": "0.2.0"},
        }
        if binary:
            config.update(payload_on="ON", payload_off="OFF")
        if unit:
            config["unit_of_measurement"] = unit
            if device_class not in ("energy", "duration"):
                config["state_class"] = "measurement"
        if device_class:
            config["device_class"] = device_class
        if diagnostic:
            config["entity_category"] = "diagnostic"
        if attrs is not None:
            config["json_attributes_topic"] = topic + "/attributes"
        config_topic = f"homeassistant/{component}/{unique}/config"
        if self.configs.get(config_topic) != config:
            if self.publish(config_topic, config, retain=True):
                self.configs[config_topic] = config
        if attrs is not None:
            self.publish(topic + "/attributes", attrs, retain=True)
        # Do not retain measurements: stale values must not be replayed as fresh.
        return self.publish(topic + "/state", str(value))

    def close(self):
        if self.connected.is_set():
            message = self.client.publish(self.availability, "offline", qos=1, retain=True)
            message.wait_for_publish(timeout=3)
        self.client.disconnect()
        self.client.loop_stop()


def normalized_value(obj_type, value):
    if value is None:
        return None
    if obj_type.startswith("binary-"):
        text = str(value).lower()
        if text in ("active", "1", "true"):
            return "ON"
        if text in ("inactive", "0", "false"):
            return "OFF"
        return None
    try:
        number = float(value)
        if not math.isfinite(number):
            return None
        return int(number) if obj_type.startswith("multi-state-") else round(number, 4)
    except (TypeError, ValueError):
        return None


async def device_metadata(bacnet, address, device_id):
    key = (device_id, "device")
    if key not in metadata_cache:
        info = {}
        for prop in ("objectName", "vendorName", "modelName", "firmwareRevision"):
            value = await read_property_safe(bacnet, address, "device", device_id, prop)
            if value is not None:
                info[prop] = str(value)
        if info:
            metadata_cache[key] = info
        return info
    return metadata_cache[key]


async def inventory_objects(bacnet, address, device_id):
    started = time.monotonic()
    info = await device_metadata(bacnet, address, device_id)
    objects = await read_property_safe(bacnet, address, "device", device_id, "objectList")
    if objects is None:
        log.warning("Impossible de récupérer objectList.")
        return
    values_read = 0
    values_published = 0
    records = []
    for obj in objects:
        if not running:
            return
        try:
            obj_type, obj_instance = str(obj[0]), int(obj[1])
        except (TypeError, ValueError, IndexError):
            continue
        cache_key = (device_id, obj_type, obj_instance)
        meta = metadata_cache.get(cache_key)
        if meta is None:
            name = await read_property_safe(bacnet, address, obj_type, obj_instance, "objectName")
            units = None
            if obj_type.startswith("analog-"):
                units = await read_property_safe(bacnet, address, obj_type, obj_instance, "units")
            meta = {"name": str(name) if name is not None else f"{obj_type} {obj_instance}",
                    "units": str(units) if units is not None else None}
            if name is not None:
                metadata_cache[cache_key] = meta
        raw = None
        if obj_type in VALUE_TYPES:
            raw = await read_property_safe(bacnet, address, obj_type, obj_instance, "presentValue")
        value = normalized_value(obj_type, raw)
        timestamp = datetime.now(timezone.utc).isoformat()
        attrs = {"device_instance": device_id, "object_type": obj_type,
                 "object_instance": obj_instance, "object_name": meta["name"],
                 "bacnet_units": meta["units"], "address": address,
                 "present_value": str(raw) if raw is not None else None,
                 "last_read": timestamp, "read_only": True}
        records.append(dict(attrs, value=value))
        if value is not None:
            values_read += 1
            unit, device_class = UNITS.get(meta["units"], (None, None))
            if bridge.sensor(device_id, info, f"{obj_type}_{obj_instance}", meta["name"],
                             value, attrs, binary=obj_type.startswith("binary-"),
                             unit=unit, device_class=device_class):
                values_published += 1
        log.debug("OBJECT | %s | %s | %s | value=%s | units=%s",
                  obj_type, obj_instance, meta["name"], raw, meta["units"])
        await asyncio.sleep(0.02)
    timestamp = datetime.now(timezone.utc).isoformat()
    bridge.sensor(device_id, info, "last_update", "Dernière lecture", timestamp,
                  device_class="timestamp", diagnostic=True)
    bridge.sensor(device_id, info, "values_read", "Valeurs lues", values_read, diagnostic=True)
    bridge.sensor(device_id, info, "object_count", "Objets BACnet", len(objects), diagnostic=True)
    bridge.sensor(device_id, info, "poll_duration", "Durée de lecture",
                  round(time.monotonic() - started, 2), unit="s",
                  device_class="duration", diagnostic=True)
    try:
        path = Path("/data/inventory.json")
        path.with_suffix(".tmp").write_text(json.dumps(
            {"updated_at": timestamp, "device": info, "objects": records},
            ensure_ascii=False, indent=2), encoding="utf-8")
        path.with_suffix(".tmp").replace(path)
    except OSError:
        log.warning("Impossible d'enregistrer l'inventaire local.")
    log.info("Inventaire terminé : %s objets, %s valeurs lues, %s publiées dans Home Assistant.",
             len(objects), values_read, values_published)


def normalize_discovered_device(device):
    """
    BAC0 peut faire évoluer légèrement la représentation
    des équipements découverts.

    On évite donc de supposer un format unique.
    """

    try:

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

            device_id = (
                device.get("device_id")
                or device.get("deviceId")
                or device.get("instance")
            )

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
        discovered = await bacnet.who_is(
            address=f"{TARGET_IP}:{BACNET_PORT}", timeout=5
        )

    except Exception as err:
        log.warning("Who-Is : %s", err)
        return

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
    global bridge

    log.info("BACnet Reader démarré.")
    log.info("VERSION : 0.2.0")
    log.info("MODE    : READ ONLY")

    if not test_ip_connectivity():
        sys.exit(1)

    log.info(
        "Ouverture BACnet/IP sur %s",
        LOCAL_IP,
    )

    while running and bridge is None:
        try:
            bridge = await asyncio.to_thread(MQTTBridge)
        except Exception as err:
            log.warning("MQTT pas encore prêt (%s), nouvelle tentative dans 15 s.", type(err).__name__)
            for _ in range(15):
                if not running:
                    return
                await asyncio.sleep(1)

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

    finally:
        if bridge is not None:
            await asyncio.to_thread(bridge.close)

    log.info("BACnet Reader arrêté.")


if __name__ == "__main__":
    asyncio.run(main())
