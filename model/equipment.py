
from random import random

from attr_reader import AttrConfig
from util import get_article, normal
from util import Chance

from __init__ import Messenger, Signal
from config import logger


class Inventory(Messenger):
    '''The bag that holds EquipmentStack.'''

    __signals__ = [
        Signal('inventory_updated', ('inventory',)),
    ]

    class View(list):
        def __init__(self, inventory):
            for item in [item.view() for item in inventory._items]:
                self.append(item)

    def __init__(self):
        super(Inventory, self).__init__()
        self._items = []

    def __nonzero__(self):
        return len(self._items) != 0

    def __iter__(self):
        return self._items.__iter__()

    def __repr__(self):
        return repr(self._items)

    def __str__(self):
        return ','.join([str(e) for e in self._items])

    @property
    def description(self):
        return ', '.join([(str(i)) for i in self._items])

    #@property
    #def items(self):
    #    return [(i.descr())) for i in self._items]

    @property
    def color(self):
        if not self:
            return None
        return self._items[-1].color

    @property
    def char(self):
        return self._items[-1].char

    def view(self):
        return self.__class__.View(self)

    def by_klass_name(self, name):
        items = []
        for item in self._items:
            if item.usable == name:
                items.append(item)
        return items

    def on_item_used(self, item):
        self.remove(item)

    def on_item_changed(self, item):
        self.events['inventory_updated'].emit(self.view())

    def append(self, item):
        item.set_changed_callback(self.on_item_changed)
        item.set_used_callback(self.on_item_used)
        found = False
        # if item supports multi counts
        if item.stackable:
            for other in self:
                if other.can_stack(item):
                    other.stack(item)
                    found = True
            if not found:
                self._items.append(item)
        else:
            self._items.append(item)

        self.events['inventory_updated'].emit(self.view())

    def remove(self, item):
        self._items.remove(item)
        self.events['inventory_updated'].emit(self.view())

    def pop(self):
        item = self._items.pop()
        self.events['inventory_updated'].emit(self.view())
        return item

    def get_by_class(self, klass):
        return [i for i in self._items if type(i.item) == klass]
        



class EquipmentStack(object):
    '''Container to manage stackable and nonstackable items.'''

    class View(object):
        def __init__(self, stack):
            self.name = stack.name
            self.category = stack.item.usable
            self.color = stack.color
            self.char = stack.char
            self.count = stack._count
            self.usable = stack.item.usable
            self.desc = stack.desc()

        def __repr__(self):
            return "EquipmentStack.View {}".format(self.desc)

        def __str__(self):
            return self.desc

        @property
        def description(self):
            return ', '.join([(str(i)) for i in self._items])

    @classmethod
    def from_cls(cls, kls, name, count=1):
        item = kls(name)
        return cls.from_item(item, count)
    
    @classmethod
    def from_item(cls, item, count=1):
        return cls(item, count)
    
    def __init__(self, item, count):
        
        self._validate_count(item, count)
        self._item = item
        self._count = count
        self._being_worn = False
        self._used_callback = None
        self._changed_callback = None

    def __str__(self):
        return self.desc()

    def __repr__(self):
        return "<EquipmentStack {}>".format(self)

    def set_changed_callback(self, callback):
        self._changed_callback = callback
        self._item.set_changed_callback(callback)

    def set_used_callback(self, callback):
        self._used_callback = callback

    def view(self):
        return self.__class__.View(self)

    def desc(self):
        return self._item.desc(self._count)

    def _validate_count(self, item, count):

        if count < 1 or int(count) != count:
            raise ValueError(count)

        if count != 1 and not item.stackable:
            raise ValueError('{} item is not stackable and count is {}.'.format(repr(item), count))

    def split_stack(self, count):
        '''Split apart stack by count amount and return new stack or raise ValueError.'''
        new_count = self._count - count
        self._validate_count(self._item, new_count)
        new_split = EquipmentStack(self._item.clone(), new_count)
        return new_split
    
    def stack(self, other):
        '''Add other's count to stack and set other's count to zeror, or raise ValueError.'''
        
        if not self.can_stack(other):
            raise ValueError(other)
        self._count += other._count
        other._count = 0
    
    def can_stack(self, other):
        '''Returns if it is possible to stack this with another stack.'''
        return other is not self and self._item.stackable and self._item.is_same(other._item)

    @property
    def count(self):
        return self._count
    @count.setter
    def count(self, value):
        if not self._item.stackable:
            raise TypeError('Cannot change count on a nonstackable item {}.'.format(item))
        self._count = value
        if self._count < 1:
            self._used_callback(self)
        else:
            self._changed_callback(self)

    @property
    def stackable(self):
        return self._item.stackable

    @property
    def usable(self):
        return self._item.usable

    @property
    def name(self):
        return self._item.name

    @property
    def item(self):
        return self._item

    @property
    def color(self):
        return self._item.color

    @property
    def char(self):
        return self._item.char

    @property
    def charges(self):
        return self._item.charges

    @property
    def spell(self):
        return self._item.spell

    @property
    def kind(self):
        return self._item.kind



