# MeshLink (Beta)
## Features

 - Send messages to and from discord
 - Send packet information to discord
 - Plugin system (see example plugin in `plugins/testcommand.py`)
 
 ### Mesh only
 - Weather forecast
 - Ping
 - HF condition checker
 - Time
 - Save position as waypoint with timestamp
 - ChatGPT with **optional** plugin
 - Help command with multi page support

## Commands
**prefix + command**
### Discord
send (message)

## Setup 

 1. Download the python script and config-example.yml from Github
 2. Rename config-example.yml to config.yml before editing (step 10)
 3. Install the Meshtastic python CLI https://meshtastic.org/docs/software/python/cli/installation/
 4. Install discord py https://discordpy.readthedocs.io/en/latest/intro.html
 5. Create a discord bot https://discord.com/developers (optional)
 6. Give it admin permission in your server and give it read messages intent (google it if you don't know what to do) (optional)
 7. Invite it to a server (optional)
 8. Get the discord channel id (this is where the messages will go) (again google a tutorial if don't know how to get the channel id) (optional)
 9. Get the discord bot token (optional)
 10. Add your discord bot token and channel id(s) to config.yml (optional)
 11. If you are using serial set `use_serial` to `True` otherwise get your nodes ip and put it into the `radio_ip` setting
 12. configure config.yml to your liking
 14. `python main.py`

## Auto-Start with Cron

A monitoring script (`check_meshlink.sh`) is included to automatically start MeshLink if it stops running.

### Setup

1. Make the script executable:
   ```bash
   chmod +x check_meshlink.sh
   ```

2. Create the cron log file:
   ```bash
   touch meshlink_cron.log
   chmod 644 meshlink_cron.log
   ```

3. Add a cron job (check every 5 minutes):
   ```bash
   crontab -e
   ```
   Add this line (adjust path as needed):
   ```
   */5 * * * * /path/to/MeshLinkBeta/check_meshlink.sh >> /path/to/MeshLinkBeta/meshlink_cron.log 2>&1
   ```

### Requirements
- Virtual environment must exist at `MeshLinkBeta/venv/`
- The cron user must have:
  - Execute permission on `check_meshlink.sh` (`chmod +x`)
  - Write permission on `meshlink_cron.log` (`chmod 644`)
  - Read/execute access to the MeshLinkBeta directory

### Troubleshooting
- Check cron log: `tail -f meshlink_cron.log`
- Test manually: `./check_meshlink.sh`
- Verify cron is set: `crontab -l`

## Updating
You may receive a log in the console like this:
`[INFO] New MeshLink update ready https://github.com/Murturtle/MeshLinkBeta`

run `git pull https://github.com/Murturtle/MeshLinkBeta main` to pull the latest version without overriding config
Make sure to increment the `rev` setting in `config.yml` or you will keep getting notified that there is an update!

## Suggestions/Feature Requests
Put them in issues.
