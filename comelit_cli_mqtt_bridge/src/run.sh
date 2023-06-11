#!/usr/bin/with-contenv bashio

echo "Fetching user config..."
export COMELIT_IP_ADDRESS=$(bashio::config "comelit_ip_address")
export COMELIT_TOKEN=$(bashio::config "comelit_token")
echo "Got COMELIT_IP_ADDRESS=${COMELIT_IP_ADDRESS} and COMELIT_TOKEN=${COMELIT_TOKEN:+<secret>}"

echo "Checking if MQTT is available..."
bashio::services mqtt > /dev/null
echo "MQTT available: $?"

echo "Fetching MQTT config..."
export MQTT_HOST=$(bashio::services mqtt "host")
export MQTT_PORT=$(bashio::services mqtt "port")
export MQTT_USERNAME=$(bashio::services mqtt "username")
export MQTT_PASSWORD=$(bashio::services mqtt "password")

echo "Got MQTT_HOST=${MQTT_HOST} MQTT_PORT=${MQTT_PORT} MQTT_USERNAME=${MQTT_USERNAME} MQTT_PASSWORD=${MQTT_PASSWORD:+<secret>}"

echo "Starting MQTT server..."
npm start
