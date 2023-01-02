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
from telegram.ext import ContextTypes
from translate import Translator

from db import audios, images, users
from utils import get_media_current_index

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

translator = Translator(to_lang="en")


def _(text):
    return translator.translate(text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    start_message = """Hello! I'm a bot that can:
    - Save audio files in .wav format.
    - Save photos with faces.
    - Return back your saved audio files and photos.

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
        [InlineKeyboardButton(_("I agree"), callback_data="True")],
        [InlineKeyboardButton(_("I do not agree"), callback_data="False")],
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

        text = """
        Thank you for agreeing to our privacy policy.
        You can now send me audio files and photos with faces.
        Use /help to see the list of commands you can use.
        """
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_(text),
        )
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
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Sorry, you can't use this bot."))


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Translate the bot's messages to the user's language.
    """

    language_keyboad = [
        [InlineKeyboardButton(_("English"), callback_data="en")],
        [InlineKeyboardButton(_("Russian"), callback_data="ru")],
        [InlineKeyboardButton(_("French"), callback_data="fr")],
    ]

    language_keyboad_markup = InlineKeyboardMarkup(language_keyboad)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=_("Choose your language:"),
        reply_markup=language_keyboad_markup,
    )


async def language_choice_callback(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the user's choice of language.
    """
    global translator
    query = update.callback_query
    await query.answer()
    language = query.data
    if len(language) != 2:
        return
    translator = Translator(to_lang=language)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=_("Your language is set!"),
    )


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
            text=_("I found a face and saved the image."))
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Sorry, I didn't find any face."))


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
        text=_("I received an audio file and saved it."))


async def get_medias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Get the list of medias of a specific type.
    """
    username = update.message.from_user.username
    if not username:
        username = str(update.message.from_user.id)
    try:
        media_type = context.args[0]
    except IndexError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_(
                "You should specify one media type after the /get command."))
        return

    if media_type.strip().lower() in ['photos', 'images']:
        media_collection = images
    elif media_type.strip().lower() == 'audios':
        media_collection = audios
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Sorry, I don't know this media type."))
        return

    medias = media_collection.find({"sender": username}, {
        "_id": False,
        "cloud_path": True
    })
    if list(medias.clone()):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_(f"Sorry, I didn't find any {media_type}."))
        return
    for media in medias:
        if config.CLOUD_FILES_SAVING:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Cloud path: {media['cloud_path']}")


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_list = [
        '/start - Start the bot',
        '/help - Show this help message',
        '/language - Change the bot language',
        '/get <media_type> - Get the list of medias of a specific type',
    ]
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=_('\n'.join(command_list)))


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=_("Sorry, I didn't understand that command."))


if __name__ == '__main__':
    print(_('Hello'))