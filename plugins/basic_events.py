import plugins
import plugins.libdiscordutil as DiscordUtil
import cfg
import plugins.liblogger as logger
from meshtastic import mesh_interface

class basicEvents(plugins.Base):

    def __init__(self):
        pass

    def start(self):
        logger.info("Loading basic events")
    
    def onReceive(self, packet, interface, client):
        if cfg.config["verbose_packets"]:
            logger.info("############################################")
            logger.info(packet)
            logger.info("--------------------------------------------")

        final_message = ""
        send_channel = 0
        if "decoded" not in packet:
            final_message += DiscordUtil.genUserName(interface, packet) + " > encrypted/failed"
            DiscordUtil.send_info(final_message, client, cfg.config)

            if cfg.config["verbose_packets"]:
                logger.infoimportant("Failed or encrypted")
            return

        if cfg.config["verbose_packets"]:
            logger.info("Decoded")

        portnum = packet["decoded"]["portnum"]

        if portnum == "TEXT_MESSAGE_APP":
            if "channel" in packet:
                send_channel = int(packet["channel"])
            final_message += DiscordUtil.genUserName(interface, packet, details=False)
            text = packet["decoded"]["text"]

            if packet.get("from") is not None:
                logger.infogreen(f"{packet['fromId']}> {text}")
            else:
                logger.infogreen("Unknown ID> " + text)

            if text.lower() == "meshlink":
                interface.sendText("MeshLink is running on this node - rev " + str(cfg.config["rev"]) + "\n\nuse " + cfg.config["prefix"] + "info for a list of commands", channelIndex=cfg.config["send_channel_index"])

            final_message += " > " + text

            if cfg.config["ping_on_messages"]:
                final_message += " ||" + cfg.config["message_role"] + "||"

            DiscordUtil.send_msg(final_message, client, cfg.config, send_channel)
            return

        if cfg.config["send_packets"]:
            try:
                is_self = packet["fromId"] == interface.getMyNodeInfo()["user"]["id"]
                if is_self and cfg.config["ignore_self"]:
                    if cfg.config["verbose_packets"]:
                        logger.info("Ignoring self")
                else:
                    final_message += DiscordUtil.genUserName(interface, packet) + "> " + str(portnum)
            except TypeError as e:
                logger.infoimportant(f"TypeError: {e}. We don't have our own nodenum yet.")

        DiscordUtil.send_info(final_message, client, cfg.config)
                
            
                

    def onConnect(self,interface,client):
        logger.infogreen("Node connected")


        DiscordUtil.send_msg("MeshLink is now running - rev "+str(cfg.config["rev"]), client, cfg.config)
        if(cfg.config["send_start_stop"]):
            interface.sendText("MeshLink is now running - rev "+str(cfg.config["rev"])+"\n\nuse "+cfg.config["prefix"]+"info for a list of commands",channelIndex = cfg.config["send_channel_index"])

    def onDisconnect(self,interface,client):
        logger.warn("Connection to node has been lost - attemping to reconnect")
        DiscordUtil.send_msg("# Connection to node has been lost",client, cfg.config)
