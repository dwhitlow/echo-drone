# ECHO (Experimental Chatbot & Helper / Organizer) Drone

Software for an intelligent agent capable of interacting with its environment via audio/video.

The ultimate goal of this project is for it to run on a quadcopter drone.

The `drone` script provides convenience commands for installing necessary dependencies and running
this software. It should be compatible with most *nix platforms but has only been tested on Ubuntu.

## Setup

If your python version does not match the one specified in `.python-version`, it is highly recommended to install [pyenv](https://github.com/pyenv/pyenv#simple-python-version-management-pyenv).

Some Python standard library modules used by this project may require certain system dependencies. If you see issues such as `ModuleNotFoundError: No module named '_bz2'` while running the project, install the necessary packages, then use pyenv to uninstall and reinstall the correct version of Python. On Ubuntu, the following packages are necessary to build all Python stdlib modules:

```sh
sudo apt-get install -y \
  build-essential \
  libbz2-dev \
  libffi-dev \
  liblzma-dev \
  libreadline-dev \
  libssl-dev \
  libsqlite3-dev \
  tk-dev \
  zlib1g-dev
```

Run `./drone init`. It validates your python version, installs required python build/env packages, and installs python package dependencies to a project-specific virtual environment.

## Assistant Integrations

To leverage some of the AI assistant integrations, you will need to provide your own API credentials.

First, create a file in the project root called `secrets.json`.

### Spotify

1. You must create an application in Spotify's [Developer Dashboard](https://developer.spotify.com/dashboard/applications).
1. Edit the application's settings and add the following redirect URI: `http://localhost:8123/spotify/oauth2_code_callback`
1. Copy the client ID/secret and write them to `secrets.json`:
  ```json
  {
    "spotify": {
      "client_id": "xxxx",
      "client_secret": "xxxx"
    }
  }
  ```

When these secrets are set, a web browser window may pop up to authenticate you when the chatbot or AI assistant is initialized. If you are running this project on a device with limited I/O options, your options are a bit limited since Spotify does not allow public access to its OAuth2 device flow. You can work around these issues by authenticating on a different device, copying the `spotify.refresh_token` value from `secrets.json`, and then updating the secrets file on the original device.

## Usage

Run `./drone help` for a full list of commands, but the core ones are:
* `init`: initializes the project and installs necessary dependencies
* `chat`: starts the chatbot with console input/output

## Development / Testing

Include the `--dev` flag when running `./drone init` and `./drone gen_deps`. This will install dev dependencies.

To record only new network responses for tests, run `VCR_RECORD_MODE=once ./drone test`. To re-record network responses for tests, run `VCR_RECORD_MODE=all ./drone test`.