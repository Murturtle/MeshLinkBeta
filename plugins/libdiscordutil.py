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

def send_msg(message,client,config):
    print(message)
    if config["use_discord"]:
        if (client.is_ready()):
            for i in config["message_channel_ids"]:
                asyncio.run_coroutine_threadsafe(client.get_channel(i).send(message),client.loop)

def send_info(message,client,config):
    print(message)
    if config["use_discord"]:
        if (client.is_ready()):
            for i in config["info_channel_ids"]:
                asyncio.run_coroutine_threadsafe(client.get_channel(i).send(message),client.loop)