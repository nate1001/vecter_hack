
import math

from PyQt4 import QtCore, QtGui


class Path(object):

    @classmethod
    def curvy(cls, start, end):

        l = []
        distance = ((end.x() - start.x())**2 + (end.y() - start.y())**2)**.5
        try:
            slope = (float(end.y()) - start.y()) / (end.x() - start.x())
        except ZeroDivisionError:
            slope = 1000000

        steps = int(distance / 10)
        amplitude = 3

        for i in range(steps):

            #find the next point in the line
            f = i / float(steps)
            p = start + f*(end - start)

            #make line curvy with sin and cosine
            sin = math.sin(p.x()) * amplitude
            cosin = math.sin(p.y()) * amplitude
            if abs(slope) == 1:
                cosin = 0

            new = QtCore.QPointF(p.x() + cosin ,p.y() + sin)
            l.append(new)
        return l


class PropAnimation(QtCore.QPropertyAnimation):
    
    base_time = 350

    def __init__(self, widget, name, time_factor=1.0, force=False):

        super(PropAnimation, self).__init__(widget, name)
        self.widget = widget
        self.finished.connect(self.onFinished)
        self.stateChanged.connect(self._onStateChanged)
        self._force = force

        self.__new = None
        self.__old_parent = None
        self.__reparent = None

        self.time = time_factor * self.base_time
        self.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

    def _onStateChanged(self, state):
        
        if state == self.Running:
            self.__started = True
            if self.__reparent:
                #XXX being now be parented above the tile widget
                #    will not come back to tile until were finished
                #    (for z index)
                self.__old_parent = self.widget.parentItem()
                self.widget.setParentItem(self.__reparent)

        elif state == self.Stopped:
            if self.__old_parent:
                self.widget.setParentItem(self.__old_parent)

    def setup(self, new, old=None, reparent=None, path_function=None):
        
        if self.state() == self.Running and not self._force:
            return False

        self.__new = new
        self.__reparent = reparent

        if old is None:
            old = getattr(self.widget, str(self.propertyName()))
            if hasattr(old, '__call__'):
                old = old()

        # make sure we already have original values saved 
        if reparent:
            old = self.widget.mapToItem(reparent, old)
            new = self.widget.mapToItem(reparent, new)


        if path_function:
            points = path_function(old, new)
            self.setKeyValues([])
            for i, p in enumerate(points):
                self.setKeyValueAt(float(i) / len(points), p)

        self.setDuration(self.time)
        self.setStartValue(old)
        self.setEndValue(new)

        return True

    def start(self):
        if self.state() == self.Running and not self._force:
            return False
        super(PropAnimation, self).start()
        return True

    def onFinished(self):

        attr = getattr(self.widget, 'set' + str(self.propertyName()).capitalize())
        attr(self.__new)

        self.__new = None
        self.__old_parent = None
        self.__reparent = None



class ScaleAnimation(PropAnimation):
    
    def __init__(self, widget):
        super(ScaleAnimation, self).__init__(widget, 'scale')

    def scale(self, factor):

        old = getattr(self.widget, str(self.propertyName()))
        if hasattr(old, '__call__'):
            old = old()

        new = old * factor
        self.setup(new)
        self.start()


    def scaleToOne(self):
        self.setup(1)
        self.setEndValue(1)
        self.start()



class ViewScrollAnimation(QtCore.QParallelAnimationGroup):

    def __init__(self, widget):

        super(ViewScrollAnimation, self).__init__()
        self.view = widget
        self.vertical = PropAnimation(widget, 'vpos')
        self.horizontal = PropAnimation(widget, 'hpos')
        self.addAnimation(self.vertical)
        self.addAnimation(self.horizontal)

    def scroll(self, direction):
        
        if direction in ['north', 'south']:
            anim = self.vertical
            bar = anim.widget.verticalScrollBar()
        elif direction in ['west', 'east']:
            anim = self.horizontal
            bar = anim.widget.horizontalScrollBar()
        else:
            raise ValueError(direction)

        if direction in ['north', 'west']:
            new = bar.value() - bar.pageStep()/2
        else:
            new = bar.value() + bar.pageStep()/2

        anim.setup(new)
        anim.start()

    def position(self, pos):
        oldx, oldy = self.view.hpos, self.view.vpos
        self.view.centerOn(pos)
        x, y= self.view.hpos, self.view.vpos
        self.view.setHpos(oldx)
        self.view.setVpos(oldy)
        self.horizontal.setup(x)
        self.vertical.setup(y)
        self.vertical.start()
        self.horizontal.start()



class PosAnimation(PropAnimation):

    def __init__(self, widget, time_factor=1):
        super(PosAnimation, self).__init__(widget, 'pos', time_factor)

    def move(self, point):
        self.setup(point)
        self.start()


class OpacityAnimation(PropAnimation):
    
    def __init__(self, widget):
        super(self.__class__, self).__init__(widget, 'opacity')

    def fadeTo(self, opacity):
        self.setup(opacity)
        return self.start()


class MeleeAnimation(QtCore.QSequentialAnimationGroup):
    
    def __init__(self, being):

        super(MeleeAnimation, self).__init__(being)

        self.being = being
        self.forward =  PosAnimation(being, time_factor=.5)
        self.backward = PosAnimation(being, time_factor=.5)

        self.addAnimation(self.forward)
        self.addAnimation(self.backward)

    def melee(self, tile):

        old = self.being.pos()
        new = (tile.pos() - self.being.parentItem().pos()) / 2
        level = tile.parentItem()

        self.forward.setup(new, reparent=level)
        self.backward.setup(old, reparent=level)
        self.start()



class MovementAnimation(PropAnimation):
    
    def __init__(self, being):

        super(MovementAnimation, self).__init__(being, 'pos')
        self.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        self.__new = None

    def walk(self, tile):
        
        self.__new = tile
        old_tile = self.widget.parentItem()
        new = QtCore.QPointF(*tile.center()) - old_tile.pos()
        level = tile.parentItem()

        if not self.setup(new, reparent=level, path_function=Path.curvy):
            return False
        self.start()
        old_tile.being = None
        return True


    def onFinished(self):
        super(MovementAnimation, self).onFinished()

        self.widget.setParentItem(self.__new)
        self.__new.being = self.widget
        self.widget.setPos(0,0)
        self.__new = None

