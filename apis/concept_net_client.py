"""
`rest_client.py`_ is a simple client for interacting with ConceptNet 5's REST
API.

.. _`rest_client.py`: https://github.com/commonsense/conceptnet/blob/master/conceptnet/webapi/rest_client.py

This client is not object-oriented. The data structures you work with are
dictionaries, of the form described in the API documentation. The main function
:func:`lookup` can be used to look up many different kinds of data. There are
also convenience functions for performing common operations on this data.

If you want to know what fields are contained in these dictionaries, read
the REST API documentation at
http://csc.media.mit.edu/docs/conceptnet/webapi.html#rest-requests .

This wrapper has been portet to ConceptNet5 by Tim Daubenschuetz
"""
import sys
import os.path

import urllib, urllib2
from requests_futures.sessions import FuturesSession
from ..utils.utils import get_config

try:
    import json
except:
    import simplejson as json

CLIENT_VERSION = '1'

# Emotext specific parameters, used to enable the library to be run locally
SERVER_URL = get_config('conceptnet5_parameters', 'SERVER_URL')
API_URL = get_config('conceptnet5_parameters', 'API_URL')
CONCEPT_NET_VERSION = get_config('conceptnet5_parameters', 'VERSION')
REQ_LIMIT = get_config('conceptnet5_parameters', 'REQ_LIMIT')

TYPES = {
    'assertion': 'a',
    'concept': 'c',
    'datasets': 'd',
    'edge': 'e',
    'license': 'l',
    'language_indenpendent_relation': 'r',
    'knowledge_sources': 's',
    'and': 'and',
    'or': 'or'
}

def lookup(type, language, key):
    """
    Get an object of a certain *type*, specified by the code for what
    *language* it is in and its *key*. The types currently supported are:

        `assertion`
            assertions
        `concept`
            concepts (words, disambiguated words, and phrases, in a particular language)
        'datasets'
            datasets (large sources of knowledge that can be downloaded as a unit)
        'edge'
            unique, arbitrary IDs for edges. Edges that assert the same thing combine to form assertions.
        'license'
            license terms for redistributing the information in an edge. The two licenses in ConceptNet are /l/CC/By for Creative Commons Attribution, and /l/CC/By-SA for the more restrictive Attribution-ShareAlike license. See Copying and sharing ConceptNet.
        'language_indenpendent_relation'
            language-independent relations, such as /r/IsA
        'knowledge_sources'
            knowledge sources, which can be human contributors, Web sites, or automated processes
        'and'
            conjunctions and disjunctions of sources
        'or'
            conjunctions and disjunctions of sources
    
    The object will be returned as a dictionary, or in the case of features,
    a list.
    """
    if type == None: 
        raise Exception('Type must be specified to request the web api.')
    if len(type) > 1: 
        type = from_name_to_type(type)
    return _get_json(type, language, key.lower())

def from_name_to_type(type='concept'):
    try:
        return TYPES[type]
    except:
        print 'The Type ' + type + 'could not have been found.'
        return None

def lookup_concept_raw(language, concept_name):
    """
    Look up a Concept by its language and its raw name. For example,
    `lookup_concept_raw('en', 'webbed feet')` will get no results, but
    `lookup_concept_raw('en', 'web foot')` will.

    Use :func:`lookup_concept_from_surface` to look up a concept from an
    existing surface text, such as "webbed feet".

    Use :func:`lookup_concept_from_nl` to look up a concept from any natural
    language text. This requires the `simplenlp` module.
    """
    return lookup('concept', language, concept_name)

def lookup_concept_from_surface(language, surface_text):
    """
    Look up a concept, given a surface form of that concept that someone has
    entered into Open Mind. For example,
    `lookup_concept_from_surface('en', 'webbed feet')` will return the concept
    'web foot'.
    """
    surface = lookup('surface', language, surface_text)
    return surface['concept']

def lookup_concept_from_nl(language, text):
    """
    Look up a concept using any natural language text that represents it.
    This function requires the :mod:`simplenlp` module
    to normalize natural language text into a raw concept name.
    """
    import simplenlp
    nltools = simplenlp.get('en')

    normalized = nltools.normalize(text)
    return lookup_concept_raw(language, normalized)

