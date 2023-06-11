# Home Assistant add-on: Comelit CLI MQTT Bridge

![Supports aarch64 Architecture](https://img.shields.io/badge/aarch64-yes-green.svg)
![Supports amd64 Architecture](https://img.shields.io/badge/amd64-yes-green.svg)
![Supports armhf Architecture](https://img.shields.io/badge/armhf-yes-green.svg)
![Supports armv7 Architecture](https://img.shields.io/badge/armv7-yes-green.svg)
![Supports i386 Architecture](https://img.shields.io/badge/i386-yes-green.svg)

If you live in a building with a [Comelit intercom system](https://comelitgroupusa.com/products/intercom/), you might have wondered how to allow to open your front-door via [Home Assistant](https://www.home-assistant.io/).
If your intercom is Wifi connected, like e.g. the [6741w](https://pro.comelitgroup.com/product/6741w), you can use this add-on to add a button that allows to buzz the door open.

## Requirements

You will need
* a running [Home Assistant](https://www.home-assistant.io/) setup
* have [the MQTT integration](https://www.home-assistant.io/integrations/mqtt/) set up (e.g. using the [Mosquitto broker](https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md))
* have a WiFi enabled Comelit intercom in the same network as your Home Assistant machine
* know the IP address if your Comelit intercom device
* have at least one account linked to your Comelit intercom using the mobile app

## Setup

After ensuring that your setup meets the requirements mentioned above, you have to follow these few steps to get up-and-running:

### 1. Get the Comelit User Token

This add-on relies on [Pierpaolo Follia, aka madchicken](https://github.com/madchicken)'s amazing reverse-engineered [Comelit CLI](https://github.com/madchicken/comelit-client) project.
You will need to get a "user token" for your Comelit device.
For this, please follow [madchicken](https://github.com/madchicken)'s walkthrough on how to get this token detailled on [this comelit-client's Wiki page](https://github.com/madchicken/comelit-client/wiki/Get-your-user-token-for-ICONA-Bridge).

### 2. Install the Add-On

Then, you will need to install this add-on on your Home Assistant installation by adding `https://github.com/nicolas-fricke/home-assistant-add-ons` as a custom add-on resository.

After this, you should see the _"Comelit CLI MQTT Bridge"_ appear in your Home Assistant Add-On store.
Click on it and select _"Install"_ to install it.
Wait a bit until the installation has completed.

### 3. Configuration

Lastly, you will need to provide the add-on with two configuration varaibles.
For this, head over to the _"Configure"_ tab.
Here, enter the IP address of your Comelit intercom in the `comelit_ip_address` field.
And then enter the token you gained in step 1. in the `comelit_token` field.

Now, head back to the _"Info"_ tab and start the add-on.
You may want to consider also enabling the _"Start on boot"_ and _"Auto update"_ tags.

### 4. Usage

If you have MQTT Auto Discovery enabled (default), the new button entity for opening your door should have been added to your Home Assistant setup.
You should be able to find it in the MQTT section of your integrations under the virtual _"Comelit Door Control"_ device.

Press the button and your door should buzz open.

## Shortcomings

This add-on can currently *only buzz the recognized doors open*.
It **does not support** any other features like reacing to someone ringing the doorbell, having an intercom conversation, or showing the video stream. It also does not yet support any other actuators than the door open action.

## Working Intercom Systems

This add-on has been successfully tested with the following intercom systems:
* [Comelit 6741w](https://pro.comelitgroup.com/product/6741w)

## Special thanks

Thanks again to [Pierpaolo Follia](https://github.com/madchicken) for his work in reverse engineering the Comelit ICONA protocol and making this available via the [Comelit CLI project](https://github.com/madchicken/comelit-client).

## Contributing

Bug reports and pull requests are welcome on GitHub at https://github.com/nicolas-fricke/home-assistant-add-ons/.
Please make sure to mention that your issue or PR is for the _Comelit CLI MQTT Bridge_.
This project is intended to be a safe, welcoming space for collaboration, and contributors are expected to follow this spirit.

## Disclaimer

This add-on was built for private use.
Use this at your own risk.

The author is in no way associated with Comelit, the Home Assistant team, the Comelit CLI developer, or any other entity related to this project.
The **author does not take any responsibility** for misbehavior.
Make sure to always also carry a key when leaving the house in case of _false-negative misbehavior_ of the add-on which could cause the door to not open when prompted.
Make sure to properly protect your apartment door and, if needed, get your neighbours' consent for the case of _false-positive misbehavior_ of the add-on which could cause the door to open without having been prompted.

## License

This is licensed under _GNU GENERAL PUBLIC LICENSE, version 3_.
Please consult https://github.com/nicolas-fricke/home-assistant-add-ons/blob/master/LICENSE for more information.
