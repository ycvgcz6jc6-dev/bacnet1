#!/usr/bin/with-contenv bashio

set -e

LOCAL_IP=$(bashio::config 'local_ip')
TARGET_IP=$(bashio::config 'target_ip')
BACNET_PORT=$(bashio::config 'bacnet_port')
DISCOVERY_INTERVAL=$(bashio::config 'discovery_interval')
READ_DEVICE_INFO=$(bashio::config 'read_device_info')
LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "============================================"
bashio::log.info " BACnet Reader"
bashio::log.info "============================================"
bashio::log.info "Local BACnet interface : ${LOCAL_IP}"
bashio::log.info "Target BACnet device   : ${TARGET_IP}"
bashio::log.info "BACnet UDP port        : ${BACNET_PORT}"
bashio::log.info "Discovery interval     : ${DISCOVERY_INTERVAL}s"
bashio::log.info "Read device info       : ${READ_DEVICE_INFO}"
bashio::log.info "Log level              : ${LOG_LEVEL}"
bashio::log.info "Mode                    : READ ONLY"
bashio::log.info "============================================"

export LOCAL_IP
export TARGET_IP
export BACNET_PORT
export DISCOVERY_INTERVAL
export READ_DEVICE_INFO
export LOG_LEVEL

exec python3 -u /bacnet_reader.py
