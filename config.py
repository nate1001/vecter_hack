
from collections import OrderedDict
from logging import Logger, StreamHandler, Formatter, INFO, DEBUG


__NAME__ = 'Rogue'

logger = Logger(__NAME__)
handler = StreamHandler()
#handler.setFormatter(Formatter('%(levelname)s: %(module)s: %(funcName)s: %(message)s'))
handler.setFormatter(Formatter('%(levelname)s: %(module)s: %(message)s'))
logger.addHandler(handler)
logger.setLevel(INFO)
logger.setLevel(DEBUG)


BASE  = '/home/starling/src/rogue'
config = {}
config['media_dir'] = BASE + '/share/media/'
config['data_dir'] = BASE + '/share/data/'
config['background'] = 'black'
config['tile_size'] = 32

defaults = {}
defaults['view/use_svg'] = (True, bool, 'use vector graphics')
defaults['view/use_iso'] = (True, bool, 'use isometric graphics')
defaults['view/use_char'] = (True, bool, 'use character tiles')
defaults['view/seethrough'] = (True, bool, 'use seethrough walls')
defaults['view/debug'] = (False, bool, 'debug mode')
defaults['view/scale'] = (1, float, 'scale')

defaults['model/wizard'] = (False, bool, 'Wizard Mode')

