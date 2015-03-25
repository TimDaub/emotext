"""
This module uses a ConceptNet5 REST-API Wrapper to connect to the network.

Given an arbitrary text (that has been stemmed and normalized),
it analyzes every token in order to create a vector that represents
the texts emotions.

This is done by algorithms searching the graph structure of concept net for
connections between a specific token and the entity 'Emotion'.
"""
import sys
import os.path
import re

from ..models.models import Node
from sets import Set
from math import pow

from ..utils.utils import get_config

from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters
from nltk.tokenize import RegexpTokenizer
from nltk.stem.snowball import SnowballStemmer
from nltk.corpus import stopwords

LANG_TO_CODE = {
    'english': 'en',
    'german': 'de',
    'french': 'fr'
}

MAX_DEPTH = get_config('emotext_graph_search', 'MAX_DEPTH', 'getint')
MIN_WEIGHT = get_config('emotext_graph_search', 'MIN_WEIGHT', 'getint')

EMOTIONS = set(["love", "anger", "fear", "hate", "happiness", "pleasant", "sadness", "pity", "shame", "ecstasy", "boredom", "love", "cry", "happy", "jealousy", "joy", "surprise", "regret", "frustration", "sorrow", "melancholy", "awe", "fear", "anger", "joy"])

def lang_name_to_code(lang_name='english'):
    """
    ConceptNet uses language codes to query words.
    Since we don't want to use those, we've integrated this method
    that allows conversion from language names to language codes.

    If a language code is missing, an exception will be thrown and the users
    will be notified.

    They can furthermore easily adjust the LANG_TO_CODE constant, to add his own language.
    """
    try:
        return LANG_TO_CODE[lang_name]
    except:
        print 'Unfortunately, no lang_code is present for this language.'
        print 'This may be adjusted in apis/emotext.py: LANG_TO_CODE'
        return None

def text_processing(text, remove_punctuation=True, stemming=True, remove_stopwords=True, language='english', replace_with_antonyms='True'):
    """
    This function enables general text processing.
    It features:
        * Tokenization on sentence level
        * Tokenization on word level
        * Punctuation removal
        * Stemming (and stopword removal)
        * Conversion to lower case
    The language parameter is only required, if stemming and removal of stopwords are desired.
    """

    # Texts often contain punctuation characters.
    # While we'd like to remove them from our data set, their information shouldn't be lost, as
    # it would enable us to handle negation in text later on.
    # 
    # An example:
    # Given the sentence: 'The movie was not bad.', we could convert all
    # adjectives in the sentence to antonyms and remove all negations.
    # Afterwards, the sentence would read 'The movie was good', where 'good'
    # is the antonym of 'bad'.
    # 
    # Therefore, punctuation information should not be lost throughout the process of
    # processing the text with NLP.
    sentence_tokenizer = PunktSentenceTokenizer(PunktParameters())
    # tokenize always returns a list of strings divided by punctuation characters
    # 
    # 'hello' => [u'hello']
    # 'hello. world.' => [u'hello.', u'world.']
    # 
    # Therefore, we need to continue handling a list, namely the sentences variable
    sentences = sentence_tokenizer.tokenize(text)

    # In the English language at least, 
    # there are certain stop words, that introduce low-level negation
    # on a sentence bases.
    # However, these stop words are often melted with their previous verb
    # 
    # isn't = is not
    # wouldn't = would not
    # 
    # This must resolved, as it would not be possible for further functionality of this function to continue
    # extracting information.
    # Especially the 'anonymity' functionality wouldn't work without this
    if language == 'english':
        sw_pattern = r"(n't)"
        sentences = [re.sub(sw_pattern, ' not', s) for s in sentences]
    
    # If desired, the user can no go ahead and remove punctuation from all sentences
    if remove_punctuation:
        # This tokenizer simply removes every character or word which
        # length is < 2 and is not a alphabetic one
        punct_rm_tokenizer = RegexpTokenizer(r'\w{2,}')
        # In this case, tokenize will return a list of every word in the sentence
        # 
        # [u'hello'] => [[u'hello']]
        # [u'hello', u'this is another sentence'] => [[u'hello'], [u'this', u'is', u'another', u'sentence']]
        # 
        # Therefore, in the next step we need to handle a list of lists
        sentences = [punct_rm_tokenizer.tokenize(s) for s in sentences]

    if remove_stopwords:
        try:
            sentences = [[w for w in sentence if not w in stopwords.words(language)] \
                                for sentence in sentences]
        except:
            print 'There are no stopwords available in this language = ' + language

    # Next, we want to stem on a words basis
    # What this does for example is convert every word into lowercase, remove morphological
    # meanings, and so on.
    if stemming:
        # If desired, stopwords such as 'i', 'me', 'my', 'myself', 'we' can be removed
        # from the text.
        stemmer = SnowballStemmer(language)
        sentences = [[stemmer.stem(w) for w in sentence] for sentence in sentences]
    else:
        # If stemming is not desired, all words are at least converted into lower case
        sentences = [[w.lower() for w in sentence] for sentence in sentences]

    return sentences

