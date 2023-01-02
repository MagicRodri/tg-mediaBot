import datetime
import io
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

# isort: off
import config
# isort: on
import cv2
import numpy as np
import pydub
from cloudinary.uploader import upload
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from db import audios, images, users
from utils import get_media_current_index

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    start_message = """Hello! I'm a bot that can:
    - Save audio files in .wav format.
    - Save photos with faces.

    By using this bot, you agree to the following privacy policy:
    1. We use your Telegram ID to identify you.
    2. We store your Telegram ID and the media you send to us.
    3. We do not share your Telegram ID or media with anyone.
    4. We do not use your Telegram ID or media for any other purpose.
    5. We do not store any other information about you.
    6. We do not use cookies or other tracking technologies.
    7. We do not collect any other information about you.
    8. We do not sell your Telegram ID or media to anyone.
    """

    keyboad = [
        [InlineKeyboardButton("I agree", callback_data="True")],
        [InlineKeyboardButton("I do not agree", callback_data="False")],
    ]
    keyboad_markup = InlineKeyboardMarkup(keyboad)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=start_message,
        reply_markup=keyboad_markup,
    )


async def agreement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the user's agreement to the privacy policy.
    """

    query = update.callback_query
    await query.answer()
    if query.data == "True":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Thank you for agreeing to our privacy policy.")
        username = query.from_user.username
        user_id = query.from_user.id
        user_count = users.count_documents({
            "username": username,
            "user_id": user_id
        })
        user_exists = bool(user_count)
        if not user_exists:
            current_time = datetime.datetime.utcnow().strftime(
                "%Y-%m-%d %H:%M:%S")
            # no yapf: disable
            users.insert_one({
                "username": username,
                "user_id": user_id,
                "date_created": datetime.datetime.fromisoformat(current_time)
            })
            # no yapf: enable
    elif query.data == "False":
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Sorry, you can't use this bot.")


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save a photo with a face in it."""

    # Get the photo
    image_file = await context.bot.get_file(update.message.photo[-1].file_id)
    img_bytes_array = await image_file.download_as_bytearray()
    img_array = np.asarray(img_bytes_array, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # face detection
    CV_DATA_PATH = Path(cv2.__file__).parent / 'data'
    face_cascade = cv2.CascadeClassifier(
        str(CV_DATA_PATH / 'haarcascade_frontalface_default.xml'))
    faces = face_cascade.detectMultiScale(img_gray,
                                          1.1,
                                          4,
                                          minSize=(30, 30),
                                          flags=cv2.CASCADE_SCALE_IMAGE)

    # Check if a face was found
    if len(faces) > 0:
        format = image_file.file_path.split('.')[-1]
        username = update.message.from_user.username
        if not username:
            username = str(update.message.from_user.id)
        current_photo_index = get_media_current_index(username=username,
                                                      media_collection=images)
        filename = f'photo_message_{current_photo_index}.{format}'
        # Save the photo
        if config.LOCAL_FILES_SAVING:
            img_dir = config.BASE_DIR / 'images' / username
            img_dir.mkdir(parents=True, exist_ok=True)
            img_path = img_dir / filename
            cv2.imwrite(str(img_path), img)

        response = None
        if config.CLOUD_FILES_SAVING:
            folder = f"telegram-media-bot/images/{username}"
            response = upload(
                io.BytesIO(img_bytes_array),
                folder=folder,
                filename=filename,
                unique_filename=False,
                use_filename=True,
            )
        current_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        # no yapf: disable
        images.insert_one({
            "sender": username,
            "index": current_photo_index,
            "local_path": str(img_path) if config.LOCAL_FILES_SAVING else None,
            "cloud_path": response["secure_url"] if config.CLOUD_FILES_SAVING else None,
            "date_created": datetime.datetime.fromisoformat(current_time),
        })
        # no yapf: enable
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="I found a face and saved the image.")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Sorry, I didn't find any face.")


async def audio(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Get the audio
    if update.message.audio:
        audio_file = await context.bot.get_file(update.message.audio.file_id)
    elif update.message.voice:
        audio_file = await context.bot.get_file(update.message.voice.file_id)
    audio_bytes_array = await audio_file.download_as_bytearray()
    audio = pydub.AudioSegment.from_file(io.BytesIO(audio_bytes_array))

    username = update.message.from_user.username
    if not username:
        username = str(update.message.from_user.id)
    current_user_audio_index = get_media_current_index(username=username,
                                                       media_collection=audios)

    # Save the audio
    format = 'wav'
    filename = f"audio_message_{current_user_audio_index}.{format}"
    if config.LOCAL_FILES_SAVING:
        audio_dir = config.BASE_DIR / 'audios' / username
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / filename
        audio.export(audio_path, format=format, bitrate='16k')

    response = None
    if config.CLOUD_FILES_SAVING:
        audio_file = NamedTemporaryFile(suffix=f'.{format}')
        audio.export(audio_file, format=format, bitrate='16k')
        folder = f"telegram-media-bot/audios/{username}"
        response = upload(
            file=open(audio_file.file.name, 'rb'),
            resource_type=
            "video",  # Cloudinary treats audio as video without visual elements
            folder=folder,
            filename=filename,
            unique_filename=False,
            use_filename=True)

    current_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    # no yapf: disable
    audios.insert_one({
        "sender": username,
        "index": current_user_audio_index,
        "local_path": str(audio_path) if config.LOCAL_FILES_SAVING else None,
        "cloud_path": response["secure_url"] if config.CLOUD_FILES_SAVING else None,
        "date_created": datetime.datetime.fromisoformat(current_time)
    })
    # no yapf: enable
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I received an audio file and saved it.")


async def get_medias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Get the list of medias of a specific type.
    """
    username = update.message.from_user.username
    if not username:
        username = str(update.message.from_user.id)
    try:
        media_type = update.message.text.split(' ')[1]
    except ValueError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You should specify the media type  after the command.")

    if media_type.strip().lower() in ['photos', 'images']:
        media_collection = images
    elif media_type.strip().lower() == 'audios':
        media_collection = audios
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, I don't know this media type.")

    medias = media_collection.find({"sender": username}, {
        "_id": False,
        "cloud_path": True
    })
    if list(medias.clone()) == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Sorry, I didn't find any {media_type}.")
    for media in medias:
        if config.CLOUD_FILES_SAVING:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Cloud path: {media['cloud_path']}")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I didn't understand that command.")


def main():
    application = ApplicationBuilder().token(config.TG_TOKEN).build()

    start_handler = CommandHandler(command='start', callback=start)
    agreement_handler = CallbackQueryHandler(callback=agreement)
    photo_handler = MessageHandler(filters=filters.PHOTO, callback=photo)
    audio_handler = MessageHandler(filters=filters.AUDIO | filters.VOICE,
                                   callback=audio)
    get_medias_handler = MessageHandler(filters=filters.Regex(r'^/get'),
                                        callback=get_medias)
    unknown_handler = MessageHandler(filters=filters.COMMAND, callback=unknown)

    application.add_handler(start_handler)
    application.add_handler(agreement_handler)
    application.add_handler(photo_handler)
    application.add_handler(audio_handler)
    application.add_handler(get_medias_handler)
    application.add_handler(unknown_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
