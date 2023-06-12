import { IconaBridgeClient, ICONA_BRIDGE_PORT } from "comelit-client";
import { logger } from "./logger.js";

const listDoors = async (host, token) => {
  logger.info("\n\n[start] Fetching available doors...");
  let doors;

  const client = new IconaBridgeClient(host, ICONA_BRIDGE_PORT, logger);
  await client.connect();
  const code = await client.authenticate(token);

  if (code === 200) {
    const addressBookAll = await client.getConfig("all");
    logger.info(`Available doors:`);
    doors = addressBookAll.vip["user-parameters"]["opendoor-address-book"];
    logger.info(doors);
  } else {
    logger.error(
      `Error while authenticating: server responded with code ${code}`
    );
  }

  await client.shutdown();

  logger.info("[done] Fetching available doors\n\n");
  return doors || [];
};

const openDoor = async (host, token, doorName) => {
  logger.log(`\n\n[start] Opening door "${doorName}"...`);
  let response;

  const client = new IconaBridgeClient(host);
  await client.connect();

  try {
    logger.log("Authenticating...");
    const code = await client.authenticate(token);
    logger.log("done.");

    if (code === 200) {
      const addressBook = await client.getConfig("none", false);
      logger.info(addressBook);

      const serverInfo = await client.getServerInfo(false);
      logger.info(serverInfo);

      const addressBookAll = await client.getConfig("all", false);
      logger.info(addressBookAll);

      const item = addressBookAll.vip["user-parameters"][
        "opendoor-address-book"
      ].find((doorItem) => doorItem.name === doorName);

      if (item) {
        logger.info(
          `Opening door ${item.name} at address ${item["apt-address"]} and index ${item["output-index"]}`
        );
        logger.info(await client.getServerInfo());

        await client.openDoor(addressBookAll.vip, item);

        response = {
          name: doorName,
          opened: true,
          error: null,
          timestamp: new Date().toISOString(),
        };
      } else {
        logger.error(
          `No door with name ${doorName} found in config. Available door names are: ${addressBookAll.vip[
            "user-parameters"
          ]["opendoor-address-book"]
            .map((d) => d.name)
            .join(", ")}`
        );
      }
      await client.shutdown();
    } else {
      const errorMessage = `Error while authenticating: server responded with code ${code}`;

      logger.error(errorMessage);
      response = {
        name: doorName,
        opened: false,
        error: { message: errorMessage, details: null },
        timestamp: new Date().toISOString(),
      };
    }
  } catch (e) {
    errorMessage = "Error while executing openDoor command";
    logger.error(errorMessage, e);
    response = {
      name: doorName,
      opened: false,
      error: { message: errorMessage, details: e },
      timestamp: new Date().toISOString(),
    };
  } finally {
    await client.shutdown();
  }

  logger.log(`[done] Opening door "${doorName}"\n\n`);
  return response;
};

export { listDoors, openDoor };
