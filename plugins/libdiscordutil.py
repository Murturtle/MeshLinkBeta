import asyncio
import plugins.libmesh as LibMesh
import discord

def genUserName(interface, packet, details=True):
    short = LibMesh.getUserShort(interface, packet)
    long  = LibMesh.getUserLong(interface, packet) or ""
    lat, lon, hasPos = LibMesh.getPosition(interface, packet)

    #ret = f"**{long}** \n"

    ret = f"Short: ({short}) " if short is not None else " "

    if details:
        if packet.get("fromId") is not None:
            ret += f"_ID: {packet['fromId']}_ \n"

    if details and hasPos:
        ret += f" [map](<https://www.google.com/maps/search/?api=1&query={lat}%2C{lon}>) "

    if "hopLimit" in packet:
        if "hopStart" in packet:
            ret += f"🐇 {packet['hopStart'] - packet['hopLimit']} of {packet['hopStart']} \n"
        else:
            ret += f"🐇 {packet['hopLimit']} \n"

    if "viaMqtt" in packet and str(packet["viaMqtt"]) == "True":
        ret += " `MQTT`"

    return ret

def send_msg(message,client,config,channel_id=0):
    if config["use_discord"]:
        if (client.is_ready()):
            if config.get("secondary_channel_message_ids") and channel_id and channel_id > 0:
                chan = config["secondary_channel_message_ids"][channel_id-1]
                asyncio.run_coroutine_threadsafe(client.get_channel(chan).send(message),client.loop)
            else:
                for i in config["message_channel_ids"]:
                    asyncio.run_coroutine_threadsafe(client.get_channel(i).send(message),client.loop)

def send_embed(title, description, client, config, channel_id=0, footer=None, color=0x3c90ba):
    if config["use_discord"]:
        if (client.is_ready()):
            embed = discord.Embed(title=title, description=description, color=color)
            if footer:
                embed.set_footer(text=footer)
            channels = []
            if config.get("secondary_channel_message_ids") and channel_id and channel_id > 0:
                channels.append(config["secondary_channel_message_ids"][channel_id-1])
            else:
                channels = config["message_channel_ids"]
            for chan_id in channels:
                asyncio.run_coroutine_threadsafe(client.get_channel(chan_id).send(embed=embed), client.loop)

def send_info(message,client,config):
    if config["use_discord"]:
        if (client.is_ready()):
            for i in config["info_channel_ids"]:
                asyncio.run_coroutine_threadsafe(client.get_channel(i).send(message),client.loop)
