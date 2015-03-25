import shelve
from ..apis.text import text_processing
from ..apis.text import text_to_emotion

class Emotext():
    """
    Represents the utility class for using Emotext.
    Provides all methods to use Emotext.
    """
    def __init__(self):
        self.db = EtDatabase()

    def handle_message(self, message):
        """
        Entrypoint for emotext, processing data.
        Handles a single message object and processes the text in it.
        """
        # process text via Message object method that uses tokenization, stemming, punctuation removal and so on...
        message.text = " ".join([" ".join([w for w in s]) \
            for s in \
            text_processing(message.text, stemming=False)]) \
            .split()

        message_node = text_to_emotion(message.text, message.language)
        # dump processed data back to the client
        return message_node

class EtDatabase():
    """
    Emotext uses a small, embedded database called unqlite.
    This class handles all communication between database and Emotext.
    """
    def __init__(self, filename='./emotext'):
        """
        Initializes the database using
        """
        self.db = shelve.open(filename)

    def __repr__(self):
        """
        Simply returns a dictionary as representation of the database
        """
        return str([{key: self.db[key]} for key in self.db.keys()])
