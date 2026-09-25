#!/usr/bin/with-contenv bashio
set -e
for key in local_ip target_ip bacnet_port discovery_interval metadata_refresh poll_delay read_device_info log_level; do
  env_name=$(echo "$key" | tr '[:lower:]' '[:upper:]')
  export "$env_name"="$(bashio::config "$key")"
done
bashio::log.info "BACnet Reader MCT 0.3.0-phase1 — READ ONLY"
exec python3 -u /bacnet_reader.py
