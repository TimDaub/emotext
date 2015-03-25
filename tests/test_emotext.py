import sys
import os.path
import re
from apis.text import text_processing
from apis.text import calc_percentages
from models.models import Emotext

texts = [
    "Hello. This isn't doge! The movie wasn't heavy."
]

def test_text_processing():
    """
    Tests:
        * if strings get separated accordingly
        * words contain punctuation chars
        * if there are sentences that have no words.
        * the number of sentences
    """
    sentences = text_processing(texts[0], stemming=False, remove_punctuation=True)
    assert len(sentences) == 3
    for sentence in sentences:
        assert type(sentence) == type([])
        assert len(sentence) > 0
        for w in sentence:
            # check for punctuation characters in word sequence
            assert re.match(r'[^\w]', w) == None

def test_calc_percentages():
    emotions = {
        "love": 27.298217235189718,
        "cry": 17.167578907271867,
        "sadness": 8.795877176280856,
        "boredom": 13.366757881808853,
        "frustration": 7.048259470954596,
        "happiness": 12.981467725924063
    }
    calc_percentages(emotions)

def test_emotext():
    et = Emotext()

def test_post_to_entities():
    """ 
    Reads all messages of a whatsapp file and posts them as one
    entity to the server in order to assert them
    """
    
    # read messages from a .txt file by using the whatsapp provider
    messages = get_messages('Tim', r'./providers/static/whatsapp_chat.txt', 'english')
    for message in messages:
        r = requests.post(base_url + '/entities/' + message.entity_name, \
            data=json.dumps(message.__dict__), \
            headers=headers)
        res_dict = json.loads(r.text)
        assert r.status_code <= 200
        # assert res_dict['entity_name'] == message.entity_name
        # assert type(res_dict['message']) == type([])
        # assert len(res_dict['message']) > 0
        # assert res_dict['date'] == message.date
        print res_dict