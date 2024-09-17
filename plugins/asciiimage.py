import plugins
import plugins.libdiscordutil as DiscordUtil
import cfg
import cv2
import numpy as np
import plugins.liblogger as logger

# COLORS: https://github.com/onlyphantom/taskquant/blob/main/taskquant/utils/colors.py
#SYMBOLS = [".", "-", "+", "*", "#", "o"]
#THRESHOLDS = [0, 50, 100, 150, 200]
SYMBOLS = [" o"," +", " #"]
THRESHOLDS = [0, 85, 170]

def print_symbols(array):
    """fill symbols in-place of numbers (index)
    """
    len_symbols = len(SYMBOLS)
    ret = ""
    for row in array:
        
        for i in row:
            ret+= SYMBOLS[i % len_symbols]
        ret+="\n"
    return ret



def generate_ascii(img):
    """returns the numeric coded image
    """

    height, width = img.shape
    new_height = 10
    new_width = 10
    
    # resizing image to fit in console for printing
    resized_img = cv2.resize(img, (new_width, new_height))

    # [0, 0, 0, 0, 0]
    # [0, 0, 1, 0, 0]
    # [0, 0, 0, 2, 0]
    # [0, 4, 0, 0, 0]

    thresh_img = np.zeros(resized_img.shape)

    for i, threshold in enumerate(THRESHOLDS):
        thresh_img[resized_img > threshold] = i

    return thresh_img.astype(int)

    

class pluginAscii(plugins.Base):

    def __init__(self):
        pass

    def start(self):
        logger.info("Loading image to ascii")
    
    def onReceive(self,packet,interface,client):
        final_message = ""
        if("decoded" in packet):
            if(packet["decoded"]["portnum"] == "TEXT_MESSAGE_APP"):
                text = packet["decoded"]["text"]
                if(text.startswith(cfg.config["prefix"])):
                    noprefix = text[len(cfg.config["prefix"]):]

                    if (noprefix.startswith("ascii")):
                        final_ascii = ""
                        img = cv2.imread("test.png", 0)
                        ascii_art = generate_ascii(img)
                        final_ascii=print_symbols(ascii_art)
                        print(final_ascii)

                        
                        interface.sendText(final_ascii,channelIndex=cfg.config["send_channel_index"],destinationId=packet["toId"])
                        if(cfg.config["send_mesh_commands_to_discord"]):
                                DiscordUtil.send_msg("`MeshLink`> \n"+final_ascii,client,cfg.config)

    def onConnect(self,interface,client):
        pass
    
    def onDisconnect(self,interface,client):
        pass