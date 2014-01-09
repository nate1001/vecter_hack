import string 

from PyQt4 import QtCore, QtGui

from animation import OpacityAnimation
from util import TextWidget, TitledTextWidget


class LogWidget(TextWidget):

    class Message(object):
        def __init__(self, level, is_player, msg):

            self.level = level
            self.is_player = is_player
            self.msg = msg

            if level < 2:
                self.color = '#aaa'
            elif level < 6:
                self.color = 'white'
            elif level < 9:
                self.color = 'orange'
            else:
                self.color = 'red'


        def toHtml(self):
            text = "<font color='{}'><i>{}</i></font>".format(self.color, self.msg)
            if not self.is_player:
                text = '<i>' + text + '</i>'
            return text

    max_messages = 12
    bg_color = QtGui.QColor('gray')
    bg_color.setAlpha(128)

    def __init__(self):
        super(LogWidget, self).__init__()
        self.messages = []
        self._all = []
        self._turn_num = None
        self._on = True

    def appendMessage(self, level, is_player, msg):
        if len(self.messages) >= self.max_messages:
            self.messages.pop(0)
        msg = self.Message(level, is_player, msg)
        self.messages.append(msg)
        self.setHtml(self.toHtml())

    def appendPlayerMessage(self, level, is_player, msg):
        self.appendMessage(level, is_player, '{}: P: '.format(self._turn_num) + msg)

    def appendDungeonMessage(self, level, is_player, msg):
        self.appendMessage(level, is_player, '{}: D: '.format(self._turn_num) + msg)

    def onTurnFinished(self, turn_num):
        self._all.extend(self.messages)
        self.messages = []
        self._turn_num = turn_num

    def toHtml(self):
        return '<br>'.join([m.toHtml() for m in self.messages])




class ChoiceItem(object):
    key_color = 'yellow'
    item_color = 'white'
    
    def __init__(self, parent, selectable, idx, item):

        self.item = item
        self.select_key = string.ascii_letters[idx]
        self._selectable = selectable

        try:
            self.key, self.value = self.item
        except (TypeError, ValueError) :
            self.key, self.value = None, self.item


    def toHtml(self):

        if self._selectable:
            html = '<td><font color="{}">{})</font></td>'.format(self.key_color, self.select_key)
        else:
            html = ''

        if self.key:
            html += ('<td align=left><font color="{}">{}&nbsp;&nbsp;</font></td>' +\
                    '<td><font color="{}">{}</font>&nbsp;</td>').format(
                    self.item_color, self.key, self.item_color, self.value)
        else:
            html += '<td><font color="{}">{}</font></td>'.format(self.item_color, self.value)
        return html


#######################
# ChoiceWidget
#######################


class ChoiceWidget(TitledTextWidget):

    title_color = 'white'
    selectable = True
    request_toggle_focus = QtCore.pyqtSignal(TitledTextWidget)

    def __init__(self):
        super(ChoiceWidget, self).__init__(self.title)
        self._items = {}

        # make sure we do not set a keyPressEvent until we
        # know we want keyboard input
        if self.selectable:
            self.keyPressEvent = self._keyPressEvent


    def reset(self, items, noset=False):

        if hasattr(items, 'items'):
            items = [(i[0],i[1]) for i in items.items()]

        self._items = {}
        for idx, item in enumerate(items):
            item = ChoiceItem(self, self.selectable, idx, item)
            self._items[item.select_key] = item

        self.body = self.toHtml()
        self.title = self.htmlTitle()

        if not noset:
            self.setHtml()

    def htmlTitle(self):
        return '<b><font color="{}">{}</font></b>'.format(self.title_color, self.title)

    def toHtml(self):
        items = []

        for key in sorted(self._items.keys()):
            items.append(self._items[key])

        html = '<table>'
        html += ''.join([('\n\t<tr>' + m.toHtml() + '</tr>')  for m in items])
        html += '\n</table>'
        return html

    def _keyPressEvent(self, event):

        if event.key() == QtCore.Qt.Key_Escape:
            self.deactivate()

        key = str(event.text())
        item = self._items.get(key)
        if item:
            idx = sorted(self._items.keys()).index(key)
            self.onActivate(idx)


class InventoryWidget(ChoiceWidget):
    title = 'Inventory'
    selectable = False
    def setPlayer(self, player):
        player.events['inventory_updated'].connect(self.reset)
        player.events['inventory_requested'].connect(self._onViewInventory)

    def _onViewInventory(self, inventory):
        self.request_toggle_focus.emit(self)


