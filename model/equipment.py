
from random import random, shuffle

from util import get_article, normal, Chance, SumOfDiceDist as Dice
from attr_reader import AttrReader, AttrConfig
from spell import Spell
from condition import Condition

from __init__ import Messenger, Signal
from config import logger

def init_appearance():
    Wand.init_appearance()
    Scroll.init_appearance()
    Potion.init_appearance()
    Ring.init_appearance()

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
            self.name = stack.item.view_name()
            self.category = stack.item.usable
            self.color = stack.color
            self.char = stack.char
            self.count = stack._count
            self.usable = stack.item.usable
            self.desc = stack.desc()

            #for attr in stack._item.attrs:
            #    setattr(self, attr[0], getattr(stack.item, attr[0]))
            if hasattr(stack.item, 'kind'):
                self.kind = stack.item.kind

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

    @property
    def appearance(self):
        return self._item.appearance

    @property
    def resistances(self):
        if hasattr(self._item, 'resistances'):
            return self._item.resistances
        else:
            return []


class EquipmentKind(AttrConfig):

    attrs = (
        ('generate', 'chance'),
        ('cursed', 'chance'),
        ('blessed', 'chance'),
        ('weight', 'int', True),
        ('color', 'qtcolor', True),
    )

class Equipment(AttrConfig):
    '''The base class for Equipment such as weapons.'''


    value = None
    _appearance = {}

    @classmethod
    def klass_by_name(cls, name):
        for klass in equipment_classes:
            if klass.usable == name:
                return klass
        raise KeyError(name)

    @classmethod
    def init_appearance(cls):
        cls._appearance = {}
        appearance = AttrReader.items_from_klass(cls.appearance_cls)
        shuffle(appearance)
        for i, item in enumerate(AttrReader.items_from_klass(cls)):
            cls._appearance[item.name] = appearance[i]

    def __init__(self, name):
        super(Equipment, self).__init__(name)
        self._name = name
        self._changed_callback = None
        self.identified = False

    def __repr__(self):
        return "<Equipment {}>".format(self._name)

    @property
    def appearance(self):
        return self._appearance[self.name]
    
    @property
    def char(self):
        return self.ascii

    @property
    def known(self):
        if not self._appearance:
            return True
        return self.appearance.known
    @known.setter
    def known(self, is_known):
        if not self._appearance:
            raise TypeError
        self.appearance.known = True
        self.changed()

    def clone(self):
        return self.__class__(self._name)
    
    #FIXME check for equip class also
    def is_same(self, other):
        return self.name == other.name

    def set_changed_callback(self, callback):
        self._changed_callback = callback

    def changed(self):
        self._changed_callback(self)

    def view_name(self):
        if self._appearance:
            return self._appearance[self.name].name.lower()
        return self.name

    

class MeleeWeapon(Equipment, AttrConfig):

    kind = EquipmentKind('weapon')
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

    kind = EquipmentKind('weapon')
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

    kind = EquipmentKind('armor')
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

    kind = EquipmentKind('tool')
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

class PotionName(AttrConfig):
    attrs = tuple()
    def __repr__(self):
        return '<ScrollName {}>'.format(self.name)
    def __init__(self, name):
        super(PotionName, self).__init__(name)
        self.known = False

class Potion(Equipment, AttrConfig):

    kind = EquipmentKind('potion')
    appearance_cls = PotionName
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
        self.spell = Spell(self.spell)

    def desc(self, count):

        #FIXME an article
        if count > 1:
            s = 's'
            a = '{} '.format(count)
        else:
            s = ''
            a = 'a '

        if not self.appearance.known:
            name = '{} potion{}'.format(self.appearance.name, s)
        else:
            name = 'potion of {}'.format(self.name)

        return '{} {}'.format(a, name)


class RayKind(object):

    min_charges = 3

    def __init__(self, kind, max_charges, directional, bounce, ray_dice):
        self.kind = kind
        self.max_charges = max_charges
        self.directional = directional
        self.bounce = bounce
        self.charge_dice = Dice(1, max_charges, minimum=self.min_charges, maximum=max_charges-4)
        self.ray_dice = ray_dice


