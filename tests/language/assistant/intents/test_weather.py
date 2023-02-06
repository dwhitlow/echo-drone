import unittest
from datetime import datetime, time, timedelta, timezone

import vcr

from bot.language.assistant.intents.weather import Direction, MoonPhase, PrecipitationType, Weather, WeatherHandler
from tests import EchoTestCase, VCR_RECORD_MODE


class WeatherHandlerTestCase(EchoTestCase):
  def setUp(self):
    self.handler = WeatherHandler()
    self.city = 'San Francisco'
    self.latitude = 37.779
    self.longitude = -122.42
    self.tzinfo = timezone(timedelta(hours=-8))
    self.current_dt = datetime(year=2023, month=2, day=12, tzinfo=self.tzinfo)
    self.intent = {
      'intent': {
        'intentName': 'query_weather',
      },
      'slots': [
        {
          'slotName': 'city',
          'value': {
            'value': self.city,
          },
        },
        {
          'slotName': 'time',
          'value': {
            'value': self.current_dt.isoformat(),
          },
        },
        {
          'slotName': 'attribute',
          'value': {
            'value': 'temperature',
          },
        },
      ],
    }

  def test_can_handle(self):
    self.assertTrue(self.handler.can_handle(self.intent))
    self.intent['intent']['intentName'] = 'not_weather'
    self.assertFalse(self.handler.can_handle(self.intent))

  @unittest.skip('Cassette data is incorrect')
  @vcr.use_cassette('fixtures/weather/fetch_weather.yml', record_mode=VCR_RECORD_MODE)
  def test_handle(self):
    response = self.handler.handle(self.intent)
    self.assertEqual(response, 'Today in San Francisco, the high is 62 and the low is 45.')

  @vcr.use_cassette('fixtures/weather/fetch_weather_today.yml', record_mode=VCR_RECORD_MODE)
  def test_fetch_daily_weather_forecast(self):
    dt = (self.current_dt + timedelta(days=1)).date()
    weather = self.handler.fetch_daily_weather(self.latitude, self.longitude, dt, self.current_dt.date())
    expected_weather = Weather(
      high = 60,
      low = 43,
      precipitation_chance = 6,
      precipitation_amount = 0,
      precipitation_type = PrecipitationType.RAIN,
      wind_speed = 20,
      wind_direction = Direction.WEST,
      sunrise = time(hour=7, minute=1),
      sunset = time(hour=17, minute=46),
      moon_phase = MoonPhase.LAST_QUARTER,
    )
    self.assertEqual(weather, expected_weather)

  @vcr.use_cassette('fixtures/weather/fetch_weather_yesterday.yml', record_mode=VCR_RECORD_MODE)
  def test_fetch_daily_weather_historic(self):
    dt = (self.current_dt - timedelta(days=1)).date()
    weather = self.handler.fetch_daily_weather(self.latitude, self.longitude, dt, self.current_dt.date())
    expected_weather = Weather(
      high = 54,
      low = 42,
      precipitation_chance = 100,
      precipitation_amount = 0.03,
      precipitation_type = PrecipitationType.RAIN,
      sunrise = time(hour=7, minute=5),
      sunset = time(hour=17, minute=45),
    )
    self.assertEqual(weather, expected_weather)

  @vcr.use_cassette('fixtures/weather/fetch_weather_on_date.yml', record_mode=VCR_RECORD_MODE)
  def test_fetch_daily_weather_almanac_and_astro_only(self):
    dt = (datetime(year=2023, month=1, day=1, tzinfo=self.tzinfo)).date()
    weather = self.handler.fetch_daily_weather(self.latitude, self.longitude, dt, self.current_dt.date())
    expected_weather = Weather(
      high = 57,
      low = 46,
      sunrise = time(hour=7, minute=26),
      sunset = time(hour=17, minute=2),
    )
    self.assertEqual(weather, expected_weather)

  def test_format_response_daily_summary(self):
    weather = Weather(
      high = 62,
      low = 40,
      precipitation_chance = 40,
      precipitation_amount = 0.02,
      precipitation_type = PrecipitationType.RAIN,
      wind_speed = 12,
      wind_direction = Direction.NORTH_NORTHWEST,
    )
    response = self.handler.format_response(self.city, self.current_dt.date(), self.current_dt.date(), weather, '')
    self.assertEqual(response, f'Today in {self.city}, the high is 62 and the low is 40. there is a 40 percent chance of rain (0.02 inches).')

  def test_format_response_tomorrow_wind(self):
    dt = (self.current_dt + timedelta(days=1)).date()
    weather = Weather(wind_speed = 12, wind_direction = Direction.NORTH_NORTHWEST)
    response = self.handler.format_response(self.city, dt, self.current_dt.date(), weather, 'wind')
    self.assertEqual(response, f'Tomorrow in {self.city}, there will be 12 mph winds.')

  def test_format_response_tomorrow_precipitation(self):
    dt = (self.current_dt + timedelta(days=1)).date()
    weather = Weather(precipitation_chance = 40, precipitation_amount = 0.02, precipitation_type = PrecipitationType.RAIN)
    response = self.handler.format_response(self.city, dt, self.current_dt.date(), weather, 'precipitation')
    self.assertEqual(response, f'Tomorrow in {self.city}, there will be a 40 percent chance of rain (0.02 inches).')

  def test_format_response_yesterday_precipitation(self):
    dt = (self.current_dt - timedelta(days=1)).date()
    weather = Weather(precipitation_chance = 100, precipitation_amount = 2, precipitation_type = PrecipitationType.RAIN)
    response = self.handler.format_response(self.city, dt, self.current_dt.date(), weather, 'precipitation')
    self.assertEqual(response, f'Yesterday in {self.city}, there were 2 inches of rain.')

  def test_format_response_last_week_sunrise(self):
    dt = (self.current_dt - timedelta(days=3)).date()
    weather = Weather(sunrise=time(hour=7, minute=30, second=0))
    response = self.handler.format_response(self.city, dt, self.current_dt.date(), weather, 'sunrise')
    self.assertEqual(response, f'Last Thursday in {self.city}, the sunrise was at 7:30 AM local time.')

  def test_format_response_week_sunset(self):
    dt = (self.current_dt + timedelta(days=3)).date()
    weather = Weather(sunset=time(hour=17, minute=30, second=0))
    response = self.handler.format_response(self.city, dt, self.current_dt.date(), weather, 'sunset')
    self.assertEqual(response, f'This Wednesday in {self.city}, the sunset will be at 5:30 PM local time.')

  def test_format_response_next_week_moon_phase(self):
    dt = (self.current_dt + timedelta(days=12)).date()
    weather = Weather(moon_phase=MoonPhase.WANING_CRESCENT)
    response = self.handler.format_response(self.city, dt, self.current_dt.date(), weather, 'moon_phase')
    self.assertEqual(response, f'Next Friday in {self.city}, the moon phase will be a waning crescent.')

  def test_format_response_absolute_date_temperature(self):
    dt = datetime(2023, 1, 1, 2, 0, 0, tzinfo=self.tzinfo).date()
    weather = Weather(high = 62, low = 40)
    response = self.handler.format_response(self.city, dt, self.current_dt.date(), weather, 'temperature')
    self.assertEqual(response, f'On January 1, 2023 in {self.city}, the high was 62 and the low was 40.')

  def test_format_response_missing_data(self):
    weather = Weather()
    response = self.handler.format_response(self.city, self.current_dt.date(), self.current_dt.date(), weather, 'temperature')
    self.assertEqual(response, "Sorry, but I couldn't find the requested weather data for that date.")
