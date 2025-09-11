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
                final = "Error fetching"
            logger.info(final)
            return final
        LibCommand.simpleCommand().registerCommand("weather", "Gets the weather", cmd_weather)

        # aqi command
        def cmd_weather(packet, interface, client, args):
            final = ""
            aqi_data_res = requests.get(
                f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={cfg.config['weather_lat']}&longitude={cfg.config['weather_long']}&current=us_aqi,us_aqi_pm2_5,us_aqi_pm10,us_aqi_nitrogen_dioxide,us_aqi_carbon_monoxide,us_aqi_ozone,us_aqi_sulphur_dioxide&timezone=auto&forecast_hours=1&past_hours=1&timeformat=unixtime"
            )
            aqi_data = aqi_data_res.json()
            final += f"AQI: {aqi_data["current"]["us_aqi"]}\n"
            final += f"PM2.5: {aqi_data["current"]["us_aqi_pm2_5"]}\n"
            final += f"PM10: {aqi_data["current"]["us_aqi_pm10"]}\n"
            final += f"NO2: {aqi_data["current"]["us_aqi_nitrogen_dioxide"]}\n"
            final += f"CO: {aqi_data["current"]["us_aqi_carbon_monoxide"]}\n"
            final += f"O3: {aqi_data["current"]["us_aqi_ozone"]}\n"
            final += f"SO2: {aqi_data["current"]["us_aqi_sulphur_dioxide"]}"
            if aqi_data_res.ok:
                print(aqi_data)
            else:
                final = "Error fetching"
            logger.info(final)
            return final
        LibCommand.simpleCommand().registerCommand("aqi", "Gets the AQI", cmd_weather)

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