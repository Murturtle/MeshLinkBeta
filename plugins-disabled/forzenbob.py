import plugins
import plugins.libdiscordutil as DiscordUtil
import cfg
import plugins.liblogger as logger
import plugins.libinfo as libinfo

class pluginZenbob(plugins.Base):

    def __init__(self):
        pass

    def start(self):
        print("[INFO] Loading forzenbob")
        libinfo.info.append("zenbob - he will never give you up")
    
    def onReceive(self,packet,interface,client):
        final_message = ""
        if("decoded" in packet):
            if(packet["decoded"]["portnum"] == "TEXT_MESSAGE_APP"):
                text = packet["decoded"]["text"]
                if(text.startswith(cfg.config["prefix"])):
                    noprefix = text[len(cfg.config["prefix"]):]

                    if (noprefix.startswith("zenbob")):
                        final_tehe = """Never gonna give you up
Never gonna let you down
Never gonna run around and desert you
Never gonna make you cry
Never gonna say goodbye
Never gonna tell a lie and hurt you"""

                        interface.sendText(final_tehe,channelIndex=cfg.config["send_channel_index"],destinationId=packet["toId"])

    def onConnect(self,interface,client):
        pass
    
    def onDisconnect(self,interface,client):
        pass
