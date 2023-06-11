import { IconaBridgeClient } from "comelit-client";

const listDoors = async (host, token) => {
  console.info("\n\n[start] Fetching available doors...");
  let doors;

  const client = new IconaBridgeClient(host);
  await client.connect();
  const code = await client.authenticate(token);

  if (code === 200) {
    const addressBookAll = await client.getConfig("all");
    console.info(`Available doors:`);
    doors = addressBookAll.vip["user-parameters"]["opendoor-address-book"];
    console.info(doors);
  } else {
    console.error(
      `Error while authenticating: server responded with code ${code}`
    );
  }

  await client.shutdown();

  console.info("[done] Fetching available doors\n\n");
  return doors || [];
};

const openDoor = async (host, token, doorName) => {
  console.log(`\n\n[start] Opening door "${doorName}"...`);
  let response;

  const client = new IconaBridgeClient(host);
  await client.connect();

  try {
    console.log("Authenticating...");
    const code = await client.authenticate(token);
    console.log("done.");

    if (code === 200) {
      const addressBook = await client.getConfig("none", false);
      console.info(addressBook);

      const serverInfo = await client.getServerInfo(false);
      console.info(serverInfo);

      const addressBookAll = await client.getConfig("all", false);
      console.info(addressBookAll);

      const item = addressBookAll.vip["user-parameters"][
        "opendoor-address-book"
      ].find((doorItem) => doorItem.name === doorName);

      if (item) {
        console.info(
          `Opening door ${item.name} at address ${item["apt-address"]} and index ${item["output-index"]}`
        );
        console.info(await client.getServerInfo());

        await client.openDoor(addressBookAll.vip, item);

        response = {
          name: doorName,
          opened: true,
          error: null,
          timestamp: new Date().toISOString(),
        };
      } else {
        console.error(
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

      console.error(errorMessage);
      response = {
        name: doorName,
        opened: false,
        error: { message: errorMessage, details: null },
        timestamp: new Date().toISOString(),
      };
    }
  } catch (e) {
    errorMessage = "Error while executing openDoor command";
    console.error(errorMessage, e);
    response = {
      name: doorName,
      opened: false,
      error: { message: errorMessage, details: e },
      timestamp: new Date().toISOString(),
    };
  } finally {
    await client.shutdown();
  }

  console.log(`[done] Opening door "${doorName}"\n\n`);
  return response;
};

export { listDoors, openDoor };
