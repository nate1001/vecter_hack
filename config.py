
from logging import Logger, StreamHandler, Formatter, INFO


__NAME__ = 'Rogue'

BASE = '/home/starling/src/rogue'
MEDIA_DIR = BASE + '/media/'
DATA_DIR = BASE + '/data/'

colors = {
    'background': 'black',
}

svg_tile_width = 128

logger = Logger(__NAME__)
handler = StreamHandler()
#handler.setFormatter(Formatter('%(levelname)s: %(module)s: %(funcName)s: %(message)s'))
handler.setFormatter(Formatter('%(levelname)s: %(module)s: %(message)s'))
logger.addHandler(handler)
logger.setLevel(INFO)
