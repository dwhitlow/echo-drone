from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import Optional

import requests

from bot.common.logging import serialize_dict
from bot.language.assistant.intents.intent import IntentHandler

DEFAULT_LOCALE = 'en-US'
DEFAULT_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/109.0',
  'Accept': '*/*',
  'Accept-Language': 'en-US,en;q=0.5',
  'Content-Type': 'application/json',
  'Origin': 'https://weather.com',
  'Referer': 'https://weather.com/',
  'DNT': '1',
  'Connection': 'keep-alive',
  'Sec-Fetch-Dest': 'empty',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Site': 'same-origin',
  'TE': 'trailers',
}

logger = logging.getLogger(__name__)


class WeatherHandler(IntentHandler):
  """Answers queries about the weather. Currently, the only supported time grain is 24h
  (i.e. asking about the weather tomorrow vs tomorrow night vs tomorrow at 4pm will yield
  the same results).

  For a full list of supported commands, see data/assistant/weather.yml. Examples:
  - Will it rain tomorrow?
  - What time will the sun set?
  - What's the weather like today?
  - Will it be windy on Saturday?"""

  def can_handle(self, intent: dict) -> bool:
    return self._find_intent_name(intent) == 'query_weather'

  def handle(self, intent: dict) -> str:
    city = self._find_named_slot_value(intent, 'city', 'San Francisco')
    current_dt = datetime.utcnow()
    dt = datetime.fromisoformat(self._find_named_slot_value(intent, 'time', current_dt.isoformat()))
    current_dt = current_dt.replace(tzinfo=dt.tzinfo)
    attribute = self._find_named_slot_value(intent, 'attribute')

    found_city, latitude, longitude = self.fetch_city_metadata(city)
    weather = self.fetch_daily_weather(latitude, longitude, dt.date(), current_dt.date())
    logger.debug(
      f'Parsed weather forecast/data for {found_city} on {dt}:\n{serialize_dict(vars(weather))}')

    return self.format_response(found_city, dt.date(), current_dt.date(), weather, attribute)

  def fetch_city_metadata(self, city_name_query: str) -> tuple[str, float, float]:
    """Returns metadata for a city name that can be used to fetch weather data"""

    request_data = [
      {
        'name': 'getSunV3LocationSearchUrlConfig',
        'params': {
          'query': city_name_query,
          'language': DEFAULT_LOCALE,
          'locationType': 'locale',
        },
      },
    ]

    response = requests.post(
      'https://weather.com/api/v1/p/redux-dal',
      json = request_data,
      headers = DEFAULT_HEADERS,
      timeout = 5,
    )
    response.raise_for_status()
    response_data = self._get_query_response(
      response.json()['dal'], request_data, 'getSunV3LocationSearchUrlConfig')['location']

    return response_data['city'][0], response_data['latitude'][0], response_data['longitude'][0]

  def fetch_daily_weather(
      self, latitude: float, longitude: float, dt: date, current_dt: date) -> Weather:
    """Combines forecasts and historical data to return weather information for a given date"""

    response, request_data = self._request_daily_weather(latitude, longitude, dt, current_dt)
    response_data = response.json()['dal']

    weather = self._process_forecast_data(response_data, request_data, dt)
    if weather is not None:
      return weather
    return self._process_non_forecast_data(response_data, request_data, dt)

  def _request_daily_weather(
      self,
      latitude: float,
      longitude: float,
      dt: date,
      current_dt: date,
  ) -> tuple[requests.Response, list[dict]]:
    date_str = dt.strftime('%Y%m%d')
    geocode = f'{latitude},{longitude}'
    locale = 'en-US'

    request_data = [
      {
        'name': 'getSunV2AstroUrlConfig',
        'params': {
          'date': date_str,
          'days': '30',
          'geocode': geocode,
          'language': locale,
        },
      },
      {
        'name': 'getSunV3DailyAlmanacUrlConfig',
        'params': {
          'startMonth': dt.month,
          'startDay': 1,
          'days': '45', # Returns 401 if not set to 45
          'geocode': geocode,
          'language': locale,
          'units': 'e',
        },
      },
    ]

    if current_dt <= dt <= current_dt + timedelta(days=15):
      request_data = [
        {
          'name': 'getSunV3DailyForecastWithHeadersUrlConfig',
          'params': {
            'duration': '15day',
            'geocode': geocode,
            'language': locale,
            'units': 'e',
          },
        }
      ]

    elif current_dt - timedelta(days=30) <= dt < current_dt:
      request_data.append({
        'name': 'getSunV3HistoricalDailyConditions30DayUrlConfig',
        'params': {
          'geocode': geocode,
          'language': locale,
          'units': 'e',
        },
      })

    response = requests.post(
      'https://weather.com/api/v1/p/redux-dal',
      json = request_data,
      headers = DEFAULT_HEADERS,
      timeout = 5,
    )
    response.raise_for_status()
    return response, request_data

  def _process_forecast_data(
      self,
      response_data: dict,
      request_data: list[dict],
      dt: date,
  ) -> Optional[Weather]:
    """Process data from forecasts"""

    forecasts = self._get_query_response(
      response_data, request_data, 'getSunV3DailyForecastWithHeadersUrlConfig')
    if forecasts is None:
      return None

    for i, datetime_str in enumerate(forecasts['validTimeLocal']):
      if datetime.fromisoformat(datetime_str).date() == dt:
        weather = Weather()

        weather.high = forecasts['temperatureMax'][i] or forecasts['calendarDayTemperatureMax'][i]
        weather.low = forecasts['temperatureMin'][i] or forecasts['calendarDayTemperatureMin'][i]

        # TODO: Get weather conditions:
        #   Day: forecasts['daypart'][0]['wxPhraseLong'][i] # may be None
        #   Night: forecasts['daypart'][0]['wxPhraseLong'][i+1]

        day_precip_chance = forecasts['daypart'][0]['precipChance'][2*i]
        night_precip_chance = forecasts['daypart'][0]['precipChance'][2*i+1]
        if day_precip_chance is None:
          day_precip_chance = night_precip_chance
        weather.precipitation_chance = math.floor((day_precip_chance + night_precip_chance) / 2)

        if forecasts['qpf'][i] >= forecasts['qpfSnow'][i]:
          weather.precipitation_amount = forecasts['qpf'][i]
          weather.precipitation_type = PrecipitationType.RAIN
        else:
          weather.precipitation_amount = forecasts['qpfSnow'][i]
          weather.precipitation_type = PrecipitationType.SNOW

        day_wind_speed = forecasts['daypart'][0]['windSpeed'][2*i]
        night_wind_speed = forecasts['daypart'][0]['windSpeed'][2*i+1]
        weather.wind_speed = day_wind_speed or night_wind_speed
        day_wind_direction = forecasts['daypart'][0]['windDirectionCardinal'][2*i]
        night_wind_direction = forecasts['daypart'][0]['windDirectionCardinal'][2*i+1]
        weather.wind_direction = Direction(day_wind_direction or night_wind_direction)

        # TODO: Humidity
        # TODO: Thunder

        sunrise_dt = datetime.fromisoformat(forecasts['sunriseTimeLocal'][i])
        weather.sunrise = sunrise_dt.replace(second=0, microsecond=0).time()
        sunset_dt = datetime.fromisoformat(forecasts['sunsetTimeLocal'][i])
        weather.sunset = sunset_dt.replace(second=0, microsecond=0).time()
        weather.moon_phase = MoonPhase(forecasts['moonPhase'][i].lower())

        return weather

    return None

  def _process_non_forecast_data(
      self,
      response_data: dict,
      request_data: list[dict],
      dt: date,
  ) -> Optional[Weather]:
    """When weather data does not fall within available forecast range,
    fall back to historic / almanac / astronomical data"""

    weather = Weather()

    almanac = self._get_query_response(
      response_data, request_data, 'getSunV3DailyAlmanacUrlConfig')
    dt_almanac = dt.strftime('%m%d')
    if almanac is not None:
      for i, date_str in enumerate(almanac['almanacRecordDate']):
        if date_str == dt_almanac:
          weather.high = almanac['temperatureAverageMax'][i]
          weather.low = almanac['temperatureAverageMin'][i]
          break

    historic = self._get_query_response(
      response_data, request_data, 'getSunV3HistoricalDailyConditions30DayUrlConfig')
    if historic is not None:
      for i, datetime_str in enumerate(historic['validTimeLocal']):
        if datetime.fromisoformat(datetime_str).date() == dt:
          weather.high = historic['temperatureMax'][i]
          weather.low = historic['temperatureMin'][i]

          if historic['rain24Hour'][i] >= historic['snow24Hour'][i]:
            weather.precipitation_amount = historic['rain24Hour'][i]
            weather.precipitation_type = PrecipitationType.RAIN
          else:
            weather.precipitation_amount = historic['snow24Hour'][i]
            weather.precipitation_type = PrecipitationType.SNOW
          weather.precipitation_chance = 100 if weather.precipitation_amount > 0 else 0

          break

    astronomy = self._get_query_response(response_data, request_data, 'getSunV2AstroUrlConfig')
    if astronomy is not None:
      for day_data in astronomy['astroData']:
        if datetime.fromisoformat(day_data['dateLocal']).date() == dt:
          sunrise_dt = datetime.fromisoformat(day_data['sun']['riseSet']['riseLocal'])
          weather.sunrise = sunrise_dt.replace(second=0, microsecond=0).time()
          sunset_dt = datetime.fromisoformat(day_data['sun']['riseSet']['setLocal'])
          weather.sunset = sunset_dt.replace(second=0, microsecond=0).time()
          # TODO: Parse moon phase data
          break

    return weather

  def _get_query_response(
      self,
      response_data: dict,
      request_data: list[dict],
      query_name: str,
  ) -> Optional[dict]:
    for query in request_data:
      if query['name'] == query_name:
        if query_name not in response_data:
          logger.error((
            f"weather.com Redux DAL malformed response:\n"
            f"Query Name: {query_name}\n"
            f"Response Keys: {', '.join(list(response_data.keys()))}"
          ))
          return None
        query_response = response_data[query_name][list(response_data[query_name].keys())[0]]
        if query_response['status'] // 100 != 2:
          logger.error((
            f"weather.com Redux DAL query {query_name} failed:\n"
            f"Params:\n{serialize_dict(query['params'])}\n"
            f"Response:\n{serialize_dict(query_response)}"
          ))
          return None
        return query_response['data']
    return None

  def format_response(
      self,
      found_city: str,
      dt: date,
      current_dt: date,
      weather: Weather,
      attribute: str,
  ) -> str:
    """Build a text response for the fetched weather data and the requested attribute"""

    base_response = f'{self._format_response_datetime(dt, current_dt)} in {found_city}'
    verb = self._format_response_verb(dt, current_dt)
    responses = []

    attributes = {attribute}
    if attribute is None or attribute == '':
      attributes = {'temperature', 'precipitation', 'wind'}

    if 'temperature' in attributes and (weather.high is not None or weather.low is not None):
      responses.append(' and '.join([
        f'the high {verb} {weather.high}',
        f'the low {verb} {weather.low}',
      ]))

    if (
      'precipitation' in attributes and
      weather.precipitation_type is not None and
      (len(attributes) == 1 or weather.precipitation_chance > 0)
    ):
      if weather.precipitation_chance == 0:
        responses.append(f'there {verb} no rain')
      elif dt >= current_dt:
        responses.append((
          f'there {verb} a {weather.precipitation_chance} percent chance of '
          f'{weather.precipitation_type} ({weather.precipitation_amount} inches)'
        ))
      else:
        responses.append(
          f'there were {weather.precipitation_amount} inches of {weather.precipitation_type}')

    if (
      'wind' in attributes and
      weather.wind_speed is not None and
      (len(attributes) == 1 or weather.wind_speed >= 20)
    ):
      responses.append(f'there {verb} {weather.wind_speed} mph winds')

    if 'sunrise' in attributes and weather.sunrise is not None:
      responses.append(
        f"the sunrise {verb} at {weather.sunrise.strftime('%I:%M %p').lstrip('0')} local time")

    if 'sunset' in attributes and weather.sunset is not None:
      responses.append(
        f"the sunset {verb} at {weather.sunset.strftime('%I:%M %p').lstrip('0')} local time")

    if 'moon_phase' in attributes and weather.moon_phase is not None:
      responses.append(f"the moon phase {verb} a {weather.moon_phase}")

    if not responses:
      logger.error(f"No data found for {dt} for the following attributes: {', '.join(attributes)}")
      return "Sorry, but I couldn't find the requested weather data for that date."

    return f"{base_response}, {'. '.join(responses)}."

  def _format_response_datetime(self, dt: date, current_dt: date) -> str:
    if dt == current_dt:
      return 'Today'
    elif dt == current_dt + timedelta(days=1):
      return 'Tomorrow'
    elif current_dt < dt < current_dt + timedelta(days=7):
      return f"This {dt.strftime('%A')}"
    elif current_dt + timedelta(days=7) <= dt < current_dt + timedelta(days=14):
      return f"Next {dt.strftime('%A')}"
    elif dt == current_dt - timedelta(days=1):
      return 'Yesterday'
    elif current_dt > dt >= current_dt - timedelta(days=7):
      return f"Last {dt.strftime('%A')}"
    else:
      return f"On {dt.strftime('%B')} {dt.day}, {dt.year}"

  def _format_response_verb(self, dt: date, current_dt: date) -> str:
    if dt == current_dt:
      return 'is'
    elif dt > current_dt:
      return 'will be'
    else:
      return 'was'