def text_to_emotion(token_list, language='english'):
    """
    This method takes a list of tokes and analyzes every one of those
    by using ConceptNet and a specially implemented graph path search algorithm

    It then returns a vector specifying emotional features of the text.
    """
    lang_code = lang_name_to_code(language)
    if len(token_list) < 1: 
        raise Exception('The token_list must contain at least one word.')
    return [build_graph(Set([Node(t, lang_code, 'c')]), Set([]), {
        'name': t,
        'emotions': {}
        }, 0) for t in token_list]

def build_graph(token_queue, used_names, emo_vector, depth):
    """
    Emotional features are extracted using ConceptNet5.

    We use the provided RESTful interface for lookups.
    This function is basically a breadth-first graph search.
    Eventually, it returns a emotion-expressing vector for
    every token it gets passed.
    """

    # Overview:
    # 
    # Essentially, ConceptNet5 lets us lookup nearly every concept known to man-kind.
    # A lookup is done using a GET request using the concepts name.
    # As an example, looking up rollercoaster would be as easy as requesting the following link:
    # 
    # http://conceptnet5.media.mit.edu/data/5.3/c/en/rollercoaster
    # 
    # Every concept has only two properties:
    # - numFound: an integer expressing the number of related edges found; and
    # - edges: concepts that are somehow connected to the original concept.
    # 
    # Since this is basically a undirected graph structure, we can traverse it easily by
    # continuously looking up the edges of a concept.
    # 
    # Algorithm:
    # 
    # build_graph takes a:
    # 
    # - token_queue: set of tokens (normal words) (default: ["a", "list", "of", "words"])
    # - used_names: a list of names that have been previously looked up
    # - emo_vector: a key-value object with emotions as keys and absolute or percentual metrics as values
    # - depth: an integer representing the graph search's depth
    #
    #
    #
    # Cancellation condition:
    # 
    # if MAX_DEPTH is reached, percentages (calc_percentages) are calculated from the absolute values
    # returned by calc_nodes_weight.
    # Subsequently, the function returns, hence execution is done.
    if depth >= MAX_DEPTH:
        emo_vector['emotions'] = calc_percentages(emo_vector['emotions'])
        return emo_vector

    # Graph search part:
    # 
    # Since we're actively working on token_queue inside of a for-loop (adding and removing elements)
    # making a copy that is not enumerated on is necessary.
    # Here, we make use of a Set as one of its qualities is that it allows no duplicates.
    # We don't want to lookup the same word twice. Lookups are just too time and CPU consuming.
    token_queue_copy = Set(token_queue)

    # We traverse through every token in the set
    # if the token's name does not resemble to one of the searched-for
    # emotion's name, then we proceed diving further down the graph until MAX_DEPTH is reached.
    for token in token_queue:
        
        # if the token's name resembles 
        if token.name in EMOTIONS:
            try:
                emo_vector['emotions'][token.name] = emo_vector['emotions'][token.name] + calc_nodes_weight(token, token.name, [], 0)
            except:
                emo_vector['emotions'][token.name] = calc_nodes_weight(token, token.name, [], 0)
        else:
            token_queue_copy.remove(token)
            try:
                token.edge_lookup(used_names, 'en')
            except Exception as e:
                print e
                continue
            for new_edge in token.edges:
                if new_edge.name not in used_names and new_edge.weight > MIN_WEIGHT:
                    used_names.add(new_edge.name)
                    token_queue_copy.add(new_edge)
    return build_graph(token_queue_copy, used_names, emo_vector, depth+1)

def calc_percentages(emotions):
    sum_values = sum(emotions.values())
    return {k: v/sum_values for k, v in emotions.items() if v != 0}

def calc_nodes_weight(node, emotion, weights, weight_num):
    print node.name + ': %d' % node.weight
    if node.parent == None:
        for i, n in enumerate(weights):
            weight_num = weight_num + n * 1/(i+1)
        print '###########################'
        return weight_num
    else:
        weights.append(node.weight)
        return calc_nodes_weight(node.parent, emotion, weights, weight_num)