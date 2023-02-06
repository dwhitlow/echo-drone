from __future__ import annotations

import json
import logging
import os
import threading
import time
import webbrowser
from difflib import SequenceMatcher
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Type
from urllib.parse import parse_qs, urlparse

import spotify

from bot import SECRETS_PATH
from bot.language.assistant.intents.intent import IntentHandler

SUPPORTED_INTENTS = {
  'play_track',
  'queue_track',
  'play_playlist',
  'play_artist_radio',
  'pause_music',
  'resume_music',
  'play_previous_track',
  'play_next_track',
  'raise_music_volume',
  'lower_music_volume',
  'toggle_music_shuffle',
  'toggle_music_repeat',
  'switch_music_device',
}

OAUTH_SCOPES = [
  'playlist-read-collaborative',
  'playlist-read-private',
  'user-modify-playback-state',
  'user-read-currently-playing',
  'user-read-playback-state',
  'user-library-read',
  'streaming',
  'app-remote-control',
]

OAUTH_CALLBACK_HOST = 'localhost'
OAUTH_CALLBACK_PORT = 8123
OAUTH_CODE_CALLBACK_PATH = '/spotify/oauth2_code_callback'
OAUTH_CODE_CALLBACK_URL = \
  f'http://{OAUTH_CALLBACK_HOST}:{OAUTH_CALLBACK_PORT}{OAUTH_CODE_CALLBACK_PATH}'

VOLUME_CHANGE_AMOUNT = 20

logger = logging.getLogger(__name__)


