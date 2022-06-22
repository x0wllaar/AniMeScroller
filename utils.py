import sys
from collections import namedtuple

PICKLE_PROTOCOL_VERSION = 5

GifData = namedtuple("GifData", ["nloops", "gif_bytes"])

def die(*args, **kwargs):
    print("ERROR:", *args, file=sys.stderr, **kwargs)
    exit(1)