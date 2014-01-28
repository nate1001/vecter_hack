
from collections import OrderedDict

from attr_reader import AttrConfig
from equipment import Inventory
from condition import Condition, TimedCondition
from messenger import Messenger, Signal, Event
from tiletype import TileType
from config import logger
from controller.action import Action
from util  import SumOfDiceDist as Dice

from pyroguelike.grid import Flags


class AttackMeans(AttrConfig):
    attrs = (
        ('condition', 'text', True),
        ('triggers_passive', 'boolean', True),
        ('physical_debug', 'msg'),
        ('condition_debug', 'msg'),
    )
    def __init__(self, name):
        super(AttackMeans, self).__init__(name)
        if self.condition:
            self.condition = Condition(self.condition)

class AttackWay(AttrConfig): 
    attrs = (
        ('try_', 'msg', True),
        ('hit', 'msg', True),
        ('miss', 'msg', True),
        ('kill', 'msg', True),
        ('verb', 'verb', True),
    )

class Attack(object):
    
    @classmethod
    def from_text(cls, text):
        way, means, dice = text.split('|')
        way = AttackWay(way)
        means = AttackMeans(means)
        dice = Dice.from_text(dice)
        return cls(way, means, dice)
    
    def __init__(self, way, means, dice, is_player=False):
        self.way = way
        self.means = means
        self.dice = dice
        self._is_player = is_player

    def set_is_player(self, is_player):
        self._is_player = is_player

    def __repr__(self):
        return '<Attack {} to {} for {}>'.format(self.way.name, self.means.name, self.dice)

    def __str__(self):
        v = self.verb(self._is_player)
        return '{} to {} ({})'.format(v, self.means.name, self.dice)

    def verb(self, is_player):
        if is_player:
            return self.way.verb.me
        else:
            return self.way.verb.she
    

class Genus(AttrConfig):
    attrs = (
        ('ascii', 'text'),
        ('actions', 'textlist'),
        ('usable', 'textlist'),
        ('intrinsics', 'textlist'),

        ('infravision', 'int'),
        ('vision', 'int'),
        ('regenerate', 'int'),
        ('spell_points', 'int'),

        ('strength', 'int', True),
        ('intellect', 'int', True),
        ('wisdom', 'int', True),
        ('dexterity', 'int', True),
        ('constitution', 'int', True),
        ('charisma', 'int', True),

        ('non_living', 'boolean', True),
    )
    '''Factory class for grouping common Species attributes.'''

    def __init__(self, name):
        super(Genus, self).__init__(name)





class Species(AttrConfig):
    attrs = (
        ('genus', 'text'),
        ('level', 'int'),
        ('speed', 'int'),
        ('ac', 'int'),
        ('magic_resistance', 'int'),
        ('alignment', 'int'),
        ('generation', 'text'),
        ('attacks', 'textlist'),
        ('passive', 'textlist'),
        ('weight', 'int'),
        ('nutrition', 'int'),
        ('sound', 'text'),
        ('size', 'text'),
        ('resistances', 'textlist'),
        ('resistances_conferred', 'textlist'),
        ('flags', 'textlist'),
        ('color', 'qtcolor'),
        #old
        ('nogenerate', 'boolean', True),
    )

    ''' Factory class for initializing monsters.'''

    def __init__(self, name):
        super(Species, self).__init__(name)
        self.genus = Genus(self.genus)
        self.attacks = [Attack.from_text(a) for a in self.attacks]
        self.passive = [Attack.from_text(a) for a in self.passive]
            
    def __repr__(self):
        return "<Species {}>".format(repr(self.name))

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return not self == other

    @property
    def value(self):
        return 1
        #FIXME return self.hit_points + self.ac + self.melee.mean
            





class Vision(object):
    
    def __init__(self):
        
        self._levels = []
        self._current = None
        self._wizard = False

    def append_level(self, size):
        self._levels.append(_Vision(size, self._wizard))
        self._current = self._levels[-1]

    @property
    def wizard(self):
        return self._wizard

    @wizard.setter
    def wizard(self, is_wizard):
        self._wizard = is_wizard
        for vision in self._levels:
            vision._wizard = is_wizard

    def set_see(self, see): self._current.set_see(see)
    def set_infravision(self, infravision): self._current.set_infravision(infravsion)
    def can_see(self, tile): return self._current.can_see(tile)

    #def can_see_other(self, other): return self._current.can_see_other(other)
    #def can_sense_other(self, other): return self._current.can_sense_other(other)

    def get_being(self, tile): return self._current.get_being(tile)
    def get_tiletype(self, tile): return self._current.get_tiletype(tile)
    def get_inventory(self, tile): return self._current.get_inventory(tile)
    def get_state(self, tile): return self._current.get_state(tile)
    def has_changed(self, tile): return self._current.has_changed(tile)

    
