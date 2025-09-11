import asyncio
import plugins.libmesh as LibMesh

def genUserName(interface, packet, details=True):
    short = LibMesh.getUserShort(interface, packet)
    long = LibMesh.getUserLong(interface, packet)
    lat, lon, hasPos = LibMesh.getPosition(interface, packet)

    ret = f"`{short} "
    if details:
        ret += f"{packet['fromId']} "
    ret += f"{long}`"

    if details and hasPos:
        ret += f" [map](<https://www.google.com/maps/search/?api=1&query={lat}%2C{lon}>)"

    if "hopLimit" in packet:
        if "hopStart" in packet:
            ret += f" `{packet['hopStart'] - packet['hopLimit']}`/`{packet['hopStart']}`"
        else:
            ret += f" `{packet['hopLimit']}`"

    if "viaMqtt" in packet and str(packet["viaMqtt"]) == "True":
        ret += " `MQTT`"

    return ret
    
def send_msg(message,client,config):
    if config["use_discord"]:
        if (client.is_ready()):
            for i in config["message_channel_ids"]:
                asyncio.run_coroutine_threadsafe(client.get_channel(i).send(message),client.loop)

def send_info(message,client,config):
    if config["use_discord"]:
        if (client.is_ready()):
            for i in config["info_channel_ids"]:
                asyncio.run_coroutine_threadsafe(client.get_channel(i).send(message),client.loop)