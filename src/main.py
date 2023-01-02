from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot import (
    agreement,
    audio,
    get_medias,
    help,
    language,
    language_choice_callback,
    photo,
    start,
    unknown,
)
from config import TG_TOKEN


def main():
    application = ApplicationBuilder().token(TG_TOKEN).build()

    start_handler = CommandHandler(command='start', callback=start)
    language_handler = CommandHandler(command='language', callback=language)
    language_choice_handler = CallbackQueryHandler(
        callback=language_choice_callback)
    agreement_handler = CallbackQueryHandler(callback=agreement)
    photo_handler = MessageHandler(filters=filters.PHOTO, callback=photo)
    audio_handler = MessageHandler(filters=filters.AUDIO | filters.VOICE,
                                   callback=audio)
    get_medias_handler = CommandHandler(command='get', callback=get_medias)
    help_handler = CommandHandler(command='help', callback=help)
    unknown_handler = MessageHandler(filters=filters.COMMAND, callback=unknown)

    application.add_handler(start_handler)
    application.add_handler(agreement_handler, group=0)
    application.add_handler(language_handler)
    application.add_handler(language_choice_handler, group=1)
    application.add_handler(photo_handler)
    application.add_handler(audio_handler)
    application.add_handler(get_medias_handler)
    application.add_handler(help_handler)
    application.add_handler(unknown_handler)

    application.run_polling()


if __name__ == '__main__':
    main()