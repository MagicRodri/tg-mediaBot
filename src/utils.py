import pymongo


def user_media_current_index(username: str,
                             media_collection: pymongo.collection.Collection):
    """
    Get the current index of the media of the user.
    """

    last_user_media_index = media_collection.aggregate([{
        "$match": {
            "sender": username
        }
    }, {
        "$group": {
            "_id": "$sender",
            "max_index": {
                "$max": "$index"
            }
        }
    }])
    last_user_media_index = list(last_user_media_index)
    if not len(last_user_media_index) == 0:
        last_user_media_index = last_user_media_index[0]['max_index']
        current_user_media_index = last_user_media_index + 1
    else:
        current_user_media_index = 0
    return current_user_media_index