import typer
from pathlib import Path

APP_NAME = "ntuee_mailer-mailer"
APP_DIR = Path(typer.get_app_dir(APP_NAME))
CONFIG_PATH = Path(APP_DIR) / "config.ini"
