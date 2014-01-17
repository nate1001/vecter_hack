
from attr_reader import AttrConfig
from spell import Spell
from __init__ import Messenger, Signal

class Condition(AttrConfig):
    
    attrs = (
        ('public', 'boolean', True),
        ('gained', 'text', True),
        ('lost', 'text', True),
        ('spell_resistance', 'text', True),
    )

    def __init__(self, name):
        super(Condition, self).__init__(name)
        self._value = 0
        if self.spell_resistance:
            self.spell_resistance = Spell(self.spell_resistance)

    @property
    def active(self):
        return self._value != 0

    def clear(self):
        '''Returns whether the condition was active before clearing.'''
        if self._value == 0:
            return False
        self._value = 0
        return True

    def add_time(self, time):
        '''Returns whether the condition was not active before clearing.'''
        if time < 1:
            raise ValueError(time)

        changed = True if self._value == 0 else False
        # if we have permament condition then do not reset.
        if self._value != -1:
            self._value += time
            logger.debug('adding {} turns to condition {}.'.format(time, repr(self.name)))
        return changed

    def add_indefinite(self):
        '''Returns whether the condition was not active before clearing.'''
        changed = True if self._value != 0 else False
        # reset no matter what in case it was timed
        # -1 condition does not time out
        self._items[name] = -1
        return changed

    def update(self):
        '''Decrements timed conditions. Returns whether the condition was cleared.'''

        if self._value < -1:
            raise ValueError(value)
        # if no condition or untimed condition then ignore
        elif self._value in [0, -1]:
            return False
        # else decriment
        else:
            self._value -= 1
            return True


class Conditions(Messenger):
    __signals__ = [
        Signal('condition_added', ('new condition',)),
        Signal('condition_cleared', ('old condition',)),
    ]
    _items = {}
    for value in Condition.values():
        _items[value.name] = value

    def __init__(self, msg_callback):
        super(Conditions,  self).__init__()
        self._msg_callback = msg_callback

    def __getitem__(self, name):
        return self._items[name].active

    def spell_resistance(self, spell):
        for c in self._items.values():
            if c.spell_resistance == spell:
                return True
        return False

    def clear(self, name):
        c = self._items[name]
        if c.clear():
            if c.public:
                self.events['condition_cleared'].emit(c.name)
            if c.lost:
                self._msg_callback(5, c.lost)

    def add_time(self, name, time):
        c = self._items[name]
        if c.add_time(time):
            if c.public:
                self.events['condition_added'].emit(c.name)
            if c.gained:
                self._msg_callback(5, c.gained)

    def add_indefinite(self, name):
        c = self._items[name]
        if c.add_indefinite():
            if c.public:
                self.events['condition_added'].emit(c.name)
            if c.gained:
                self._msg_callback(5, c.gained)

    def new_turn(self):
        for c in self._items.values():
            if c.update():
                if c.public:
                    self.events['condition_cleared'].emit(c.name)
                if c.lost:
                    self._msg_callback(5, c.lost)
