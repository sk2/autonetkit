def dot_to_underscore(instring):
    """Replace dots with underscores"""
    return instring.replace(".", "_")

def natural_sort(sequence, key=lambda s:s):
    """
    Sort the sequence into natural alphanumeric order.
    """
    import re
    sequence = list(sequence)
    def get_alphanum_key_func(key):
        convert = lambda text: int(text) if text.isdigit() else text
        return lambda s: [convert(c) for c in re.split('([0-9]+)', key(s))]
    sort_key = get_alphanum_key_func(key)
    sequence.sort(key=sort_key)
    return sequence

def sort_sessions(sequence):
    """Wrapper around natural_sort for bgp sessions"""
    return natural_sort(sequence, key = lambda x: x.dst.label)
