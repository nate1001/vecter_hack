
import sys
from getopt import getopt

from PyQt4 import QtCore, QtGui

from view.game import MainWindow
from view.util import Settings
from model.game import Game
from config import defaults, __NAME__


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
game = Game(settings, )
view = game.view()

app = QtGui.QApplication(sys.argv)
main = MainWindow(__NAME__, view, settings, options)
main.setGeometry(300, 0, 1000, 600)
main.show()
app.exec_()


