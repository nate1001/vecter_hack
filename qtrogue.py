
import sys

from PyQt4 import QtCore, QtGui

from view.game import MainWindow
from view.util import Settings
from model.dungeon import Dungeon
from config import defaults, __NAME__


settings = Settings(__NAME__.lower(), defaults)
game = Dungeon(settings).view()

app = QtGui.QApplication(sys.argv)
main = MainWindow(game, settings)
main.setGeometry(300, 0, 1000, 600)
main.show()
sys.exit(app.exec_())
