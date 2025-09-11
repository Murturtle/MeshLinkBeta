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

        def getLatLong(packet, interface):
            lat, long, hasPos = LibMesh.getPosition(interface, packet)
            if hasPos:
                return (lat, long, True)
            else:
                return (cfg.config['weather_lat'], cfg.config['weather_long'], False)

        # weather command
        def cmd_weather(packet, interface, client, args):
            lat, long, hasPos = getLatLong(packet, interface)
            weather_data_res = requests.get(
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={long}"
                "&hourly=temperature_2m,precipitation_probability&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timeformat=unixtime&timezone=auto"
            )
            weather_data = weather_data_res.json()
            final = ""
            if weather_data_res.ok:
                for j in range(cfg.config["max_weather_hours"]):
                    i = j + int(time.strftime('%H'))
                    final += f"{i % 24} {round(weather_data['hourly']['temperature_2m'][i])}F {weather_data['hourly']['precipitation_probability'][i]}%\n"
                #final = final[:-1] # to remove newline at end
                final += "(Your position)" if hasPos else "(Config position)" 
            else:
                final = "Error fetching"
            logger.info(final)
            return final
        LibCommand.simpleCommand().registerCommand("weather", "Gets the weather", cmd_weather)

        # aqi command
        def cmd_aqi(packet, interface, client, args):
            lat, long, hasPos = getLatLong(packet, interface)
            final = ""
            aqi_data_res = requests.get(
                f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={long}&current=us_aqi,us_aqi_pm2_5,us_aqi_pm10,us_aqi_nitrogen_dioxide,us_aqi_carbon_monoxide,us_aqi_ozone,us_aqi_sulphur_dioxide&timezone=auto&forecast_hours=1&past_hours=1&timeformat=unixtime"
            )
            aqi_data = aqi_data_res.json()
            
            if aqi_data_res.ok:
                final += f"AQI: {aqi_data['current']['us_aqi']}\n"
                final += f"PM2.5: {aqi_data['current']['us_aqi_pm2_5']}\n"
                final += f"PM10: {aqi_data['current']['us_aqi_pm10']}\n"
                final += f"NO2: {aqi_data['current']['us_aqi_nitrogen_dioxide']}\n"
                final += f"CO: {aqi_data['current']['us_aqi_carbon_monoxide']}\n"
                final += f"O3: {aqi_data['current']['us_aqi_ozone']}\n"
                final += f"SO2: {aqi_data['current']['us_aqi_sulphur_dioxide']}\n"
            else:
                final = "Error fetching"
            logger.info(final)
            return final
        LibCommand.simpleCommand().registerCommand("aqi", "Gets the AQI", cmd_aqi)

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
                final = "Error fetching"
            logger.info(final)
            return final
        LibCommand.simpleCommand().registerCommand("hf", "Get HF radio conditions", cmd_hf)


        # elevation command
        def cmd_elevation(packet, interface, client, args):
            lat, long, hasPos = LibMesh.getPosition(interface, packet)
            name = LibMesh.getUserLong(interface, packet)
            if hasPos:
                ele = requests.get(f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={long}")
                if ele.ok:
                    return f"{name} elevation is {ele.json()['elevation'][0]}m asl"
                else:
                    return "Error fetching"
            else:
                return "No position found!"
        LibCommand.simpleCommand().registerCommand("elevation", "Gets your elevation", cmd_elevation)