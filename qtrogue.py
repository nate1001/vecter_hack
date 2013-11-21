
from PyQt4 import QtCore, QtGui

from view.game import MainWindow

if __name__ == '__main__':

    import sys
    #sys.path.append('../')
    #sys.path.append('.')

    from model.dungeon import Game

    app = QtGui.QApplication(sys.argv)
    main = MainWindow(Game())
    main.setGeometry(300, 0, 1000, 600)
    main.show()
    sys.exit(app.exec_())