@dataclass
class Weather:
  """A collection of weather forecast/historic/almanac data for a given day"""
  high: Optional[int] = None
  low: Optional[int] = None
  precipitation_chance: Optional[int] = None # 0-100
  precipitation_amount: Optional[float] = None # inches
  precipitation_type: Optional[PrecipitationType] = None
  wind_speed: Optional[int] = None # mph
  wind_direction: Optional[Direction] = None
  humidity: Optional[int] = None # 0-100
  # TODO: Thunder
  sunrise: Optional[time] = None
  sunset: Optional[time] = None
  moon_phase: Optional[MoonPhase] = None
  aqi: Optional[int] = None


class PrecipitationType(StrEnum):
  """Enum for different types of precipitation tracked by weather.com"""
  RAIN = 'rain'
  SNOW = 'snow'


class Direction(StrEnum):
  """Enum for all cardinal, intercardinal, and secondary intercardinal directions"""
  NORTH = 'N'
  NORTH_NORTHEAST = 'NNE'
  NORTHEAST = 'NE'
  EAST_NORTHEAST = 'ENE'
  EAST = 'E'
  EAST_SOUTHEAST = 'ESE'
  SOUTHEAST = 'SE'
  SOUTH_SOUTHEAST = 'ESE'
  SOUTH = 'S'
  SOUTH_SOUTHWEST = 'SSW'
  SOUTHWEST = 'SW'
  WEST_SOUTHWEST = 'WSW'
  WEST = 'W'
  WEST_NORTHWEST = 'WNW'
  NORTHWEST = 'NW'
  NORTH_NORTHWEST = 'NNW'


class MoonPhase(StrEnum):
  """Enum of moon phase string values as reported by the weather.com DAL"""
  NEW = 'new moon'
  WAXING_CRESCENT = 'waxing crescent'
  FIRST_QUARTER = 'first quarter'
  WAXING_GIBBOUS = 'waxing gibbous'
  FULL = 'full moon'
  WANING_GIBBOUS = 'waning gibbous'
  LAST_QUARTER = 'last quarter'
  WANING_CRESCENT = 'waning crescent'