class Material(AttrConfig):
    attrs = (
        ('color', 'qtcolor'),
        ('rots', 'boolean', True),
        ('burns', 'boolean', True),
        ('corrodes', 'boolean', True),
        ('rusts', 'boolean', True),
        ('spell_hinder', 'boolean', True),
    )

class WandName(AttrConfig):
    attrs = (('material', 'text'),)

    def __repr__(self):
        return '<WandName {} {}>'.format(self.name, self.material)

    def __init__(self, name):
        super(WandName, self).__init__(name)
        self.known = False
        self.color = Material(self.material).color


class Wand(Equipment, AttrConfig):
    
    kind = EquipmentKind('wand')
    appearance_cls = WandName
    attrs=(
        ('prob', 'int'),
        ('spell', 'text'),
        ('kind', 'text'),
        ('cost', 'int'),
        ('zap', 'text', True),
        ('can_tunnel', 'boolean', True),
    )
    ascii='/'
    stackable = False
    value = 1
    usable = 'wand'
    bounce = Chance(.2)
    weight = 7
    kinds = {
        'ray': RayKind('ray', 8, True, True, Dice(1, 5, modifier=+6)),
        'beam': RayKind('beam', 8, True, False, Dice(1, 6, modifier=+5)),
        'nodir': RayKind('nodir', 15, False, False, None),
        'wishing': RayKind('wishing', 3, False, False, None),
    }

    def __init__(self, name):
        super(Wand, self).__init__(name)
        self.kind = self.kinds[self.kind]
        self._charges = self.kind.charge_dice.roll()
        self.spell = Spell(self.spell)

    def did_bounce(self):
        if not self.kind.bounce:
            return False
        return self.bounce.roll()

    def desc(self, count):
        return 'a wand of {} ({})'.format(self.name, self.charges)

        if self.identified:
            return 'a wand of {} ({})'.format(self.name, self.charges)
        elif self.appearance.known:
            return 'a wand of {}'.format(self.name)
        else:
            return 'a {} wand'.format(self.appearance.name)

    def view_name(self):
        return self.appearance.material

    @property
    def charges(self):
        return self._charges
    @charges.setter
    def charges(self, new):
        self._charges = new
        self.changed()

    @property
    def color(self):
        return self._appearance[self.name].color


class ScrollName(AttrConfig):
    attrs = tuple()
    def __repr__(self):
        return '<ScrollName {}>'.format(self.name)
    def __init__(self, name):
        super(ScrollName, self).__init__(name)
        self.known = False

class Scroll(Equipment, AttrConfig):

    kind = EquipmentKind('scroll')
    attrs=(
        ('spell', 'text'),
        ('cost', 'int'),
        ('prob', 'int'),
        ('marker', 'int'),
    )
    ascii='?'
    appearance_cls = ScrollName
    stackable = True
    value = 1
    usable = 'scroll'
    color = 'white'

    def __init__(self, name):
        super(Scroll, self).__init__(name)
        self.spell = Spell(self.spell)

    def desc(self, count):
        if not self.appearance.known:
            name = 'labled ' + self.appearance.name
        else:
            name = 'of ' + self.name
        if count > 1:
            return '{} scroll {}'.format(count, name)
        else:
            return 'a scroll {}'.format(name)

    @property
    def color(self):
        return self.kind.color


class RingName(AttrConfig):
    attrs = tuple()
    def __repr__(self):
        return '<RingName {}>'.format(self.name)
    def __init__(self, name):
        super(RingName, self).__init__(name)
        self.known = False

class Ring(Equipment, AttrConfig):

    kind = EquipmentKind('ring')
    attrs=(
        ('cost', 'int'),
        ('condition', 'text'),
    )
    ascii='='
    appearance_cls = RingName

    stackable = False
    value = 1
    usable = 'ring'

    def __init__(self, name):
        super(Ring, self).__init__(name)
        self.condition = Condition(name)

    def desc(self, count):
        return 'a ring of {}'.format(self.name)

    @property
    def color(self):
        return self.kind.color


equipment_classes = [
    MeleeWeapon,
    Amunition,
    Armor,
    Light,
    Treasure,
    Potion,
    Wand,
    Scroll,
    Ring,
]


if __name__ == '__main__':

    sword = Weapon('long sword')
    stack = EquipmentStack.from_item(sword)
    
