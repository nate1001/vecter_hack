
import sys

from PyQt4 import QtCore, QtGui

from view.game import MainWindow
from view.util import Settings
from model.dungeon import Game
from config import defaults, __NAME__


app = QtGui.QApplication(sys.argv)
s = Settings(__NAME__.lower(), defaults)
main = MainWindow(Game(), s)
main.setGeometry(300, 0, 1000, 600)
main.show()
sys.exit(app.exec_())
