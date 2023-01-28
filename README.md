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

Run `./drone init --dev`. It validates your python version, installs required python build/env packages, and installs python package dependencies to a project-specific virtual environment.

## Usage

Run `./drone help` for a full list of commands, but the core ones are:
* `init`: initializes the project and installs necessary dependencies
* `chat`: starts the chatbot with console input/output
