from collections import OrderedDict

import autonetkit.log as log

# based on docs.python.org/2.7/library/collections
# and http://stackoverflow.com/q/455059


class ConfigStanza(object):

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], ConfigStanza):
            # Clone the data (shallow copy)
            # TODO: check how this relates to calling dict() on a dict - same?
            in_dict = args[0]._odict
            object.__setattr__(self, '_odict', OrderedDict(in_dict))
            return

        if len(args) == 1 and isinstance(args[0], dict):
            # Clone the data (shallow copy)
            in_dict = args[0]
            object.__setattr__(self, '_odict', OrderedDict(in_dict))
            return

        object.__setattr__(self, '_odict', OrderedDict(kwargs))

    def __repr__(self):
        return str(self._odict.items())

    def to_json(self):
        retval = OrderedDict(self._odict)  # clone to append to
        retval['_ConfigStanza'] = True
        return retval

    def add_stanza(self, name, **kwargs):
        """Adds a sub-stanza to this stanza"""
        stanza = ConfigStanza(**kwargs)
        self[name] = stanza
        return stanza

    def __getitem__(self, key):
        return self._odict[key]

    def __delitem__(self, key):
        del self._odict[key]

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            log.warning(
                "Adding dictionary %s: did you mean ",
                "to add a ConfigStanza?" % key)
        self._odict[key] = value

    def __setattr__(self, key, value):
        self._odict[key] = value

    def __getattr__(self, key):
        # TODO: decide how to return misses
        try:
            return self._odict[key]
        except KeyError:
            # TODO: implement warning here
            # TODO: log a key miss, and if strict turned on, give warning
            return

    def items(self):
        # TODO map this to proper dict inherit to
        # support these methods, keys, etc
        return self._odict.items()

    def __iter__(self):
        return iter(self._odict.items())

    def __len__(self):
        return len(self._odict)

    # TODO: add __iter__, __keys etc

    #self.__dict__['_odict'][key] = value

    # TODO: add a sort function that sorts the OrderedDict