class _Vision(object):
    
    #TODO impliment memorized object on tile in case it moves
    
    states = (
        'see',
        'memorized',
        'unknown',
    )
    unknown = TileType('unknown')
    
    def __init__(self, size, is_wizard):

        self._see = Flags(size)
        self._last_see = Flags(size)
        self._see_changed = Flags(size)
        self._infravision = Flags(size)
        self._memorized = Flags(size)
        self._wizard = is_wizard
        
    def set_see(self, see):
        self._memorized = self._memorized | see
        self._last_see = self._see
        self._see = see
        self._see_changed = see ^ self._last_see

    def set_infravision(self, infravision):
        self._infravision = infravision

    def can_see_other(self, other):
        return self._see[other.tile.idx]

    def can_see(self, tile):
        return self._see[tile.idx]

    def can_sense_other(self, other):
        return self._infravision[other.tile.idx]

    def has_changed(self, tile):
        return self._see_changed[tile.idx]
        
    def get_state(self, tile):
        idx = tile.idx
        if self._see[idx] or self._wizard:
            return 'see'
        if self._memorized[idx]:
            return 'memorized'
        else:
            return 'unknown'

    def get_tiletype(self, tile):

        state = self.get_state(tile)
        if self._wizard or state == 'see':
            return tile.tiletype
        elif state == 'memorized':
            return tile.tiletype
        elif state == 'unknown':
            return self.unknown
        else:
            raise ValueError()

    def get_being(self, tile):

        state = self.get_state(tile)
        infravision = self._infravision[tile.idx]

        if self._wizard or state == 'see':
            return tile.being
        elif infravision:
            return tile.being
        elif state == 'memorized':
            return None
        elif state == 'unknown':
            return None
        else:
            raise ValueError()

    def get_inventory(self, tile):

        state = self.get_state(tile)
        if self._wizard or state == 'see':
            return tile.inventory
        elif state == 'memorized':
            return None
        elif state == 'unknown':
            return None
        else:
            raise ValueError()


class BeingInventory(Inventory):
    __signals__ = [
        Signal('using_updated', ('items',)),
    ]
    def __init__(self, use_slots):
        super(BeingInventory, self).__init__()
        self._use_slots = use_slots
        self._wearing = {}
        for key in self._use_slots:
            self._wearing[key] = None

    @property
    def wearing(self):
        # base it off self._items so it will have a stable order
        return [i for i in self._items if i in self._wearing.values()]

    @property
    def extrinsics(self):
        return [i.condition for i in self.wearing if i.condition]

    @property
    def ac(self):
        return sum([0] + [i.ac for i in self.wearing if hasattr(i, 'ac')])

    @property
    def melee(self):
        if 'melee' not in self._use_slots:
            raise KeyError('melee')
        return self._wearing['melee']

    def wearing_view(self):
        d = {}
        for key, item in self._wearing.items():
            if item:
                d[key] = item.view()
        return d

    def wear(self, item):
        
        if item not in self._items:
            raise ValueError(item)
        if item in self._wearing.values():
            raise ValueError('item {} is already being worn.'.format(item))
        if item.usable not in self._use_slots:
            raise ValueError('{} cannot be worn.'.format(item))
        self._wearing[item.usable] = item
        self.events['using_updated'].emit(self.wearing_view())

    def take_off(self, item):
        if item not in self._items:
            raise ValueError(item)
        if item not in self._wearing.values():
            raise ValueError('item {} is not being worn.'.format(item))
        self._wearing[item.usable] = None
        self.events['using_updated'].emit(self.wearing_view())

    def could_wear(self):
        items = []
        for item in self._items:
            if item.usable in self._use_slots and item not in self._wearing.values():
                items.append(item)
        return items



