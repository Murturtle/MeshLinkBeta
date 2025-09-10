import plugins
import plugins.liblogger as logger
import plugins.libinfo as libinfo
import plugins.libmesh as LibMesh
import cfg
import requests
import time
import xml.dom.minidom
from datetime import datetime
import plugins.libcommand as LibCommand

class basicCommands(plugins.Base):

    def __init__(self):
        pass

    def start(self):
        logger.info("Loading basic commands")

        # ping command
        def cmd_ping(packet, interface, client, args):
            return "pong"
        LibCommand.simpleCommand().registerCommand("ping", "pong!", cmd_ping)

        # time command
        def cmd_time(packet, interface, client, args):
            return time.strftime('%H:%M:%S')
        LibCommand.simpleCommand().registerCommand("time", "Sends the current time", cmd_time)

        # weather command
        def cmd_weather(packet, interface, client, args):
            weather_data_res = requests.get(
                f"https://api.open-meteo.com/v1/forecast?latitude={cfg.config['weather_lat']}&longitude={cfg.config['weather_long']}"
                "&hourly=temperature_2m,precipitation_probability&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timeformat=unixtime&timezone=auto"
            )
            weather_data = weather_data_res.json()
            final = ""
            if weather_data_res.ok:
                for j in range(cfg.config["max_weather_hours"]):
                    i = j + int(time.strftime('%H'))
                    final += f"{i % 24} {round(weather_data['hourly']['temperature_2m'][i])}F {weather_data['hourly']['precipitation_probability'][i]}%\n"
                final = final[:-1]
            else:
                final = "error fetching"
            logger.info(final)
            return final
        LibCommand.simpleCommand().registerCommand("weather", "Gets the weather", cmd_weather)

        # hf command
        def cmd_hf(packet, interface, client, args):
            final = ""
            solar = requests.get("https://www.hamqsl.com/solarxml.php")
            if solar.ok:
                solarxml = xml.dom.minidom.parseString(solar.text)
                for i in solarxml.getElementsByTagName("band"):
                    final += f"{i.getAttribute('time')[0]}{i.getAttribute('name')} {i.childNodes[0].data}\n"
                final = final[:-1]
            else:
                final = "error fetching"
            logger.info(final)
            return final
        LibCommand.simpleCommand().registerCommand("hf", "Get HF radio conditions", cmd_hf)

        # mesh command
        #def cmd_mesh(packet, interface, client, args):
        #    final = "<- Mesh Stats ->"
        #    final += "\nWARNING NODES DO NOT REPORT CHUTIL WHEN CHUTIL IS HIGH"

        #    nodes_with_chutil = 0
        #    total_chutil = 0
        #    for i in interface.nodes:
        #        a = interface.nodes[i]
        #        if "deviceMetrics" in a:
        #            if "channelUtilization" in a['deviceMetrics']:
        #                nodes_with_chutil += 1
        #                total_chutil += a['deviceMetrics']["channelUtilization"]

        #    if nodes_with_chutil > 0:
        #        avg_chutil = total_chutil / nodes_with_chutil
        #        avg_chutil = round(avg_chutil, 1)
        #        final += "\n chutil avg: " + str(avg_chutil)
        #    else:
        #        final += "\n chutil avg: N/A"
        #    return final
        #LibCommand.simpleCommand().registerCommand("mesh", "Check channel utilization", cmd_mesh)

        # savepos command
        def cmd_savepos(packet, interface, client, args):
            lat, long, hasPos = LibMesh.getPosition(interface, packet)
            name = LibMesh.getUserLong(interface, packet)
            if hasPos:
                interface.sendWaypoint(
                    name,
                    description=datetime.now().strftime("%H:%M, %m/%d/%Y"),
                    latitude=lat,
                    longitude=long,
                    channelIndex=cfg.config["send_channel_index"],
                    expire=2147483647
                )
                return f"{name} {lat} {long}"
            else:
                return "No position found!"
        LibCommand.simpleCommand().registerCommand("savepos", "Saves your position", cmd_savepos)