
import math
from weakref import WeakValueDictionary

from PyQt4 import QtCore, QtGui


running_animations = []


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
    disable_animation = True


    def __init__(self, widget, name, time_factor=1.0, force=False):

        super(PropAnimation, self).__init__(widget, name)
        self.stateChanged.connect(self._onStateChanged)
        self._force = force

        self.dic = WeakValueDictionary()
        self.dic['widget'] = widget

        self.__new = None

        self.time = time_factor * self.base_time
        self.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

    @property
    def widget(self):
        return self.dic['widget']

    def _onStateChanged(self, state):

        if state == self.Running:
            running_animations.append(self)

            if self.dic.get('__reparent'):
                self.dic['__old_parent'] = self.widget.parentItem()
                self.widget.setParentItem(self.dic['__reparent'])

        elif state == self.Stopped:

            running_animations.remove(self)
            attr = getattr(self.dic['widget'], 'set' + str(self.propertyName()).capitalize())
            attr(self.__new)
            self.__new = None
            if self.dic.get('__reparent'):
                self.widget.setParentItem(self.dic['__old_parent'])
                self.dic.pop('__reparent')
                self.dic.pop('__old_parent')


    def setup(self, new, old=None, reparent=None, path_function=None):
        
        if self.state() == self.Running and not self._force:
            return False

        self.__new = new

        if old is None:
            old = getattr(self.dic['widget'], str(self.propertyName()))
            if hasattr(old, '__call__'):
                old = old()

        if reparent:
            self.dic['__reparent'] = reparent
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

    def scaleTo(self, scale):
        self.setup(scale)
        self.setEndValue(scale)
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
        super(PosAnimation, self).__init__(widget, 'pos', time_factor=time_factor)

    def move(self, point):
        self.setup(point)
        self.start()

class RayAnimation(PosAnimation):

    def _onStateChanged(self, state):
        super(PosAnimation, self)._onStateChanged(state)
        if state == self.Running:
            self.widget.show()
        elif state == self.Stopped:
            self.widget.hide()



class OpacityAnimation(PropAnimation):
    
    def __init__(self, widget, force=False, time_factor=1):
        super(self.__class__, self).__init__(widget, 'opacity', time_factor=time_factor, force=force)

    def fadeTo(self, opacity):
        self.setup(opacity)
        self.start()

class FadeInOutAnimation(QtCore.QSequentialAnimationGroup):


    def __init__(self, widget):

        super(FadeInOutAnimation, self).__init__(widget)

        fade_in =  OpacityAnimation(widget, time_factor=.5)
        fade_out = OpacityAnimation(widget, time_factor=.5)

        self.addAnimation(fade_in)
        self.addAnimation(fade_out)

    def fade(self):
        a = self.animationAt(0)
        a.setup(1)
        a = self.animationAt(1)
        a.setup(0)
        self.start()


class MeleeAnimation(QtCore.QSequentialAnimationGroup):

    def __init__(self, being):

        super(MeleeAnimation, self).__init__(being)

        forward =  PosAnimation(being, time_factor=.5)
        backward = PosAnimation(being, time_factor=.5)
        self.being = being

        self.addAnimation(forward)
        self.addAnimation(backward)

    def del_(self):
        self.takeAnimation(1)
        self.takeAnimation(0)
    
    def melee(self, tile):
        
        #if self.forward.disable_animation:
        #    return

        being = self.being
        old = being.pos()
        new = (tile.pos() - being.parentItem().pos()) / 2
        level = tile.parentItem()

        a = self.animationAt(0)
        a.setup(new, reparent=level)
        a = self.animationAt(1)
        a.setup(old, reparent=level)


class MovementAnimation(PropAnimation):
    
    def __init__(self, being):

        super(MovementAnimation, self).__init__(being, 'pos')
        #self.stateChanged.connect(self._onStateChanged2)
        self.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        self.__newtile = None
        self.__level = None

    def walk(self, old_tile, new_tile, level):

        self.__newtile = new_tile
        self.__level = level

        old = old_tile.pos()
        new = new_tile.pos()

        if not self.setup(new, old=old, path_function=Path.curvy):
            raise ValueError

        old_tile.being = None

    def _onStateChanged(self, state):
        
        super(MovementAnimation, self)._onStateChanged(state)
        if state == self.Running:

            #XXX being now be parented above the tile widget
            #    will not come back to tile until were finished
            #    (for z index)
            self.widget.setParentItem(self.__level)

        elif state == self.Stopped:

            self.widget.setParentItem(self.__newtile)
            self.__newtile.being = self.widget
            self.widget.setPos(0,0)
            self.__newtile = None
            self.__level = None


class BeingAnimation(QtCore.QSequentialAnimationGroup):
    
    def __init__(self, being):
        super(BeingAnimation, self).__init__()
        #self.currentAnimationChanged.connect(self._onChanged)
        self.being = being
        self.finished.connect(self._onFinished)

    def walk(self, old_tile, new_tile, level):
        anima = MovementAnimation(self.being)
        anima.walk(old_tile, new_tile, level)
        self._start(anima)

    def die(self):
        anima = PropAnimation(self.being, 'opacity')
        anima.setup(0)
        anima.finished.connect(self._onFinishedDying)
        self._start(anima)

    def teleport_away(self):
        self.die()

    def _onFinishedDying(self):
        self.being.scene().removeItem(self.being)

    def melee(self, tile):
        anima = MeleeAnimation(self.being)
        anima.melee(tile)
        self._start(anima)

    def _start(self, anima):
        
        self.addAnimation(anima)
        # give the animation less time
        # as more animations back up
        if hasattr(anima, 'setDuration'):
            da = anima.duration()
            dt = self.duration()
            t = self.currentTime()
            if dt-da:
                done = t / float(dt-da) 
            else:
                done = 1
            anima.setDuration(done * anima.duration())
        self.start()

    def _onFinished(self):
        self.clear()

            


