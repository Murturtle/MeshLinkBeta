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
import plugins.libdiscordutil as DiscordUtil
from datetime import datetime
import math
import plugins.libcommand as LibCommand


def handler(signum, frame):
    logger.infogreen("MeshLink is now stopping!")
    if(cfg.config["send_start_stop"]):
        interface.sendText("MeshLink is now stopping!",channelIndex = cfg.config["send_channel_index"])
    exit(1)
 
signal.signal(signal.SIGINT, handler)

with open("./config.yml",'r') as file:
    cfg.config = yaml.safe_load(file)

config_options = [
    "rev",
    "ignore_update_prompt",
    "check_for_updates",
    "use_discord",
    "max_message_length",
    "info_channel_ids",
    "message_channel_ids",
    "secondary_channel_message_ids",
    "token",
    "discord_prefix",
    "ignore_self",
    "send_packets",
    "ping_on_messages",
    "message_role",
    "send_mesh_commands_to_discord",
    "prefix",
    "use_serial",
    "radio_ip",
    "send_channel_index",
    "verbose_packets",
    "send_start_stop",
    "include_username_prefix",
    "weather_lat",
    "weather_long",
    "max_weather_hours"
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

if(cfg.config["check_for_updates"]):
    oversion = requests.get(update_check_url)
    if(oversion.ok):
        if(cfg.config["rev"] < int(oversion.text)):
            logger.infoimportant("New MeshLink update ready "+update_url)
            logger.warn("Remember after the update to double check the plugins you want disabled stay disabled")
            logger.warn("Also remember to increment rev in config.yml")
            if(not cfg.config["ignore_update_prompt"]):
                if(input("       Would you like to update MeshLink? y/n ")=="y"):
                    logger.info("running: git pull "+update_url +" main")
                    os.system("git pull "+update_url+" main")
                    logger.infogreen("Start MeshLink to apply updates!")
                    exit(1)
                else:
                    logger.infoimportant("Ignoring update - use the following command to update: git pull "+update_url+" main")
        else:
            logger.infogreen("MeshLink is up to date! local: " + str(cfg.config["rev"])+" remote: "+str(int(oversion.text)))
    else:
        logger.warn("Failed to check for updates using url "+update_check_url+"\x1b[0m")
else:
    logger.infoimportant("Update checking disabled, change this using check_for_updates in config.yml")

intents = discord.Intents.default()
intents.message_content = True
if cfg.config["use_discord"]:
    client = discord.Client(intents=intents)
else:
    client = None

def onConnection(interface, topic=pub.AUTO_TOPIC):
    for p in Base.plugins:
        inst = p()
        if hasattr(inst, "onConnect") and callable(inst.onConnect):
            inst.onConnect(interface,client)

def onReceive(packet, interface):
    for p in Base.plugins:
        inst = p()
        if hasattr(inst, "onReceive") and callable(inst.onReceive):
            inst.onReceive(packet,interface,client)
    for cmd in LibCommand.commands:
        cmd.onReceive(packet,interface,client)
    
def onDisconnect(interface):
    for p in Base.plugins:
        inst = p()
        if hasattr(inst, "onDisconnect") and callable(inst.onDisconnect):
            inst.onDisconnect(interface,client)
    init_radio()

pub.subscribe(onConnection, "meshtastic.connection.established")
pub.subscribe(onDisconnect, "meshtastic.connection.lost")
pub.subscribe(onReceive, "meshtastic.receive")

def init_radio():
    global interface
    logger.info("Connecting to node...")
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
                if(cfg.config["include_username_prefix"]):
                    final_message = message.author.name+">"+ trunk_message
                else:
                    final_message = trunk_message
                
                if(len(final_message) < cfg.config["max_message_length"] - 1):
                    await message.reply(final_message)
                    interface.sendText(final_message,channelIndex = cfg.config["send_channel_index"])
                    logger.infodiscord(final_message)
                    #DiscordUtil.send_msg("DISCORD: "+final_message,client,cfg.config)
                else:
                    await message.reply("(shortend) "+final_message[:cfg.config["max_message_length"]])
                    interface.sendText(final_message,channelIndex = cfg.config["send_channel_index"])
                    logger.infodiscord(final_message[:cfg.config["max_message_length"]])
                    #DiscordUtil.send_msg("DISCORD: "+final_message,client,cfg.config)
                

                #await message.delete()
                
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