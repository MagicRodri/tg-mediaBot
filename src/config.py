import os
from pathlib import Path

import cloudinary
from dotenv import load_dotenv

# Absolute path to the project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

# General configuration
LOCAL_FILES_SAVING = True
CLOUD_FILES_SAVING = True

# Telegram bot token
TG_TOKEN = os.getenv("TG_TOKEN")

# MongoDB configuration
MG_URI = os.getenv("MG_URI")

# Cloudinary configuration
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)