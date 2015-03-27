import shelve
from ..apis.text import text_processing
from ..utils.utils import get_config
from emotext.models.models import Message
from emotext.models.models import Conversation
from datetime import datetime
from datetime import timedelta

TOLERANCE_TIME = get_config('clustering', 'TOLERANCE_TIME', 'getint')

class Emotext():
    """
    Represents the utility class for using Emotext.
    Provides all methods to use Emotext.
    """
    def __init__(self):
        self.mc = MessageCluster()

    def handle_message(self, message):
        """
        Entry point for emotext, processing data.
        Handles a single message object and processes the text in it.
        """
        # process text via Message object method that uses tokenization, stemming, punctuation removal and so on...
        message.text = " ".join([" ".join([w for w in s]) \
            for s in \
            text_processing(message.text, stemming=False)]) \
            .split()

        # We collect all messages in a MessageCluster.
        # Once a conversation is over, we process them using the text_to_emotion function.
        self.mc.add_message(message)
        # message_node = text_to_emotion(message.text, message.language)
        # dump processed data back to the client
        # return message_node

class CacheController():
    """
    Extracting emotions from text through conceptnet5 can be a very time consuming task,
    especially when processing large quantities of text.

    The CacheController class therefore can be used to save word-based results persistently.
    """

    # This class should simply act as a key-value storage cache that can be asked before a word is being processed.
    # If the word is not included in its cache, the word must be processed by traversing conceptnet5's
    # graph structure, else we can just use the already given result.
    # 
    # Since different parameters (which can be found in config.cfg) alter the results immensely,
    # CacheController must be initialized with all those parameters.
    # Also, it is very likely that parameters will increase in later versions, hence naming function parameters
    # might be a good idea for everyone reusing this class.
    
    def __init__(self, max_depth, min_weight, req_limit):
        self.max_depth = max_depth
        self.min_weight = min_weight
        self.req_limit = req_limit

        # for every form those parameters can take, a new .db file is created on the hard drive.
        self.cache = shelve.open('./word_cache_%d_%d_%d' % (self.max_depth, self.min_weight, self.req_limit))

    def add_word(self, word, emotions):
        """
        Adds an emotion dictionary. 

        This method will overwrite everything.
        """
        self.cache[word] = emotions

    def fetch_word(self, word):
        """
        Fetches a word and returns None if a KeyValue exception is thrown.
        """
        try:
            return self.cache[word]
        except:
            # in case a word is not found in the cache
            return None

    def __repr__(self):
        """
        Simply returns a dictionary as representation of the object
        """
        return str(self.__dict__)

class MessageCluster():
    """
    Handles the clustering of messages. Keeps track of the clustering tolerance and handles
    its own runtime-embedded key-value store for it.
    """

    # In instant messenger conversations multiple messages for 2 or more participants 
    # form a conversation.
    # Additionally, conversations can grow quickly and remain 'active' for multiple hours or days.
    # 
    # Since Emotext wants to provide functionality that allows for smoothing methods to be applied to words,
    # sentences and *even* conversations, we need not only to save them for a small period of time but as long as 
    # the conversation stays 'active'.
    # 
    # For simplicity matters, we do not introduce or use a designated 'clustering' algorithm.
    # Instead, we start increasing a tolerance counter once the first message of a new conversation is 
    # added to the cluster.
    # Every time a new message is added to the cluster, the tolerance counter is reset.
    # Does the conversation fail to add a new message before the tolerance counter achieves its
    # max time. The cluster is sealed and the conversation is essentially over.
    # 
    # A tolerance time in seconds can be defined in config.cfg and probably needs to be readjusted depending 
    # its use case.

    def __init__(self, tolerance_time=None):
        """
        Initializing the MessageCluster simply instantiates a shelve database.
        """
        self.db = shelve.open('./message_clustering')

        # mainly for testing purposes, self.tolerance_time can be overrode.
        # Its unit is seconds.
        if tolerance_time is not None:
            self.tolerance_time = tolerance_time
        else:
            self.tolerance_time = TOLERANCE_TIME

    def get_messages(self):
        """
        Yields a list of messages from the database or in case of a k-y exception, 
        an empty list.
        """
        try:
            return self.db['messages']
        except:
            return list()

    def start_tolerance(self):
        """
        Saves a datetime to the shelve database to track the counter's start time.
        """
        self.db['future_time'] = datetime.now() + timedelta(seconds=self.tolerance_time)

    def is_conversation_over(self):
        """
        Yields whether or not the latest conversation is over.
        """
        try:
            tolerance_time = self.db['future_time']
            if tolerance_time < datetime.now():
                return True
            else:
                return False
        except:
            # When initializing our application from scratch,
            # tolerance_time will naturally be not defined and self.db['tolerance_time']
            # will produce a KeyValue Exception which we catch here and return True
            return True

    def add_message(self, message):
        """
        Handles the addition of a new message. All messages must be of instance emotext.models.models.Message.
        """

        # In case a new MessageCluster is created,
        # then the old one is converted to a conversation object.
        # Subsequently this Conversation is being processed in a subprocess 
        # to analyze its emotions.

        if isinstance(message, Message):
            if self.is_conversation_over():
                # old conversation is long over, therefore we delete everything
                # thats left from it and start a new one.
                # But before that, we need to make sure that process our old conversation (if it exists)
                if len(self.get_messages()) > 0:
                    conversation = self.to_conversation_obj()
                # afterwards, we can move on reseting the database
                self.reset_db()
                self.db['messages'] = [message]
            else:
                messages = self.get_messages()
                messages.append(message)
                self.db['messages'] = messages
            # In both cases, renew tolerance time
            self.start_tolerance()
        else:
            raise Exception('Only messages of type emotext.models.models.Message can be added.')

    def reset_db(self):
        """
        Deletes all keys from the database.
        """
        for key in self.db.keys():
            del self.db[key]

    def to_conversation_obj(self):
        """
        Converts a MessageCluster object to a Conversation.
        """
        return Conversation(self.get_messages())

    def __repr__(self):
        """
        Simply returns a dictionary as representation of the database.
        """
        return str([{key: self.db[key]} for key in self.db.keys()])