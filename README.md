# MeshLink (Beta)
## Features

 - Send messages to and from discord
 - Send packet information to discord
 - Plugin system
 
 ### Mesh only
 - Weather forecast
 - Ping
 - HF condition checker
 - Time
 - Mesh statistics

## Commands
**prefix + command**
### Discord
send (message)

### Mesh
ping
weather
hf
time
mesh

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

run `git pull origin main` to pull the latest version without overriding config
Make sure to increment the `rev` setting in `config.yml` or you will keep getting notified that there is an update!

## Suggestions/Feature Requests
Put them in issues.
