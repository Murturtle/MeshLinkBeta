import plugins
import plugins.liblogger as logger
import plugins.libmesh as LibMesh
import plugins.libcommand as LibCommand
import cfg
import requests
from datetime import datetime, timezone

class weatherCommand(plugins.Base):
    """Weather plugin that fetches forecast from National Weather Service API"""

    def __init__(self):
        pass

    def start(self):
        logger.info("Loading weather command")

        def cmd_weather(packet, interface, client, args):
            """Get weather forecast for the next 24 hours from NWS"""
            try:
                # Get location - try user's position first, fall back to config
                lat, lon, hasPos = LibMesh.getPosition(interface, packet)
                
                if not hasPos:
                    # Fall back to configured location
                    lat = cfg.config.get("weather_lat", "45.516022")
                    lon = cfg.config.get("weather_long", "-122.681427")
                
                # Round coordinates for API
                lat = float(lat)
                lon = float(lon)
                
                # Step 1: Get grid points from NWS
                points_url = f"https://api.weather.gov/points/{lat},{lon}"
                headers = {
                    "User-Agent": "MeshLink Weather Bot",
                    "Accept": "application/geo+json"
                }
                
                points_response = requests.get(points_url, headers=headers, timeout=10)
                if points_response.status_code != 200:
                    return f"Weather API error: {points_response.status_code}"
                
                points_data = points_response.json()
                
                # Get forecast URL from response
                forecast_url = points_data["properties"]["forecast"]
                location_name = points_data["properties"]["relativeLocation"]["properties"]["city"]
                state = points_data["properties"]["relativeLocation"]["properties"]["state"]
                
                # Step 2: Get the forecast
                forecast_response = requests.get(forecast_url, headers=headers, timeout=10)
                if forecast_response.status_code != 200:
                    return f"Forecast API error: {forecast_response.status_code}"
                
                forecast_data = forecast_response.json()
                periods = forecast_data["properties"]["periods"]
                
                # Build compact response for next 24 hours
                result = f"{location_name}, {state}\n"
                
                # Get first 2 periods (covers ~24 hours)
                for i, period in enumerate(periods[:2]):
                    name = period["name"][:8]  # Truncate period name
                    temp = period["temperature"]
                    unit = period["temperatureUnit"]
                    forecast = period["shortForecast"]
                    
                    # Keep forecast very short for mesh
                    if len(forecast) > 20:
                        forecast = forecast[:17] + "..."
                    
                    result += f"{name}: {temp}{unit} {forecast}\n"
                
                return result.strip()
                
            except requests.exceptions.Timeout:
                return "Weather request timed out"
            except requests.exceptions.RequestException as e:
                return f"Weather request failed: {str(e)[:30]}"
            except KeyError as e:
                return f"Weather data parse error"
            except Exception as e:
                logger.error(f"Weather command error: {e}")
                return "Weather unavailable"

        LibCommand.simpleCommand().registerCommand("weather", "Get 24hr weather forecast", cmd_weather)
