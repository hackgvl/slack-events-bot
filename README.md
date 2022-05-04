# c4g-events

A Slack bot that relays information from
[OpenUpstate](http://www.openupstate.org/)'s events API to Slack channels!

## Repository

You can find the repository on
[Github](github.com:codeforgreenville/c4g-events).

To download this repo locally, clone it with `git clone
git@github.com:codeforgreenville/c4g-events.git`

## Installation

1. Clone the repo using the instructions above and enter the new directory.
1. Install the python version in `.tool-versions`. I recommend that you use
   [asdf version manager](https://asdf-vm.com/), which will use the version in
   `.tool-versions`.
    1. To use asdf, first follow the [install
     instructions](https://asdf-vm.com/guide/getting-started.html#_1-install-dependencies).
    1. Then, install the python plugin with `asdf plugin-add python`
    1. Then, run `asdf install` and possibly `asdf reshim` to install.
1. Load the environment variables specified in `.envrc.example`. I recommend you
   use [direnv](https://direnv.net/) to keep this per-project.
    1. To use direnv, follow the [instruction
       examples](https://direnv.net/docs/installation.html).
    1. Then, create a slack app following the [Slack Bolt
       tutorial](https://slack.dev/bolt-python/tutorial/getting-started#create-an-app).
    1. Copy `.envrc.example` to `.envrc`, and fill in the private values from
       Slack into `.envrc`. Make sure to never put these values into the code
       directly!
    1. Run `direnv allow` to load the environment variables into your shell.
       This will need to be re-run if there are any changes to `.envrc`.
1. Create a virtual environment with `python -m venv env`.
1. Activate the venv with `source env/bin/activate`
    1. Use `deactivate` to exit the venv if needed.
1. Install dependencies using `pip install -r requirements.txt`
1. Run the app with `python c4g-events.py`!

## Docker instructions

1. Clone the repo using the instructions above and enter the new directory.
1. Run `docker-compose pull` to pull the latest version of the container and
   it's dependencies.
1. Build and start the app with `docker-compose up --force-recreate --no-deps`
    1. You can just start the app by doing `docker-compose up` or
       `docker-compose -d` to run in detached mode.

## License

This bot is licensed under the MIT license.
