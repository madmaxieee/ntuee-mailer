import typer
import os
import shutil
import locale
from pathlib import Path

APP_NAME = "ntuee-mailer"
APP_ROOT = Path(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))))
APP_DIR = Path(typer.get_app_dir(APP_NAME))
# make APP_DIR if it doesn't exist
APP_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = Path(APP_DIR) / "config.ini"
if not CONFIG_PATH.is_file():
    shutil.copy(APP_ROOT / "config-default.ini", CONFIG_PATH)

ENCODING = locale.getpreferredencoding()
