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