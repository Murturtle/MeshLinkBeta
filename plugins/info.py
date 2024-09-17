import plugins
import plugins.libdiscordutil as DiscordUtil
import xml.dom.minidom
import cfg
import requests
import time
import plugins.liblogger as logger

class pluginInfo(plugins.Base):

    def __init__(self):
        pass

    def start(self):
        logger.info("Loading info")
    
    def onReceive(self,packet,interface,client):
        final_message = ""
        if("decoded" in packet):
            if(packet["decoded"]["portnum"] == "TEXT_MESSAGE_APP"):
                text = packet["decoded"]["text"]
                if(text.startswith(cfg.config["prefix"])):
                    noprefix = text[len(cfg.config["prefix"]):]

                    if (noprefix.startswith("info")):
                        final_info = "<- info ->\n"+"ping\n"+"time\n"+"weather\n"+"hf\n"+"mesh"
                        interface.sendText(final_info,channelIndex=cfg.config["send_channel_index"],destinationId=packet["toId"])
                        if(cfg.config["send_mesh_commands_to_discord"]):
                                DiscordUtil.send_msg("`MeshLink`> "+final_info,client,cfg.config)

    def onConnect(self,interface,client):
        pass
    
    def onDisconnect(self,interface,client):
        pass