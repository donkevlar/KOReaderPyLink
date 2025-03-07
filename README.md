# KOReaderPyLink
**Koreader position sync server**

## Description

This is a simple implementation of the KOReader (https://github.com/koreader/koreader) position sync server for self-hosting at home which has docker support. *This is a modified fork of b1n4ryj4n/koreader-sync with some additional logging and slightly modified endpoints.*
 
## Dependencies

* FastAPI : https://github.com/tiangolo/fastapi
* TinyDB: https://github.com/msiemens/tinydb
* Uvicorn: https://www.uvicorn.org/
* Python-dotenv: https://saurabh-kumar.com/python-dotenv/

## Environment Variables

* RECEIVE_RANDOM_DEVICE_ID ("True"|"False")

Set it true to retrieve always a random device id to force a progress sync. 
This is usefull if you only sync your progress from one device and 
usually delete the *.sdr files with some cleaning tools.

* OPEN_REGISTRATIONS ("True"|"False")

Enable/disable new registrations to the server. Useful if you want to run a private server for a few users, although it doesn't necessarily improve security by itself.
Set to True (enabled) by default.

* WEBHOOK_ENABLED ("True"|"False")

Enable/disable the discord webhook functionality. Note: Currently only have registrations sending out a notification.

* WEBHOOK_URL (String)

Discord webhook url, `WEBHOOK_ENABLED` must be set to `True` for this to take effect.

## Docker Installation

### Prerequisites
- Install [Docker](https://docs.docker.com/get-docker/)

### Steps
1. Clone the repository:
   ```sh
   git clone https://github.com/donkevlar/KOReaderPyLink.git
   cd KOReaderPyLink
   ```
2. Build and run the container, setting the environment variables:
   ```sh
   docker build -t koreaderpylink .
   docker run -d -v $(pwd)/data:/app/data -p 8081:8081 --name koreaderpylink      -e RECEIVE_RANDOM_DEVICE_ID="False"      -e OPEN_REGISTRATIONS="True"      koreaderpylink
   ```

### Installing through Unraid Template
This is also available via the unraid community application store. Search for `KOReaderPyLink`.

## Connection

* Use http://IP:8081 as custom sync server
* Recommendation: Setup a reverse proxy for example with Nginx Proxy Manager (https://nginxproxymanager.com/) to connect with https

### KOReader Setup
* 1) Navigate to the setup menu (Wrench and screwdriver icon)
* 2) Under "Progress Sync" -> "Custom sync server". Use your server address:  `http://IP:8081` or behind a proxy manager `https://sync.mydomanin.com`. Register using a username and password and you're done!
