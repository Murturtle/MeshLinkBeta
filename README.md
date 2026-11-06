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

Use Discord’s Reply action on a forwarded mesh message and send `$send your reply`
(using your configured prefix) to include its Meshtastic reply ID. Mesh replies
to Discord-originated packets link back to the original Discord message. Links
use the existing in-memory cache and expire after restart or cache eviction.

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

## Updating
You may receive a log in the console like this:
`[INFO] New MeshLink update ready https://github.com/Murturtle/MeshLinkBeta`

run `git pull https://github.com/Murturtle/MeshLinkBeta main` to pull the latest version without overriding config
Restart MeshLink after updating. At startup, MeshLink automatically copies the installed version from the local `rev` file into `config.yml`, preserving your other settings and comments. This also happens immediately after a successful update through the interactive prompt. A failed `git pull` does not advance the config revision.

Missing top-level settings from `config-example copy.yml` (or `config-example.yml`, when present) are automatically added to `config.yml` at startup and after a successful interactive update. Existing values and comments are preserved. New settings use the example defaults; review them after updating.

`ignore_update_prompt: True` skips the interactive prompt; it does not automatically download updates. Revision syncing still runs when `check_for_updates` is disabled.

## Suggestions/Feature Requests
Put them in issues.
