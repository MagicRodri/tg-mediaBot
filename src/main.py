import io
import logging
from pathlib import Path

import cv2
import numpy as np
import pydub
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="I'm a bot, please talk to me!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=update.message.text)


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Get the photo
    photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
    img_bytes_array = await photo_file.download_as_bytearray()
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
        # Save the photo
        img_dir = config.BASE_DIR / 'images'
        img_dir.mkdir(parents=True, exist_ok=True)
        img_path = img_dir / f'{update.message.message_id}.jpg'
        cv2.imwrite(str(img_path), img)
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

    # Save the audio
    audio_dir = config.BASE_DIR / 'audios'
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = audio_dir / f'{update.message.message_id}.wav'
    audio.export(audio_path, format='wav', bitrate='16k')
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I received an audio file and saved it.")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I didn't understand that command.")


def main():
    application = ApplicationBuilder().token(config.TG_TOKEN).build()

    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(filters=filters.TEXT & (~filters.COMMAND),
                                  callback=echo)
    photo_handler = MessageHandler(filters=filters.PHOTO, callback=photo)
    audio_handler = MessageHandler(filters=filters.AUDIO | filters.VOICE,
                                   callback=audio)
    unknown_handler = MessageHandler(filters=filters.COMMAND, callback=unknown)

    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(photo_handler)
    application.add_handler(audio_handler)
    application.add_handler(unknown_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
