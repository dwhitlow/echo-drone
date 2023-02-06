import time
import unittest

import vcr

from bot.language.assistant.intents.music import MusicHandler
from tests import EchoTestCase, VCR_RECORD_MODE


# TODO: Scrub auth data from requests and responses, implement custom request matcher, and re-enable
@unittest.skip('client is not compatible with vcr.py when record_mode="none"')
class MusicHandlerTestCase(EchoTestCase):
  """NOTE: These tests will fail if spotify.client_id and spotify.client_secret are not set up
  in secrets.json. They will also fail if no playback devices are available.
  test_play_playlist will fail due to its dependence on user-specific data if it is re-recorded.

  The tests will hang if spotify.refresh_token has not been included in secrets.json
  until you authenticate via the browser window that pops up."""

  @vcr.use_cassette('fixtures/music/handle.yml', record_mode=VCR_RECORD_MODE)
  def test_handle(self):
    handler = MusicHandler()
    intent = {
      'intent': {
        'intentName': 'play_track'
      },
      'slots': [
        {
          'slotName': 'artist',
          'value': {
            'value': 'Patrice Rushen'
          }
        },
        {
          'slotName': 'track',
          'value': {
            'value': 'Forget Me Nots'
          }
        }
      ]
    }
    response = handler.handle(intent)
    self.assertEqual(response, 'Playing the track Forget Me Nots by Patrice Rushen on Spotify')

  @vcr.use_cassette('fixtures/music/play_playlist.yml', record_mode=VCR_RECORD_MODE)
  def test_play_playlist(self):
    handler = MusicHandler()
    response = handler.play_playlist('Workshop')
    self.assertEqual(response, 'Playing the playlist "Workshop" on Spotify')

  @vcr.use_cassette('fixtures/music/play_artist_radio.yml', record_mode=VCR_RECORD_MODE)
  def test_play_artist_radio(self):
    handler = MusicHandler()
    response = handler.play_artist_radio('Childish Gambino')
    self.assertEqual(response, 'Playing the playlist "This Is Childish Gambino" on Spotify')

  @vcr.use_cassette('fixtures/music/controls.yml', record_mode=VCR_RECORD_MODE)
  def test_controls(self):
    handler = MusicHandler()

    response = handler.play_track('Forget Me Nots', 'Patrice Rushen')
    self.assertEqual(response, 'Playing the track Forget Me Nots by Patrice Rushen on Spotify')

    time.sleep(0.5)
    response = handler.pause_music()
    self.assertEqual(response, 'I paused the music')

    time.sleep(0.5)
    response = handler.resume_music()
    self.assertEqual(response, "I've resumed the music")

    time.sleep(0.5)
    response = handler.lower_volume()
    self.assertRegex(response, r'I set the volume to \d+ percent')

    time.sleep(0.5)
    response = handler.raise_volume()
    self.assertRegex(response, r'I set the volume to \d+ percent')

    time.sleep(0.5)
    response = handler.switch_device('any')
    self.assertRegex(response, r'I transferred the music playback.*')

  @vcr.use_cassette('fixtures/music/multi_track_controls.yml', record_mode=VCR_RECORD_MODE)
  def test_multi_track_controls(self):
    handler = MusicHandler()

    response = handler.play_artist_radio('Childish Gambino')

    time.sleep(0.5)
    response = handler.play_next_track()
    self.assertEqual(response, 'Started playing the next track')

    time.sleep(0.5)
    response = handler.play_previous_track()
    self.assertEqual(response, 'Started playing the previous track')

    time.sleep(0.5)
    response = handler.queue_track('Before I Let Go', 'Maze')
    self.assertEqual(response, 'Queueing the track Before I Let Go by Maze on Spotify')

    time.sleep(0.5)
    response = handler.toggle_shuffle()
    self.assertRegex(response, r'I (enabled|disabled) playback shuffle')

    time.sleep(0.5)
    response = handler.toggle_repeat()
    self.assertRegex(response, r'I (enabled|disabled) playback repeat')