class MusicHandler(IntentHandler):
  """Controls music playback. Currently, only Spotify is supported.

  For a full list of supported commands, see data/assistant/music.yml. Examples:
  - Play Forget Me Nots by Patrice Rushen
  - Lower the volume
  - Skip to the next track"""

  def __init__(
      self,
      client_id: Optional[str] = None,
      client_secret: Optional[str] = None,
      refresh_token: Optional[str] = None,
  ):
    # Disable asyncio spam caused by spotify.py
    logging.getLogger('asyncio').setLevel(logging.CRITICAL)

    secrets = {'spotify': {}}
    if os.path.isfile(SECRETS_PATH):
      with open(SECRETS_PATH, 'r', encoding='utf-8') as f:
        secrets = json.load(f)
    client_id = client_id or secrets['spotify'].get('client_id', None)
    client_secret = client_secret or secrets['spotify'].get('client_secret', None)
    refresh_token = refresh_token or secrets['spotify'].get('refresh_token', None)

    self._auth(client_id, client_secret, refresh_token)

    spotify_secrets = {
      'client_id': client_id,
      'client_secret': client_secret,
      'refresh_token': self.client.refresh_token,
    }
    if 'spotify' not in secrets or secrets['spotify'] != spotify_secrets:
      secrets['spotify'] = spotify_secrets
      with open(SECRETS_PATH, 'w', encoding='utf-8') as f:
        json.dump(secrets, f)

  def _auth(self, client_id: str, client_secret: str, refresh_token: Optional[str] = None) -> None:
    client = spotify.Client(client_id, client_secret)

    if refresh_token is None:
      oauth = spotify.OAuth2(client_id, OAUTH_CODE_CALLBACK_URL, scopes=OAUTH_SCOPES)
      oauth_code = _authorize(oauth.url, OAUTH_CODE_CALLBACK_URL)
      self.user = client.loop.run_until_complete(
        spotify.User.from_code(client, oauth_code, redirect_uri=OAUTH_CODE_CALLBACK_URL))
    else:
      try:
        self.user = client.loop.run_until_complete(
          spotify.User.from_refresh_token(client, refresh_token))
      except spotify.HTTPException:
        logger.warning('Refresh token may be expired', exc_info=True)
        self._auth(client_id, client_secret)

    self.client = self.user.http

  def can_handle(self, intent: dict) -> bool:
    return self._find_intent_name(intent) in SUPPORTED_INTENTS

  def handle(self, intent: dict) -> str:
    track_name = self._find_named_slot_value(intent, 'track', '')
    artist_name = self._find_named_slot_value(intent, 'artist', '')
    playlist_name = self._find_named_slot_value(intent, 'playlist', '')
    device_name = self._find_named_slot_value(intent, 'device', '')

    intent_name = self._find_intent_name(intent)
    match intent_name:
      case 'play_track':
        return self.play_track(track_name, artist_name, device_name)
      case 'queue_track':
        return self.queue_track(track_name, artist_name)
      case 'play_playlist':
        return self.play_playlist(playlist_name, device_name)
      case 'play_artist_radio':
        return self.play_artist_radio(artist_name, device_name)
      case 'pause_music':
        return self.pause_music()
      case 'resume_music':
        return self.resume_music()
      case 'play_previous_track':
        return self.play_previous_track()
      case 'play_next_track':
        return self.play_next_track()
      case 'raise_music_volume':
        return self.raise_volume()
      case 'lower_music_volume':
        return self.lower_volume()
      case 'toggle_music_shuffle':
        return self.toggle_shuffle()
      case 'toggle_music_repeat':
        return self.toggle_repeat()
      case 'switch_music_device':
        return self.switch_device(device_name)

    raise ValueError(f'Unrecognized intent name {intent_name}')

  def play_track(self, track_name: str, artist_name: str = '', device_name: str = '') -> str:
    """Searches for a track with the specified title and artist and queues the first result.
    If a device name is specified, an available device with the most similar name will be used
    for playback."""
    def play(track: spotify.Track) -> None:
      device_id = self.__device_id(device_name)
      self.client.loop.run_until_complete(
        self.client.play_playback([track['uri']], device_id=device_id))

    return self.__operate_on_searched_track('Playing', play, track_name, artist_name)

  def queue_track(self, track_name: str, artist_name: str = '') -> str:
    """Searches for a track with the specified title and artist and queues the first result.
    If a device name is specified, an available device with the most similar name will be used
    for playback."""
    def queue(track: spotify.Track) -> None:
      self.client.loop.run_until_complete(self.client.playback_queue(uri=track['uri']))

    return self.__operate_on_searched_track('Queueing', queue, track_name, artist_name)

  def play_playlist(self, playlist_name: str, device_name: str = '') -> str:
    """Searches for and then plays a Spotify-curated playlist that most closely matches
    the specified artist name"""
    results = self.client.loop.run_until_complete(self.client.current_playlists(limit=50))
    playlists = results['items']
    if not playlists:
      return "I couldn't find any playlists that belong to you"

    self.__sort_results_by_relevance(playlists, 'name', playlist_name)
    playlist = playlists[0]
    logger.debug(f"Found playlist '{playlist['name']}' with relevance {playlist['relevance']}")

    # TODO: Search doesn't seem to include private playlists from the current user
    #   fall back to playlist search if relevance is too low (<0.5?)

    device_id = self.__device_id(device_name)
    self.client.loop.run_until_complete(
      self.client.play_playback(playlist['uri'], device_id=device_id))
    return f"Playing the playlist \"{playlist['name']}\" on Spotify"

  def play_artist_radio(self, artist_name: str, device_name: str = '') -> str:
    """Plays a Spotify-curated playlist that most closely matches the specified artist name"""
    results = self.client.loop.run_until_complete(
      self.client.search(artist_name, query_type='playlist'))
    playlists = [p for p in results['playlists']['items'] if p['owner']['id'] == 'spotify']
    if not playlists:
      return f"I couldn't find any playlists for the artist {artist_name}"

    playlist = playlists[0]
    logger.debug(f"Found playlist '{playlist['name']}' for artist '{artist_name}'")

    device_id = self.__device_id(device_name)
    self.client.loop.run_until_complete(
      self.client.play_playback(playlist['uri'], device_id=device_id))
    return f"Playing the playlist \"{playlist['name']}\" on Spotify"

  def pause_music(self) -> str:
    """Pauses music on the active playback device"""
    try:
      self.client.loop.run_until_complete(self.client.pause_playback())
    except spotify.NotFound:
      return "I couldn't find a Spotify device to pause"
    return 'I paused the music'

  def resume_music(self) -> str:
    """Starts/resumes music on the last active playback device"""
    try:
      self.client.loop.run_until_complete(self.client.play_playback(None))
    except spotify.NotFound:
      return "I couldn't find a Spotify device to resume"
    return "I've resumed the music"

  def play_previous_track(self) -> str:
    """Skips to the previous track on the user's track context"""
    try:
      self.client.loop.run_until_complete(self.client.skip_previous())
    except spotify.NotFound:
      return "I couldn't find a Spotify device to control"
    return 'Started playing the previous track'

  def play_next_track(self) -> str:
    """Skips to next queued track"""
    try:
      self.client.loop.run_until_complete(self.client.skip_next())
    except spotify.NotFound:
      return "I couldn't find a Spotify device to control"
    return 'Started playing the next track'

  def raise_volume(self) -> str:
    """Increases volume on the current device by VOLUME_CHANGE_AMOUNT.
    Returns a failure response if no music is currently playing."""
    return self._change_volume(VOLUME_CHANGE_AMOUNT)

  def lower_volume(self) -> str:
    """Decreases volume on the current device by VOLUME_CHANGE_AMOUNT.
    Returns a failure response if no music is currently playing."""
    return self._change_volume(-VOLUME_CHANGE_AMOUNT)

  def _change_volume(self, amount: int) -> str:
    player = self.client.loop.run_until_complete(self.client.current_player())
    if not player:
      return "I can't do that since no music appears to be playing"
    volume = player['device']['volume_percent']
    new_volume = max(0, min(volume + amount, 100))

    self.client.loop.run_until_complete(self.client.set_playback_volume(new_volume))
    return f'I set the volume to {new_volume} percent'

  def toggle_shuffle(self) -> str:
    """Toggles playback shuffle mode.
    Returns a failure response if no music is currently playing."""
    # TODO: Support explicit on/off commands
    player = self.client.loop.run_until_complete(self.client.current_player())
    if not player:
      return "I can't do that since no music appears to be playing"
    shuffle_state = not player['shuffle_state']

    self.client.loop.run_until_complete(self.client.shuffle_playback(shuffle_state))
    return f"I {'enabled' if shuffle_state else 'disabled'} playback shuffle"

  def toggle_repeat(self) -> str:
    """Toggles playback repeat mode between repeat-track and none.
    Returns a failure response if no music is currently playing."""
    # TODO: Support explicit on/off commands and repeat-track mode
    player = self.client.loop.run_until_complete(self.client.current_player())
    if not player:
      return "I can't do that since no music appears to be playing"
    repeat_state = 'context' if player['repeat_state'] == 'off' else 'off'

    self.client.loop.run_until_complete(self.client.repeat_playback(repeat_state))
    return f"I {'enabled' if repeat_state == 'context' else 'disabled'} playback repeat"

  def switch_device(self, device_name: str) -> str:
    """Begin playing music on the device that most closely matches device_name.
    device_name cannot be an empty string."""
    device_id = self.__device_id(device_name)
    self.client.loop.run_until_complete(self.client.transfer_player(device_id, play=True))

    device_qualifier = ''
    devices = self.client.loop.run_until_complete(self.client.available_devices())['devices']
    if devices:
      devices = [d for d in devices if d['id'] == device_id]
      if devices:
        device = devices[0]
        device_qualifier = f" to {device['name']}"
    return f'I transferred the music playback{device_qualifier}'

  def __operate_on_searched_track(
      self,
      op_verb: str,
      op: callable,
      track_name: str,
      artist_name: str = '',
  ) -> str:
    query = f'track:{track_name}'
    if artist_name != '':
      query += f' artist:{artist_name}'
    results = self.client.loop.run_until_complete(self.client.search(query, query_type='track'))

    if not results['tracks']['items']:
      logger.info(f'No track results found for {query}')
      track_description = track_name
      if artist_name:
        track_description += f' by {artist_name}'
      return f"I couldn't find any results for the track {track_description}"
    track = results['tracks']['items'][0]

    op(track)

    artist_description = ''
    if track['artists']:
      artist_description = f" by {track['artists'][0]['name']}"
    return f"{op_verb} the track {track['name']}{artist_description} on Spotify"

  def __device_id(self, device_name: str = '') -> Optional[str]:
    """Determines which device to play on.
    Returns None if a device is already active and device_name is empty."""
    if device_name == '':
      player = self.client.loop.run_until_complete(self.client.current_player())
      if not player:
        devices = self.client.loop.run_until_complete(self.client.available_devices())['devices']
        if not devices:
          return None
        return devices[0]['id']

    else:
      devices = self.client.loop.run_until_complete(self.client.available_devices())['devices']
      if not devices:
        return None
      self.__sort_results_by_relevance(devices, 'name', device_name)
      device = devices[0]
      logger.debug(f"Found device {device['name']} with relevance {device['relevance']}")
      return device['id']

    return None

  def __sort_results_by_relevance(self, elts: list[dict], key: str, query: str) -> dict:
    for elt in elts:
      elt['relevance'] = SequenceMatcher(None, query, elt[key]).ratio()
    elts.sort(key=lambda e: e['relevance'], reverse=True)


