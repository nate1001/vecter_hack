
from attr_reader import AttrConfig
from __init__ import Messenger, Signal


class Condition(AttrConfig):
    
    attrs = (
        ('public', 'boolean', True),
        ('gained', 'text', True),
        ('lost', 'text', True),
        ('resisted', 'verb', True),

        ('resisted_by', 'text', True),
        ('spell_resistance', 'text', True),
    )
    def __repr__(self):
        return '<Condition {}>'.format(self.name)


class TimedCondition(Condition):
    
    def __init__(self, name, time):
        super(TimedCondition, self).__init__(name)
        if time < 1:
            raise ValueError(time)
        self._time = time

    def __repr__(self):
        return '<TimedCondition {}:{}>'.format(self.name, self.time)

    @property
    def time(self):
        return self._time

    def add(self, other):
        if self != other:
            return TypeError(other)
        if other._time < 1:
            raise ValueError(other._time)
        self._time += other._time

    def update(self):
        if self._time < 1:
            raise ValueError('{} has already timed out.'.format(self))
        self._time -= 1
        if self._time == 0:
            return True
        return False

