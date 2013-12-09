
from collections import OrderedDict
from logging import Logger, StreamHandler, Formatter, INFO


__NAME__ = 'Rogue'

logger = Logger(__NAME__)
handler = StreamHandler()
#handler.setFormatter(Formatter('%(levelname)s: %(module)s: %(funcName)s: %(message)s'))
handler.setFormatter(Formatter('%(levelname)s: %(module)s: %(message)s'))
logger.addHandler(handler)
logger.setLevel(INFO)


BASE  = '/home/starling/src/rogue'
config = {}
config['media_dir'] = BASE + '/share/media/'
config['data_dir'] = BASE + '/share/data/'
config['svg_tile_width'] = 128
config['background'] = 'black'
config['tile_size'] = 32

defaults = {}
defaults['view/use_svg'] = (True, bool, 'use vector graphics')
defaults['view/use_iso'] = (True, bool, 'use isometric graphics')
defaults['view/seethrough'] = (True, bool, 'use seethrough walls')
defaults['view/debug'] = (False, bool, 'debug mode')

defaults['game/wizard'] = (False, bool, 'Wizard Mode')

