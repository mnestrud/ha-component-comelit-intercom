import { connect } from "mqtt"; // import connect from mqtt
import { listDoors, openDoor } from "./comelit-icona-interface.js";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { logger } from "./logger.js";

// Load package.json using fs since Node.js v22 doesn't support assert { type: "json" }
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const packageJSON = JSON.parse(readFileSync(join(__dirname, "package.json"), "utf8"))

const haDiscoveryPrefix = "homeassistant";
const nodeId = "comelitbridge";

const comelitIpAddress = process.env.COMELIT_IP_ADDRESS;
const comelitToken = process.env.COMELIT_TOKEN;
const mqttHost = process.env.MQTT_HOST;
const mqttPort = process.env.MQTT_PORT;
const mqttUsername = process.env.MQTT_USERNAME;
const mqttPassword = process.env.MQTT_PASSWORD;

const comelitTopicPrefix = `${nodeId}/door`;
const availabilityTopic = `${nodeId}/available`;

// Credit to https://www.w3resource.com/javascript-exercises/fundamental/javascript-fundamental-exercise-120.php
const toSnakeCase = (str) =>
  str &&
  str
    .match(/[A-Z]{2,}(?=[A-Z][a-z]+[0-9]*|\b)|[A-Z]?[a-z]+[0-9]*|[A-Z]|[0-9]+/g)
    .map((x) => x.toLowerCase())
    .join("_");

const availableDoors = await listDoors(
  comelitIpAddress,
  comelitToken
);
const topicDoorMapping = availableDoors.reduce((topicDoorMapping, door) => {
  const camelCaseName = toSnakeCase(door.name);
  const doorTopicPrefix = `${comelitTopicPrefix}/${camelCaseName}`;

  topicDoorMapping[`${doorTopicPrefix}/unlatch`] = {
    entityId: `comelit_door_${camelCaseName}_unlatch`,
    name: door.name,
  };

  return topicDoorMapping;
}, {});

logger.log(`\nConnecting to MQTT server ${mqttHost}:${mqttPort} as user ${mqttUsername}...`);
let client = connect({
  servers: [
    {
      host: mqttHost,
      port: mqttPort,
    },
  ],
  username: mqttUsername,
  password: mqttPassword,
  clientId: toSnakeCase(packageJSON.name),
  will: {
    topic: availabilityTopic,
    payload: "false",
    retain: true,
  },
});

client.on("connect", () => {
  logger.log(`↳ done\n`);

  // Not ready to process messages yet
  client.publish(availabilityTopic, "offline", { retain: true });

  Object.keys(topicDoorMapping).forEach((controlTopic) => {
    const door = topicDoorMapping[controlTopic];

    const haDiscoveryTopic = `${haDiscoveryPrefix}/button/${nodeId}/${door.entityId}/config`;

    logger.log(`\nSetting up discovery for door "${door.name}"...`);

    client.publish(
      haDiscoveryTopic,
      JSON.stringify({
        availability_topic: availabilityTopic,
        command_topic: controlTopic,
        device: {
          // configuration_url: `http://${config.comelitIPAddress}:8080`,
          manufacturer: "HA Add On",
          model: "Comelit CLI to Home Assistant MQTT bridge",
          name: "Comelit Door Control",
          via_device: "Comelit Home Assistant Bridge Add On",
          suggested_area: "Entrance",
          sw_version: packageJSON.version,
          identifiers: door.entityId,
        },
        icon: "mdi:door-open",
        name: door.name,
        unique_id: door.entityId,
        retain: true,
      })
    );

    logger.log(`↳ done\n`);

    client.subscribe(controlTopic, (error) => {
      if (error) {
        logger.error(
          `Could not connect to topic "${controlTopic}" because of error: ${error}\n`
        );
        return;
      }

      logger.log(
        `\nSuccessfully subscribed to open commands for door "${door.name}" via "${controlTopic}" MQTT topic\n\n`
      );

      client.publish(availabilityTopic, "online", { retain: true });
    });
  });

  client.on("message", (topic, _message) => {
    const doorName = topicDoorMapping[topic].name;
    logger.log(`\n\n--> Received message on topic ${topic}\n\n`);
    openDoor(comelitIpAddress, comelitToken, doorName);
  });

  client.on("disconnect", () => {
    logger.log(`\n\n--> Received message to disconnect\n\n`);
    client.publish(availabilityTopic, "offline", { retain: true });
  });

  client.on("offline", () => {
    logger.log(`\n\n--> Received message that client goes offline\n\n`);
    client.publish(availabilityTopic, "offline", { retain: true });
  });
});