class PlayerView(Messenger):


    def __init__(self, player):

        super(PlayerView, self).__init__()
        
        self.name = player.species.name
        self.color = player.species.color
        self.char = player.species.genus
        self._inventory = player.inventory
        self._player_id = id(player)
        self._actions = player.actions
        self._vision = player.vision

        # expose events to this class
        events = (
            player.actions.events.values()
            + player.inventory.events.values()
            + player.events.values()
        )
        for event in events:
            self.events[event.name] = event

    @property
    def vision(self):
        return self._vision

    @property
    def inventory(self):
        return self._inventory

    def dispatch_command(self, name):
        return self._actions.dispatch_command(name)

    def emit_info(self):
        self.events['inventory_updated'].emit(self.inventory.view())
        self.events['using_updated'].emit(self.inventory.wearing_view())
        #self.events['stats_updated'].emit(self.stats.items)
        #self.events['intrinsics_updated'].emit(self.stats.intrinsics)



class Word(AttrConfig):
    attrs = (
        ('me', 'text'),
        ('she', 'text'),
    )

class Words(object):
    
    items = dict([(w.name, w) for w in Word.values()])

    def __init__(self, name, is_player):
        self.is_player = is_player
        self.name = name

    def __getattr__(self, attr):
        if self.is_player:
            return self.items[attr].me
        else:
            return self.items[attr].she

    def __str__(self):
        if self.is_player:
            return 'you'
        else:
            return 'the {}'.format(self.name)

    @property
    def your(self):
        if self.is_player:
            return 'your'
        else:
            if self.name.endswith('s'):
                return "the {}'".format(self.name)
            else:
                return "the {}'s".format(self.name)

    @property
    def Your(self): 
        return self.your.capitalize()

    @property
    def You(self): 
        return str(self).capitalize()

    @property
    def you_are(self):
        if self.is_player:
            return 'you are'
        else:
            return 'the {} is'.format(self.name)
    @property
    def You_are(self): return self.you_are.capitalize()

    def to_dict(self):
        d = {}
        for key in self.items:
            d[key] = getattr(self, key)
        d['you'] = str(self)
        d['You'] = self.You
        d['your'] = self.your
        d['Your'] = self.Your
        d['you_are'] = self.you_are
        d['You_are'] = self.You_are
        return d

        

