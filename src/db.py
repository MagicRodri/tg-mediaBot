import dns
import pymongo

import config

client = pymongo.MongoClient(config.MG_URI)
db = client['telegram-media-bot']
users = db.users
photos = db.photos
audios = db.audios

if __name__ == '__main__':
    print(db.list_collection_names())