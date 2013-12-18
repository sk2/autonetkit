# YAML helpers from http://stackoverflow.com/questions/8640959

import yaml
from collections import OrderedDict

class quoted(str): pass

def quoted_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

class literal(str): pass

def literal_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')

def ordered_dict_presenter(dumper, data):
    return dumper.represent_dict(data.items())

def add_representers():
    yaml.add_representer(quoted, quoted_presenter)
    yaml.add_representer(literal, literal_presenter)
    yaml.add_representer(OrderedDict, ordered_dict_presenter)