class Being(Messenger):
    '''The instance of a Species.'''


    __signals__ = [
        Signal('stats_updated', ('stats',)),
        Signal('intrinsics_updated', ('intrinsics',)),
        Signal('condition_added', ('intrinsics',)),
        Signal('condition_cleared', ('intrinsics',)),
    ]

    NORMAL_SPEED = 12
    HIT_POINT_SIDES = 8

    guid = 0


    class View(object):
        
        def __init__(self, being):

            self.is_player = being.is_player
            self.color = being.species.color
            self.char = being.species.genus.ascii
            self.category = 'genus/' + being.species.genus.name
            self.name = being.species.name
            self.guid = being.guid
            self.direction = being.direction

            if being.is_player:
                self.category = 'player'
                self.using = [i.view() for i in being.inventory.wearing]

        def __str__(self):
            return '<Being.View {}>'.format(self.name)

    def __init__(self, controller, species, is_player=False):
        
        super(Being, self).__init__()
        
        self._species = species

        Being.guid += 1 #FIXME
        self.guid = Being.guid
        self.actions = Action.from_being(controller, self) 
        self.is_player = is_player
        self.inventory = BeingInventory(species.genus.usable)
        self.vision = Vision()
        self.words = Words(species.name, is_player)
        self.words_dict = self.words.to_dict()
        self.value = species.value
        for a in self.species.attacks:
            a.set_is_player(is_player)

        self._wizard = False
        self._direction = None
        hp = Dice(species.level, self.HIT_POINT_SIDES).roll()
        self._stats = {
            'hit_points': hp,
            'max_hit_points': hp,
            'spell_points': 10,
            'vision': 10,
            'turns': 0,
            'experience': 0,
            'movement_points': species.speed
        }
        #intrinsics
        self._timed_conditions = []
        self._conditions= []
        if not self.is_player:
            self.set_condition('asleep')


    def __str__(self):
        if self.is_player:
            return 'you'
        else:
            return 'the {}'.format(self.species.name)

    def __repr__(self):
        return '#{} {}'.format(self.guid, self.species.name)

    def new_level(self, size):
        self.vision.append_level(size)

    def view(self):
        return self.__class__.View(self)

    def new_turn(self):
        self._stats['movement_points'] += self.species.speed
        remove = [c for c in self._timed_conditions if c.update()]
        for r in remove:
            self._timed_conditions.remove(r)

    def move_made(self):
        self._stats['movement_points'] -= self.NORMAL_SPEED
        if self._stats['movement_points'] < 0:
            raise ValueError(self._stats['movement_points'])

    def has_condition(self, name):
        c = Condition(name)
        ct = TimedCondition(name, 1)
        return (
            c in self.inventory.extrinsics 
            or c in self.species.resistances
            or c in self._conditions
            or ct in self._timed_conditions
        )

    def clear_condition(self, name):
        found = False
        c = Condition(name)
        if c in self._timed_conditions:
            found = True
            self._timed_conditions.remove(c)
        if c in self._conditions:
            found = True
            self._conditions.remove(c)
        if not found:
            raise KeyError(c)

    def set_condition(self, name, time=None):

        if time:
            self._set_timed_condition(name, time)
        else:
            self._set_condition(name)

    def _set_condition(self, name):
        c = Condition(name)
        if c in self._conditions:
            raise ValueError('{} already set'.format(c))
        self._conditions.append(c)

    def _set_timed_condition(self, name, time):

        tc = TimedCondition(name, time)
        if tc in self._timed_conditions:
            [c.add(tc) for c in self._timed_conditions if c == tc]
        else:
            self._timed_conditions.append(tc)


    #######################################
    ## being props
    #######################################

    #FIXME should we make this public?
    @property
    def conditions(self):
        return (
              self.inventory.extrinsics 
            + self.species.resistances
            + self._conditions
            + self._timed_conditions
        )

    @property
    def see_radius(self):
        if self.has_condition('blind'):
            return 0
        else:
            return self._stats['vision']
        self.vision.set_see(bitmap, tile.idx, radius)

    @property
    def species(self):
        return self._species
    
    @property
    def attacks(self):
        l = []
        for a in self.species.attacks:
            # if were not wielding a wepon for a melee attack
            # change it to a punching attack
            if a.way.name == 'wields' and not self.melee:
                a = Attack(AttackWay('punches'), a.means, a.dice, is_player=self.is_player)
            #else set the dice to weapon
            if a.way.name == 'wields' and self.melee:
                a = Attack(a.way, a.means, self.melee.dice, is_player=self.is_player)
            l.append(a)
        return l

    @property
    def passive(self):
        return self.species.passive

    @property
    def max_hit_points(self): 
        return self._stats['hit_points']

    @property
    def hit_points(self): 
        return self._stats['hit_points']
    @hit_points.setter
    def hit_points(self, value): 
        value = min(max(0, value), self._stats['max_hit_points'])
        self._stats['hit_points'] = value
        #self.events['stats_updated'].emit(self.items)

    @property
    def experience(self): return self._stats['experience']
    @experience.setter
    def experience(self, value):
        self._stats['experience'] = value
        #self.events['stats_updated'].emit(self.items)

    @property
    def ac(self): return self.species.ac

    @property
    def melee(self): return self.inventory.melee

    @property
    def infravision(self): return self.species.infravision

    @property
    def gold(self): return self._stats['gold']

    @property
    def wizard(self): return self._wizard
    @wizard.setter
    def wizard(self, is_wizard):
        self.vision.wizard = is_wizard
        self._wizard = is_wizard

    @property
    def direction(self): return self._direction
    @direction.setter
    def direction(self, direction):
        #if direction not in self.directions:
        #    raise ValueError(direction)
        self._direction = direction

    @property
    def non_living(self):
        return self.species.genus.non_living

    @property
    def is_dead(self):
        return self.hit_points < 1

    @property
    def name(self):
        return self.species.name

    @property
    def color(self):
        return self.species.color

    @property
    def char(self):
        return self.species.genus.ascii

    @property
    def can_move(self):
        return (
            not self.has_condition('paralyzed')
            and not self.has_condition('asleep')
        )
          

if __name__ == '__main__':

     human = Species('orc')
     being = Being(None, human)


