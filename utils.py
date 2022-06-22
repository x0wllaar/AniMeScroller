from collections import namedtuple

PICKLE_PROTOCOL_VERSION = 5

GifData = namedtuple("GifData", ["nloops", "gif_bytes"])
