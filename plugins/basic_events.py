import plugins
import plugins.libdiscordutil as DiscordUtil
import cfg
import plugins.liblogger as logger

class basicEvents(plugins.Base):

    def __init__(self):
        pass

    def start(self):
        logger.info("Loading basic events")
    
    def onReceive(self,packet,interface,client):
        if(cfg.config["verbose_packets"]):
            logger.info("############################################")
            logger.info(packet)
            logger.info("--------------------------------------------")
        final_message = ""
        if("decoded" in packet):
            if(cfg.config["verbose_packets"]):
                logger.info("Decoded")
            if(packet["decoded"]["portnum"] == "TEXT_MESSAGE_APP"):
                final_message += DiscordUtil.genUserName(interface,packet,details=False)
                text = packet["decoded"]["text"]

                if(packet["fromId"] != None):
                    logger.infogreen(packet["fromId"]+"> "+text)
                else:
                    logger.infogreen("Unknown ID> "+text)
                
                final_message += " > "+text
                if(cfg.config["ping_on_messages"]):
                    final_message += "\n||"+cfg.config["message_role"]+"||"
                DiscordUtil.send_msg(final_message,client,cfg.config)
            else:
                    if(cfg.config["send_packets"]):
                        try:
                            if((packet["fromId"] == interface.getMyNodeInfo()["user"]["id"]) and cfg.config["ignore_self"]):
                                if(cfg.config["verbose_packets"]):
                                    logger.info("Ignoring self")
                            else:
                                final_message+=DiscordUtil.genUserName(interface,packet)+"> "+str(packet["decoded"]["portnum"])
                        except TypeError as e:
                            logger.infoimportant(f"TypeError: {e}. We don't have our own nodenum yet.")
                    DiscordUtil.send_info(final_message,client,cfg.config)
        else:
            final_message+=DiscordUtil.genUserName(interface,packet)+" > encrypted/failed"
            DiscordUtil.send_info(final_message,client,cfg.config)
            if(cfg.config["verbose_packets"]):
                logger.importantinfo("Failed or encrypted")
                
            
                

    def onConnect(self,interface,client):
        logger.infogreen("Node connected")
        DiscordUtil.send_msg("MeshLink is now running - rev "+str(cfg.config["rev"]), client, cfg.config)
        interface.sendText("MeshLink is now running - rev "+str(cfg.config["rev"])+"\n\nuse "+cfg.config["prefix"]+"info for a list of commands",channelIndex = cfg.config["send_channel_index"])

    def onDisconnect(self,interface,client):
        logger.warn("Connection to node has been lost - attemping to reconnect")
        DiscordUtil.send_msg("# Connection to node has been lost",client, cfg.config)