class Equipment(object):
    '''The base class for Equipment such as weapons.'''

    value = None

    @classmethod
    def klass_by_name(cls, name):
        for klass in equipment_classes:
            if klass.usable == name:
                return klass
        raise KeyError(name)

    def __init__(self, name):
        super(Equipment, self).__init__(name)
        self._name = name
        self._changed_callback = None

    def __repr__(self):
        return "<Equipment {}>".format(self._name)
    
    @property
    def char(self):
        return self.ascii

    def clone(self):
        return self.__class__(self._name)
    
    #FIXME check for equip class also
    def is_same(self, other):
        return self.name == other.name

    def set_changed_callback(self, callback):
        self._changed_callback = callback

    def changed(self):
        self._changed_callback(self)
    

class MeleeWeapon(Equipment, AttrConfig):

    attrs=(
        ('melee', 'dice'),
        ('color', 'qtcolor'),
    )
    ascii=')'

    stackable = False
    usable = 'melee'
    value = 5

    def __init__(self, name):
        super(MeleeWeapon, self).__init__(name)
        self.value = self.melee.mean

    def desc(self, count):
        return '{} {}'.format(get_article(self.name), self.name)


class Amunition(Equipment, AttrConfig):

    attrs = (
        ('damage', 'dice'),
        ('color', 'qtcolor'),
        ('plural', 'text'),
    )
    ascii='{'
    stackable = True
    usable='amunition'
    value = 2

    def __init__(self, name):
        super(Amunition, self).__init__(name)
        self.value = self.damage.mean

    def desc(self, count):
        if count > 1:
            return '{} {}'.format(count, self.plural)
        else:
            return '{} {}'.format(get_article(self.name), self.name)


class Armor(Equipment, AttrConfig):

    attrs=(
        ('color', 'qtcolor'),
        ('ac', 'int'),
    )
    ascii='['
    usable='armor'
    stackable = False
    value = 4

    def __init__(self, name):
        super(Armor, self).__init__(name)
        self.value = self.ac

    def desc(self, count):
        return '{}'.format(self.name)

class Light(Equipment, AttrConfig):

    attrs=(
        ('color', 'qtcolor'),
        ('radius', 'int'),
        ('plural', 'text'),
    )
    ascii='('
    stackable = True
    usable = 'light'
    value = 2

    def __init__(self, name):
        super(Light, self).__init__(name)
        self.value = self.radius

    def desc(self, count):
        if count > 1:
            return '{} {}'.format(count, self.plural)
        else:
            return '{} {}'.format(get_article(self.name), self.name)


class Treasure(Equipment, AttrConfig):

    attrs=(
        ('color', 'qtcolor'),
        ('value', 'int'),
    )
    ascii='$'
    stackable = True
    value = 1
    usable = 'treasure'

    def __init__(self, name):
        super(Treasure, self).__init__(name)

    def desc(self, count):
        if count > 1:
            return '{} {} pieces'.format(count, self.name)
        else:
            return '1 piece of {}'.format(self.name)


class Potion(Equipment, AttrConfig):

    attrs=(
        ('color', 'qtcolor'),
        ('value', 'int'),
        ('spell', 'text'),
    )
    ascii='!'
    stackable = True
    value = 1
    usable = 'potion'

    def __init__(self, name):
        super(Potion, self).__init__(name)

    def desc(self, count):
        if count > 1:
            return '{} potions of {}'.format(count, self.name)
        else:
            return 'a potion of {}'.format(self.name)

class Wand(Equipment, AttrConfig):

    attrs=(
        ('color', 'qtcolor'),
        ('value', 'int'),
        ('spell', 'text'),
        ('kind', 'text'),
        ('avg_charges', 'dice'),
    )
    ascii='/'
    stackable = False
    value = 1
    usable = 'wand'
    ray_length = 10
    bounce = Chance(.2)

    def __init__(self, name):
        super(Wand, self).__init__(name)
        self._charges = self.avg_charges.roll()

    def did_bounce(self):
        if self.kind != 'ray':
            return False
        return self.bounce.roll()

    def desc(self, count):
        return 'a wand of {} ({})'.format(self.name, self.charges)

    @property
    def charges(self):
        return self._charges
    @charges.setter
    def charges(self, new):
        self._charges = new
        self.changed()

class Scroll(Equipment, AttrConfig):

    attrs=(
        ('color', 'qtcolor'),
        ('value', 'int'),
        ('spell', 'text'),
    )
    ascii='?'
    stackable = True
    value = 1
    usable = 'scroll'

    def __init__(self, name):
        super(Scroll, self).__init__(name)

    def desc(self, count):
        if count > 1:
            return '{} scroll of {}'.format(count, self.name)
        else:
            return 'a scroll of {}'.format(self.name)

equipment_classes = [
    MeleeWeapon,
    Amunition,
    Armor,
    Light,
    Treasure,
    Potion,
]


if __name__ == '__main__':

    sword = Weapon('long sword')
    stack = EquipmentStack.from_item(sword)
    
