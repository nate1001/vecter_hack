import string 
from collections import OrderedDict

from PyQt4 import QtCore, QtGui

from animation import OpacityAnimation
from util import TextWidget, TitledTextWidget

from config import direction_by_name


class InputWidget(QtGui.QGraphicsWidget):

    finished = QtCore.pyqtSignal()
    canceled = QtCore.pyqtSignal()
    point_size = 20
    padding = 5
    bg_color = QtGui.QColor('white')
    question_color = QtGui.QColor('blue')

    class TextItem(QtGui.QGraphicsTextItem):

        def __init__(self, parent):
            super(InputWidget.TextItem, self).__init__(parent)

        def keyPressEvent(self, event):

            if event.key() == QtCore.Qt.Key_Return:
                self.parentItem()._onFinished(str(self.toPlainText()))
                self.setPlainText('')
            elif event.key() == QtCore.Qt.Key_Escape:
                self.parentItem()._onFinished(None)
                self.setPlainText('')
            else:
                event.ignore()
            self.parentItem()._setBackground()
            super(InputWidget.TextItem, self).keyPressEvent(event)

    
    def __init__(self, parent):
        super(InputWidget, self).__init__(parent)

        self._callback = None

        self.title = QtGui.QGraphicsSimpleTextItem(self)
        font = self.title.font()
        font.setPointSize(self.point_size)
        font.setItalic(True)
        self.title.setFont(font)

        self.question = self.TextItem(self)
        font = self.question.font()
        font.setPointSize(self.point_size)
        self.question.setFont(font)
        self.question.setDefaultTextColor(self.question_color)
        self.question.setTextInteractionFlags(
            QtCore.Qt.TextEditable
            | QtCore.Qt.TextEditorInteraction
        )
        p = self.padding
        self.title.setPos(p, p)
        self.question.setPos(p, p + self.point_size)
        self.question.setEnabled(False)

        self.background = QtGui.QGraphicsRectItem(self)
        self.background.setBrush(self.bg_color)
        self.background.setZValue(-1)

        self.hide()

    def _setBackground(self):

        w = max(self.title.boundingRect().width() + self.point_size, self.question.boundingRect().width() + self.point_size)
        h = self.title.boundingRect().height() + self.question.boundingRect().height()
        p = self.padding
        rect = QtCore.QRectF(0, 0, w+p, h+p)
        self.background.setRect(rect)

    def _onFinished(self, answer):
        if answer is not None:
            self.canceled.emit()
            self._callback(answer)
            self._callback = None
        else:
            self.finished.emit()
        self.question.ungrabKeyboard()
        self.question.setEnabled(False)
        self.hide()

    def ask(self, question, callback):
        
        self.show()
        self.question.setEnabled(True)
        self.question.grabKeyboard()
        self.title.setText(question)
        self._setBackground()
        self._callback = callback



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

    def appendPlayerMessage(self, level, msg):
        self.appendMessage(level, True, '{}: P: '.format(self._turn_num) + msg)

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
    
    def __init__(self, parent, selectable, idx, item, item_keys=False):

        if item_keys:
            self.item = item[0]
            self.select_key = item[1]
        else:
            self.item = item
            self.select_key = string.ascii_letters[idx]
        self._selectable = selectable

        try:
            self.key, self.value = self.item
        except (TypeError, ValueError) :
            self.key, self.value = None, self.item

    def __repr__(self):
        return '<ChoiceItem {}:{}>'.format(self.select_key, self.item)


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
        self._items = OrderedDict()

        # make sure we do not set a keyPressEvent until we
        # know we want keyboard input
        if self.selectable:
            self.keyPressEvent = self._keyPressEvent


    def reset(self, items, noset=False, item_keys=False):

        if hasattr(items, 'items'):
            items = [(i[0],i[1]) for i in items.items()]

        self._items = OrderedDict()
        for idx, item in enumerate(items):
            item = ChoiceItem(self, self.selectable, idx, item, item_keys=item_keys)
            self._items[item.select_key] = item

        self.body = self.toHtml()
        self.title = self.htmlTitle()

        if not noset:
            self.setHtml()

    def htmlTitle(self):
        return '<b><font color="{}">{}</font></b>'.format(self.title_color, self.title)

    def toHtml(self):
        items = []

        for key in self._items.keys():
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
            idx = (self._items.keys()).index(key)
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
        self._conditions = []
        self._old = None

    def setPlayer(self, player):
        player.events['stats_updated'].connect(self._onStatsUpdated)
        player.events['condition_added'].connect(self._onConditionAdded)
        player.events['condition_cleared'].connect(self._onConditionCleared)

    def _onStatsUpdated(self, items):
        if self._conditions:
            items['conditions'] = ', '.join(self._conditions)
        self.reset(items)
        self._old = items

    def _onConditionAdded(self, condition):
        if condition in self._conditions:
            return
        self._conditions.append(condition)
        items = self._old.copy()
        self._onStatsUpdated(items)

    def _onConditionCleared(self, condition):
        self._conditions.remove(condition)
        items = self._old.copy()
        if items.get('conditions'):
            items.pop('conditions')
        self._onStatsUpdated(items)


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
        self._activate_callback(idx)
        self.deactivate()

    def deactivate(self):
        self._activate_callback = None
        self._opaciter.fadeTo(0)
        #self.setOpacity(0)
        self.clearFocus()

    def setPlayer(self, player):
        player.events['remove_usable_requested'].connect(self._onTakeOffItemRequested)
        player.events['usable_requested'].connect(self._onUsableRequested)

    def _onTakeOffItemRequested(self, wearing, callback):
        self.setChoices("Remove what item?", wearing, callback)

    def _onUsableRequested(self, question, usables, callback):
        self.setChoices(question, usables, callback)


class DirectionWidget(ChoiceWidget):
    title = 'Direction'

    def __init__(self):
        super(DirectionWidget, self).__init__()
        self._activate_callback = None
        self._opaciter = OpacityAnimation(self)
        self.hide()
        self._index = None

    def setChoices(self, title, items, callback):
        self.show()
        self._opaciter.fadeTo(1)
        self.title = title
        self._activate_callback = callback
        self.reset(items, noset=True, item_keys=True)
        self.setFocus()

    def onActivate(self, idx):
        direction = direction_by_name[direction_by_name.keys()[idx]]
        self._activate_callback(self._index, direction)
        self.deactivate()

    def deactivate(self):
        self._activate_callback = None
        self._index = None
        self._opaciter.fadeTo(0)
        self.clearFocus()

    def setPlayer(self, player):
        player.events['item_direction_requested'].connect(self._onItemDirectionRequested)

    def _onItemDirectionRequested(self, question, index, callback):

        directions = []
        for d in direction_by_name.values():
            directions.append((d.name, d.key))

        self._index = index
        self.setChoices(question, directions, callback)


class InfoWidget(QtGui.QGraphicsWidget):
    
    resize_event = QtCore.pyqtSignal()
    lost_focus = QtCore.pyqtSignal(QtGui.QGraphicsWidget)
    gained_focus = QtCore.pyqtSignal(QtGui.QGraphicsWidget)

    def __init__(self):
        super(InfoWidget, self).__init__()
        
        self.inventory = InventoryWidget()
        self.wearing = WearingWidget()
        self.choices = ChoicesWidget()
        self.direction = DirectionWidget()
        self.intrinsics = IntrinsicsWidget()

        layout = QtGui.QGraphicsLinearLayout()
        layout.setOrientation(QtCore.Qt.Vertical)
        self.setLayout(layout)

        self._widgets = [self.inventory, self.wearing, self.intrinsics, self.choices, self.direction]

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
            
        
        
        