class StatsWidget(ChoiceWidget):
    title = 'Stats'
    selectable = False
    focusable = False

    def __init__(self):
        super(StatsWidget, self).__init__()
        self.background.setPen(QtGui.QPen(QtCore.Qt.NoPen))

    def setPlayer(self, player):
        player.events['stats_updated'].connect(self.reset)


class WearingWidget(ChoiceWidget):
    title = 'Equipment'
    selectable = False
    def setPlayer(self, player):
        player.events['using_updated'].connect(self.reset)
        player.events['using_requested'].connect(self._onViewWearing)

    def _onViewWearing(self, using):
        self.reset(using)
        self.request_toggle_focus.emit(self)

class IntrinsicsWidget(ChoiceWidget):
    title = 'Intrinsics'
    selectable = False
    def setPlayer(self, player):
        player.events['intrinsics_updated'].connect(self.reset)
        


class ChoicesWidget(ChoiceWidget):

    title = 'Choices'
    def __init__(self):
        super(ChoicesWidget, self).__init__()
        self._activate_callback = None
        self._opaciter = OpacityAnimation(self)
        self.hide()

    def setChoices(self, title, items, callback):
        self.show()
        self._opaciter.fadeTo(1)
        self.title = title
        self._activate_callback = callback
        self.reset(items, noset=True)
        self.setFocus()

    def onActivate(self, idx):
        print 33, idx
        self._activate_callback(idx)
        self.deactivate()

    def deactivate(self):
        self._activate_callback = None
        #self._opaciter.fadeTo(0)
        self.setOpacity(0)
        self.clearFocus()

    def setPlayer(self, player):
        print 11, player
        player.events['remove_usable_requested'].connect(self._onTakeOffItemRequested)
        player.events['add_usable_requested'].connect(self._onAddWieldingRequested)

    def _onTakeOffItemRequested(self, wearing, callback):
        self.setChoices("Remove what item?", wearing, callback)

    def _onAddWieldingRequested(self, wearables, callback):
        self.setChoices("Use what item?", wearables, callback)


class InfoWidget(QtGui.QGraphicsWidget):
    
    resize_event = QtCore.pyqtSignal()
    lost_focus = QtCore.pyqtSignal(QtGui.QGraphicsWidget)
    gained_focus = QtCore.pyqtSignal(QtGui.QGraphicsWidget)

    def __init__(self):
        super(InfoWidget, self).__init__()
        
        self.inventory = InventoryWidget()
        self.wearing = WearingWidget()
        self.choices = ChoicesWidget()
        self.intrinsics = IntrinsicsWidget()

        layout = QtGui.QGraphicsLinearLayout()
        layout.setOrientation(QtCore.Qt.Vertical)
        self.setLayout(layout)

        self._widgets = [self.inventory, self.wearing, self.intrinsics, self.choices]

        self._focus = [None, self.inventory, self.wearing, self.intrinsics]

        for widget in self._widgets:
            widget.setParentItem(self)
            widget.focusOutEvent(None)
            layout.addItem(widget)
            widget.lost_focus.connect(self.lost_focus.emit)
            widget.gained_focus.connect(self.gained_focus.emit)
            widget.request_toggle_focus.connect(self._onWidgetRequestFocus)
            widget.size_change.connect(self._onWidgetHtmlSet)

    def setPlayer(self, player):
        for widget in self._widgets:
            widget.setPlayer(player)

    def resizeEvent(self, event):
        self.resize_event.emit()

    def advanceFocus(self):
        self._focus = self._focus[1:] + [self._focus[0]]
        w = self._focus[0]
        if w:
            w.focusInEvent(None)
        [w.focusOutEvent(None) for w in self._focus[1:] if w]

    def _onWidgetHtmlSet(self, widget, size):
        return
        #FIXME the widgets keep being resized all at once
        # but I cannot trace where it is being called
        #max_width = max([widget.background.boundingRect().width() for widget in self._widgets])
        for other in [w for w in self._widgets if w is not widget]:
            rect = other.boundingRect()
            if rect.width() < size.width():
                new = QtCore.QRectF(rect.x(), rect.y(), size.width(), rect.height())
                other.background.setRect(new)

    def _onWidgetRequestFocus(self, widget):

        if widget is self._focus[0]:
            widget.focusOutEvent(None)
            self._focus = [w for w in self._focus if w is not widget] + [widget]
        else:
            widget.focusInEvent(None)
            [w.focusOutEvent(None) for w in self._focus if w and w is not widget]
            self._focus = [widget] + [w for w in self._focus if w is not widget]
            
        
        
        
