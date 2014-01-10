
from attr_reader import AttrConfig
from util import get_article
from __init__ import Messenger, Signal


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

    @property
    def items(self):
        return [(str(i)) for i in self._items]

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

    def append(self, item):
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
        

class Equipment(object):
    '''The base class for Equipment such as weapons.'''


    def __init__(self, name):
        super(Equipment, self).__init__(name)
        self._name = name
    
    @property
    def char(self):
        return self.ascii

    def clone(self):
        return self.__class__(self._name)
    
    #FIXME check for equip class also
    def is_same(self, other):
        return self.name == other.name

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Equipment {}>".format(self._name)



class EquipmentStack(object):
    '''Container to manage stackable and nonstackable items.'''

    class View(object):
        def __init__(self, stack):
            self.name = stack.name
            self.category = stack.item.usable
            self.color = stack.color
            self.char = stack.char
            self.count = stack._count
            self.string = stack.string()
            self.usable = stack.item.usable
            self.direction = None

        def __repr__(self):
            return "EquipmentStack.View {}".format(self.string)

        def __str__(self):
            return self.string

        @property
        def description(self):
            return ', '.join([(str(i)) for i in self._items])

    @classmethod
    def from_cls(cls, kls, name):
        item = kls(name)
        return cls.from_item(item)
    
    @classmethod
    def from_item(cls, item, count=1):
        return cls(item, count)
    
    def __init__(self, item, count):
        
        self._validate_count(item, count)
        self._item = item
        self._count = count
        self._being_worn = False

    def __str__(self):
        return self.string()

    def __repr__(self):
        return "<EquipmentStack {}>".format(self)

    def view(self):
        return self.__class__.View(self)

    def string(self, worninfo=False):
        if self._being_worn and worninfo:
            worn = "(being worn)"
        else:
            worn = ""
        if self._count > 1:
            count = str(self._count)
            name = self._item.plural
        else:
            count = get_article(self._item.name)
            name = self._item.name
        return "{} {} {}".format(count, name, worn)

            
    @property
    def char(self):
        return self._item.char

    @property
    def name(self):
        return self._item.name

    @property
    def usable(self):
        return self._item.usable

    @property
    def color(self):
        return self._item.color

    @property
    def item(self):
        return self._item

    @property
    def stackable(self):
        return self._item.stackable

    def _validate_count(self, item, count):

        if count < 1 or int(count) != count:
            raise ValueError(count)

        if count != 1 and not item.stackable:
            raise ValueError(count)

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
    


class MeleeWeapon(Equipment, AttrConfig):

    attrs=(
        ('melee', 'dice'),
        ('color', 'qtcolor'),
    )
    ascii=')'

    value = 1
    stackable = False
    usable='melee'

    def __init__(self, name):
        super(MeleeWeapon, self).__init__(name)
        self.value = self.melee.mean

class Amunition(Equipment, AttrConfig):

    attrs = (
        ('damage', 'dice'),
        ('color', 'qtcolor'),
        ('plural', 'text'),
    )
    ascii='{'
    stackable = True
    usable='amunition'
    value = 1

    def __init__(self, name):
        super(Amunition, self).__init__(name)
        self.value = self.damage.mean

class Armor(Equipment, AttrConfig):

    attrs=(
        ('color', 'qtcolor'),
        ('ac', 'int'),
    )
    ascii='['
    usable='armor'
    value = 1
    stackable = False

    def __init__(self, name):
        super(Armor, self).__init__(name)
        self.value = self.ac

class Light(Equipment, AttrConfig):

    attrs=(
        ('color', 'qtcolor'),
        ('radius', 'int'),
    )
    ascii='('
    value = 1
    stackable = True
    usable = 'light'

    def __init__(self, name):
        super(Light, self).__init__(name)
        self.value = self.radius

    @property
    def plural(self):
        return self.name


equipment_classes = [
    MeleeWeapon,
    Amunition,
    Armor,
    Light,
]


if __name__ == '__main__':

    sword = Weapon('long sword')
    stack = EquipmentStack.from_item(sword)
    print sword
    print sword.clone()
    

