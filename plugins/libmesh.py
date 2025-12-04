import cfg

def getUserLong(interface,packet):
    ret=None
    node = getNode(interface,packet)
    if(node and "user" in node):
        ret = str(node["user"]["longName"])
        return ret

    ret = decimal_to_hex(packet["from"])
    return ret

def getUserShort(interface,packet):
    ret=None
    node = getNode(interface,packet)
    if(node and "user" in node):
        ret = str(node["user"]["shortName"])
    return ret

def getNode(interface,packet):
    ret = None
    if(packet["fromId"] in interface.nodes):
        ret = interface.nodes[packet["fromId"]]
    return ret

def decimal_to_hex(decimal_number):
    return f"!{decimal_number:08x}"

def getPosition(interface,packet):
    lat = None
    long = None
    hasPos = False
    
    node = getNode(interface,packet)
    if(packet["fromId"] in interface.nodes):
        if("position" in node):
                if("latitude" in node["position"] and "longitude" in node["position"]):
                    lat = node["position"]["latitude"]
                    long = node["position"]["longitude"]
                    hasPos = True
                     
    return lat, long, hasPos


def sendReply(text, interface, packet, channelIndex = -1):
    ret = packet

    if(channelIndex == -1):
        channelIndex = cfg.config["send_channel_index"]
        
    to = 4294967295 # ^all

    if(packet["to"] == interface.localNode.nodeNum):
         to = packet["from"]
    interface.sendText(text=text,destinationId=to,channelIndex=channelIndex)

    return ret