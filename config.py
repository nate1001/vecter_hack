
from logging import Logger, StreamHandler, Formatter, INFO

from PyQt4 import QtGui

__NAME__ = 'Rogue'

BASE = '/home/starling/src/rogue'
MEDIA_DIR = BASE + '/media/'
DATA_DIR = BASE + '/data/'

colors = {
    'clear': QtGui.QColor(0,0,0,0),
    'background': QtGui.QColor('black'),
}

logger = Logger(__NAME__)
handler = StreamHandler()
#handler.setFormatter(Formatter('%(levelname)s: %(module)s: %(funcName)s: %(message)s'))
handler.setFormatter(Formatter('%(levelname)s: %(module)s: %(message)s'))
logger.addHandler(handler)
logger.setLevel(INFO)
