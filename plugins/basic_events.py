import plugins
import plugins.libdiscordutil as DiscordUtil
import cfg
import plugins.liblogger as logger
from meshtastic import mesh_interface
import plugins.libmesh as LibMesh

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
            # Check if encrypted message is from ignored channels
            encrypted_channel = int(packet["channel"]) if "channel" in packet else 0
            ignored_channels = [1, 2, 3, 4, 5, 6, 7]

            if encrypted_channel not in ignored_channels:
                final_message += DiscordUtil.genUserName(interface, packet) + ": encrypted message"
                DiscordUtil.send_info(final_message, client, cfg.config)
            else:
                logger.info(f"Skipping encrypted message notification for channel {encrypted_channel} (ignored)")

            if cfg.config["verbose_packets"]:
                logger.infoimportant("Failed or encrypted")
            return

        if cfg.config["verbose_packets"]:
            logger.info("Decoded")

        portnum = packet["decoded"]["portnum"]

        if portnum == "TEXT_MESSAGE_APP":
            if "channel" in packet:
                send_channel = int(packet["channel"])
            username = DiscordUtil.genUserName(interface, packet, details=False)
            text = packet["decoded"]["text"]

            if packet.get("from") is not None:
                logger.infogreen(f"{packet['fromId']}> {text}")
            else:
                logger.infogreen("Unknown ID> " + text)

            # Check if message is from ignored channels (1-7)
            ignored_channels = [1, 2, 3, 4, 5, 6, 7]
            is_ignored_channel = send_channel in ignored_channels

            if text.lower() == "meshlink" and not is_ignored_channel:
                LibMesh.sendReply("fl0v is running " + str(cfg.config["rev"]) + "\n\nuse " + cfg.config["prefix"] + "info for a list of commands", interface, packet)

            # Only send to Discord if not from ignored channels
            if not is_ignored_channel:
                title = f"From: {username}"
                description = text
                if cfg.config["ping_on_messages"]:
                    description += f"\n\n{cfg.config['message_role']}"

                DiscordUtil.send_embed(title, description, client, cfg.config, send_channel)
            else:
                logger.info(f"Skipping Discord message for channel {send_channel} (ignored)")
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

        # Check if packet is from ignored channels before sending to Discord
        packet_channel = int(packet["channel"]) if "channel" in packet else 0
        ignored_channels = [1, 2, 3, 4, 5, 6, 7]
        if packet_channel not in ignored_channels:
            DiscordUtil.send_info(final_message, client, cfg.config)
        else:
            logger.info(f"Skipping Discord info for channel {packet_channel} (ignored)")
                
            
                

    def onConnect(self,interface,client):
        logger.infogreen("Node connected")


        DiscordUtil.send_msg("fl0v is running "+str(cfg.config["rev"]), client, cfg.config)
        if(cfg.config["send_start_stop"]):
            interface.sendText("fl0v is running "+str(cfg.config["rev"])+"\n\nuse "+cfg.config["prefix"]+"info for a list of commands",channelIndex = cfg.config["send_channel_index"])

    def onDisconnect(self,interface,client):
        logger.warn("Connection to node has been lost - attemping to reconnect")
        # DiscordUtil.send_msg("# Connection to node has been lost",client, cfg.config)
