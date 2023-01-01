import os
from pathlib import Path

from dotenv import load_dotenv

# Absolute path to the project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

TG_TOKEN = os.getenv("TG_TOKEN")