# TODO: if Spotify makes their device OAuth2 flow public, reimplement this using the
#   oauthlib package. spotify.py and requests-oauthlib do not support the device flow.
#   https://oauthlib.readthedocs.io/en/latest/oauth2/clients/deviceclient.html
#   https://community.spotify.com/t5/Spotify-for-Developers/Device-Authorization-Grant-authentication-flow-for-custom/td-p/5485468 # pylint: disable=line-too-long
def _authorize(auth_url: str, code_callback_url: str) -> str:
  logger.info('Authenticating to Spotify. A browser window may open.')
  parsed_auth_url = urlparse(code_callback_url)
  httpd = _OAuthHTTPServer(('', parsed_auth_url.port), _OAuthHTTPHandler, parsed_auth_url.path)

  # Get auth code
  # TODO: Set a timeout of 120s to prevent the project from hanging on init on devices that cannot
  #   display a web browser window to the user
  browser_thread = threading.Thread(target=_start_auth_step, args=(httpd,), daemon=True)
  browser_thread.start()
  time.sleep(1) # Give server time to initialize

  # TODO: Detect if on I/O-limited device (kb/mouse/display check?) and
  #   switch to an alternative auth flow
  browser = webbrowser.get()
  browser.open_new_tab(auth_url)

  browser_thread.join()
  if httpd.code is None:
    raise RuntimeError('An exception occurred in the HTTP server thread')
  return httpd.code


def _start_auth_step(httpd: _OAuthHTTPServer):
  while httpd.code is None:
    httpd.handle_request()
    time.sleep(0.5)


class _OAuthHTTPServer(HTTPServer):
  def __init__(
      self,
      server_address: tuple[str, int],
      handler_class: Type[BaseHTTPRequestHandler],
      oauth_callback_path: str,
  ):
    super().__init__(server_address, handler_class)
    self.oauth_callback_path = oauth_callback_path
    self.code = None


class _OAuthHTTPHandler(BaseHTTPRequestHandler):
  # pylint: disable-next=invalid-name, missing-function-docstring
  def do_GET(self):
    parsed_url = urlparse(self.path)
    if parsed_url.path == self.server.oauth_callback_path:
      self._serve_get_oauth_code(parsed_url)
    else:
      self.send_response(404)
      self.wfile.write(b'Not Found')

  def _serve_get_oauth_code(self, parsed_url):
    params = parse_qs(parsed_url.query)
    self.server.code = params['code'][0]
    self.send_response(200)
    self.wfile.write(b'Authentication complete! Proceeding shortly...')

  def log_message(self, *args):
    args = list(args)
    msg_format = args.pop(0)
    logger.debug(msg_format, *args)
