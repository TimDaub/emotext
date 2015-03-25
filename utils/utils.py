import ConfigParser
import os

def extr_from_concept_net_edge(s):
    """
    ConceptNet returnes on lookup edges that are named in this fashion:

        'c/en/autobahn'

    From this we can extract:
        - type
        - language-code
        - name of the node
    """
    params_list = s.split('/')
    if len(params_list) < 3: 
        raise Exception('The given string did not contain at least two slashes.')
    return {
        'type': params_list[1],
        'lang_code': params_list[2],
        'name': params_list[3]
    }

def get_config(section, key, method_name='get'):
    """
    Reads the 'config.cfg' file in the root directory and allows
    to select specific values from it that will - if found - be returned.
    """
    config_parser = ConfigParser.ConfigParser()
    config_parser.readfp(open(os.path.dirname(os.path.abspath(__file__)) + r'/../config.cfg'))
    try:
        return getattr(config_parser, method_name)(section, key)
    except:
        print 'Combination of section and key has not been found in config.cfg file.'
        return None