def assertions_for_concept(concept, direction='all', limit=20):
    """
    Given a dictionary representing a concept, look up the assertions it
    appears in.

    By default, this returns all matching assertions. By setting the
    optional argument `direction` to "forward" or "backward", you can restrict
    it to only assertions that have that concept on the left or the right
    respectively.

    You may set the limit on the number of results up to 100. The default is
    20. This limit is applied before results are filtered for forward or
    backward assertions.
    """
    def assertion_filter(assertion):
        if direction == 'all': return True
        elif direction == 'forward':
            return assertion['concept1']['text'] == concept['text']
        elif direction == 'backward':
            return assertion['concept2']['text'] == concept['text']
        else:
            raise ValueError("Direction must be 'all', 'forward', or 'backward'")
        
    assertions = _refine_json(concept, 'assertions', 'limit:%d' % limit)
    return [a for a in assertions if assertion_filter(a)]

def surface_forms_for_concept(concept, limit=20):
    """
    Given a dictionary representing a concept, get a list of its surface
    forms (also represented as dictionaries).

    You may set the limit on the number of results up to 100. The default is
    20.
    """
    return _refine_json(concept, 'surfaceforms', 'limit:%d' % limit)

def votes_for(obj):
    """
    Given a dictionary representing any object that can be voted on -- such as
    an assertion or raw_assertion -- get a list of its votes.
    """
    return _refine_json(obj, 'votes')

def similar_to_concepts(concepts, limit=20):
    """
    `concepts` is a list of concept names or (concept name, weight) pairs.
    Given this, `similar_to_concepts` will find the `limit` most related
    concepts.

    These similar concepts are returned in dictionaries of the form:

        {'concept': concept, 'score': score}

    where `concept` is the data structure for a concept.
    """
    pieces = []
    for entry in concepts:
        if isinstance(entry, tuple):
            concept, weight = entry
        else:
            concept = entry
            weight = 1.
        if hasattr(concept, 'text'):
            concept = concept.text
        concept = concept.replace(' ', '_').encode('utf-8')
        pieces.append("%s@%s" % (concept, weight))
    termlist = ','.join(pieces)
    limitstr = 'limit:%d' % limit
    return _get_json('en', 'similar_to', termlist, limitstr)

def add_statement(language, frame_id, text1, text2, username, password):
    """
    Add a statement to Open Mind, or vote for it if it is there.

    Requires the following parameters:
        
        language
            The language code, such as 'en'.
        frame_id
            The numeric ID of the sentence frame to use.
        text1
            The text filling the first blank of the frame.
        text2
            The text filling the second blank of the frame.
        username
            Your Open Mind username.
        password
            Your Open Mind password.
    
    Example: 
    >>> frame = lookup('frame', 'en', 7)
    >>> frame['text']
    '{1} is for {2}'
    
    >>> add_statement('en', 7, 'election day', 'voting', 'rspeer', PASSWORD)
    (Result: rspeer adds the statement "election day is for voting", which
    is also returned as a raw_assertion.)
    """
    return _post_json([language, 'frame', frame_id, 'statements'], {
        'username': username,
        'password': password,
        'text1': text1,
        'text2': text2
    })


def _get_json(*url_parts):
    """
    This method has been updated and now uses ConceptNet5 syntax to access the web-API
    """
    session = FuturesSession()
    url = API_URL + '/' + CONCEPT_NET_VERSION + '/' + '/'.join(urllib2.quote(p.encode('utf-8')) for p in url_parts) + '?limit=' + REQ_LIMIT
    # print 'Looking up: ' + url
    #return session.get(url)
    return json.loads(_get_url(url))

def _extend_url(old_url, *url_parts):
    url = old_url + '/'.join(urllib2.quote(str(p)) for p in url_parts) + '/'
    return json.loads(_get_url(url))

def _get_url(url):
    conn = urllib2.urlopen(url)
    return conn.read()

def _refine_json(old_obj, *parts):
    return _extend_url(SERVER_URL + old_obj['resource_uri'], *parts)
