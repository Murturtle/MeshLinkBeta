import plugins
import plugins.libdiscordutil as DiscordUtil
import xml.dom.minidom
import cfg
import requests
import time
import plugins.liblogger as logger
import plugins.libinfo as libinfo
from datetime import datetime
import plugins.libmesh as LibMesh

class basicCommands(plugins.Base):

    def __init__(self):
        pass

    def start(self):
        logger.info("Loading basic commands")
        libinfo.info.append("ping - pong!")
        libinfo.info.append("time - sends the time")
        libinfo.info.append("weather - gets the weather")
        libinfo.info.append("hf - get the hf radio conditions")
        libinfo.info.append("mesh - check chutil")
        libinfo.info.append("savepos - saves your position")
        logger.info("Added commands to info")
    
    def onReceive(self, packet, interface, client):
        if "decoded" in packet:
            if packet["decoded"]["portnum"] == "TEXT_MESSAGE_APP":
                final = None

                text = packet["decoded"]["text"]

                if text.startswith(cfg.config["prefix"]):
                    noprefix = text[len(cfg.config["prefix"]):]

                    if noprefix.startswith("ping"):
                        final = "pong"
                        LibMesh.sendReply(final,interface,packet)


                    if noprefix.startswith("savepos"):
                        lat, long, hasPos = LibMesh.getPosition(interface,packet)
                        name = LibMesh.getUserLong(interface,packet)
                        if(hasPos):
                            final= f"{name} {lat} {long}"
                            interface.sendWaypoint(name, description=datetime.now().strftime("%H:%M, %m/%d/%Y"),latitude=lat,longitude=long,channelIndex=cfg.config["send_channel_index"],expire=2147483647) # round(datetime.now().timestamp()+5000)
                        else:
                            final = "No position found!"
                       
                    
                    elif noprefix.startswith("time"):
                        final = time.strftime('%H:%M:%S')
                        LibMesh.sendReply(final,interface,packet)
                        
                    
                    elif noprefix.startswith("weather"):
                        weather_data_res = requests.get("https://api.open-meteo.com/v1/forecast?latitude=" + cfg.config["weather_lat"] + "&longitude=" + cfg.config["weather_long"] + "&hourly=temperature_2m,precipitation_probability&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timeformat=unixtime&timezone=auto")
                        weather_data = weather_data_res.json()
                        final = ""
                        if weather_data_res.ok:
                            for j in range(cfg.config["max_weather_hours"]):
                                i = j + int(time.strftime('%H'))
                                final += str(int(i) % 24) + " "
                                final += str(round(weather_data["hourly"]["temperature_2m"][i])) + "F " + str(weather_data["hourly"]["precipitation_probability"][i]) + "%🌧️\n"
                            final = final[:-1]
                        else:
                            final += "error fetching"
                        logger.info(final)
                        LibMesh.sendReply(final,interface,packet)
                        
                    
                    elif noprefix.startswith("hf"):
                        final = ""
                        solar = requests.get("https://www.hamqsl.com/solarxml.php")
                        if solar.ok:
                            solarxml = xml.dom.minidom.parseString(solar.text)
                            for i in solarxml.getElementsByTagName("band"):
                                final += i.getAttribute("time")[0] + i.getAttribute("name") + " " + str(i.childNodes[0].data) + "\n"
                            final = final[:-1]
                        else:
                            final += "error fetching"
                        logger.info(final)
                        LibMesh.sendReply(final,interface,packet)

                        
                    
                    elif noprefix.startswith("mesh"):
                        final = "<- Mesh Stats ->"
                        final += "\nWARNING NODES DO NOT REPORT CHUTIL WHEN CHUTIL IS HIGH"
                        # channel utilization
                        nodes_with_chutil = 0
                        total_chutil = 0
                        for i in interface.nodes:
                            a = interface.nodes[i]
                            if "deviceMetrics" in a:
                                if "channelUtilization" in a['deviceMetrics']:
                                    nodes_with_chutil += 1
                                    total_chutil += a['deviceMetrics']["channelUtilization"]

                        if nodes_with_chutil > 0:
                            avg_chutil = total_chutil / nodes_with_chutil
                            avg_chutil = round(avg_chutil, 1)  # Round to the nearest tenth
                            final += "\n chutil avg: " + str(avg_chutil)
                        else:
                            final += "\n chutil avg: N/A"
                            
                        

                        LibMesh.sendReply(final,interface,packet)
                    

                    if(final):
                        if cfg.config["send_mesh_commands_to_discord"]:
                            DiscordUtil.send_msg("`MeshLink`> " + final, client, cfg.config)

    def onConnect(self, interface, client):
        pass
    
    def onDisconnect(self, interface, client):
        pass
