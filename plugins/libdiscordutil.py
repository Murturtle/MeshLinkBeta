import asyncio

def genUserName(interface,packet,details=True):
    if(packet["fromId"] in interface.nodes):
        if(interface.nodes[packet["fromId"]]["user"]):
            ret = "`"+str(interface.nodes[packet["fromId"]]["user"]["shortName"])+" "
            if details:
                ret+= packet["fromId"]+" "
            ret+= str(interface.nodes[packet["fromId"]]["user"]["longName"])+"`"
        else:
            ret = str(packet["fromId"])

        if details:    
            if("position" in interface.nodes[packet["fromId"]]):
                if("latitude" in interface.nodes[packet["fromId"]]["position"] and "longitude" in interface.nodes[packet["fromId"]]["position"]):
                    ret +=" [map](<https://www.google.com/maps/search/?api=1&query="+str(interface.nodes[packet["fromId"]]["position"]["latitude"])+"%2C"+str(interface.nodes[packet["fromId"]]["position"]["longitude"])+">)"
        if("hopLimit" in packet):
            if("hopStart" in packet):
                ret+=" `"+str(packet["hopStart"]-packet["hopLimit"])+"`/`"+str(packet["hopStart"])+"`"
            else:
                ret+=" `"+str(packet["hopLimit"])+"`"
        if("viaMqtt" in packet):
            if str(packet["viaMqtt"]) == "True":
                ret+=" `MQTT`"
        return ret
    else:
        return "`"+str(packet["fromId"])+"`"
    
def send_msg(message,client,config,channel_id=None):
    if config["use_discord"]:
        if (client.is_ready()):
            if config.get("secondary_channel_message_ids") and channel_id > 0:
                for i in config["secondary_channel_message_ids"]:
                    asyncio.run_coroutine_threadsafe(client.get_channel(i).send(message),client.loop)
            for i in config["message_channel_ids"]:
                asyncio.run_coroutine_threadsafe(client.get_channel(i).send(message),client.loop)

def send_info(message,client,config):
    if config["use_discord"]:
        if (client.is_ready()):
            for i in config["info_channel_ids"]:
                asyncio.run_coroutine_threadsafe(client.get_channel(i).send(message),client.loop)