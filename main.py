from plugins import Base

# dont change unless you are making a fork
update_check_url = "https://raw.githubusercontent.com/Murturtle/MeshLinkBeta/main/rev"
update_url = "https://github.com/Murturtle/MeshLinkBeta"
import yaml
import xml.dom.minidom
import os
from pubsub import pub
import discord
from meshtastic.tcp_interface import TCPInterface
from meshtastic.serial_interface import SerialInterface
import asyncio
import time
import requests
import cfg
import plugins.liblogger as logger
import signal
 
def handler(signum, frame):
    logger.infogreen("MeshLink is now stopping!")
    interface.sendText("MeshLink is now stopping!",channelIndex = cfg.config["send_channel_index"])
    exit(1)
 
signal.signal(signal.SIGINT, handler)

with open("./config.yml",'r') as file:
    cfg.config = yaml.safe_load(file)

config_options = [
    "rev",
    "max_message_length",
    "message_channel_ids",
    "info_channel_ids",
    "token",
    "prefix",
    "discord_prefix",
    "use_serial",
    "radio_ip",
    "send_channel_index",
    "ignore_self",
    "send_packets",
    "verbose_packets",
    "weather_lat",
    "weather_long",
    "max_weather_hours",
    "ping_on_messages",
    "message_role",
    "use_discord",
    "send_mesh_commands_to_discord"
]

for i in config_options:
    if i not in cfg.config:
        logger.infoimportant("Config option "+i+" missing in config.yml (check github for example)")
        exit()

for i in cfg.config:
    if i not in config_options:
        logger.infoimportant("Config option "+i+" might not needed anymore")

for plugin in Base.plugins:
    inst = plugin()
    inst.start()

oversion = requests.get(update_check_url)
if(oversion.ok):
    if(cfg.config["rev"] < int(oversion.text)):
        for i in range(5):
            logger.infoimportant("New MeshLink update ready "+update_url)
else:
    logger.warn("Failed to check for updates using url "+update_check_url+"\x1b[0m")

intents = discord.Intents.default()
intents.message_content = True
if cfg.config["use_discord"]:
    client = discord.Client(intents=intents)
else:
    client = None

def onConnection(interface, topic=pub.AUTO_TOPIC):
    for p in Base.plugins:
        inst = p()
        inst.onConnect(interface,client)

def onReceive(packet, interface):
    for p in Base.plugins:
        inst = p()
        inst.onReceive(packet,interface,client)
    
def onDisconnect(interface):
    for p in Base.plugins:
        inst = p()
        inst.onDisconnect(interface,client)
    init_radio()

pub.subscribe(onConnection, "meshtastic.connection.established")
pub.subscribe(onDisconnect, "meshtastic.connection.lost")
pub.subscribe(onReceive, "meshtastic.receive")

def init_radio():
    global interface
    if (cfg.config["use_serial"]):
        interface = SerialInterface()
    else:
        interface = TCPInterface(hostname=cfg.config["radio_ip"], connectNow=True)

init_radio()

if cfg.config["use_discord"]:
    @client.event
    async def on_ready():   
        logger.info("Logged in as {0.user} on Discord".format(client))
        #send_msg("ready")

    @client.event
    async def on_message(message):
        global interface
        if message.author == client.user:
            return
        if message.content.startswith(cfg.config["discord_prefix"]+'send'):
            if (message.channel.id in cfg.config["message_channel_ids"]):
                await message.channel.typing()
                trunk_message = message.content[len(cfg.config["discord_prefix"]+"send"):]
                final_message = message.author.name+">"+ trunk_message
                
                if(len(final_message) < cfg.config["max_message_length"] - 1):
                    await message.reply(final_message)
                    interface.sendText(final_message,channelIndex = cfg.config["send_channel_index"])
                    logger.infogreen("\x1b[35;49m"+final_message)
                else:
                    await message.reply("(shortend) "+final_message[:cfg.config["max_message_length"]])
                    interface.sendText(final_message,channelIndex = cfg.config["send_channel_index"])
                    logger.infogreen("\x1b[35;49m"+final_message[:cfg.config["max_message_length"]])
                
            else:
                return

try:
    if cfg.config["use_discord"]:
        client.run(cfg.config["token"],log_handler=None)
    else:
        while True:
            time.sleep(1)
except discord.HTTPException as e:
    if e.status == 429:
        logger.warn("Discord: too many requests")
