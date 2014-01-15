
import sys
from getopt import getopt

from PyQt4 import QtCore, QtGui

from view.game import MainWindow
from view.util import Settings
from model.attr_reader import AttrReaderError
from model.game import Game
from controller.controller import Controller
from config import defaults, map_defaults, __NAME__

def parse_cmdline():
    
    d = {
        'quit after startup': False,
    }
    
    options, args = getopt(sys.argv[1:], 'q')
    for option, value in options:
        if option == '-q':
            d['quit after startup'] = True
    return d

options = parse_cmdline()
settings = Settings(__NAME__.lower(), defaults)
map_settings = Settings(__NAME__.lower() + '_map', map_defaults)
game = Game(Controller(), settings)
view = game.view()

app = QtGui.QApplication(sys.argv)
main = MainWindow(__NAME__, view, settings, map_settings, options)
main.setGeometry(300, 0, 1000, 600)
main.show()
app.exec_()


