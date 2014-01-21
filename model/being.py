
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

        #XXX I dont think we need this here as it will pop trying to add the class in Action
        #for action in self.actions:
        #    if action.lower() not in [a.__name__.lower() for a in registered_actions_types]:
        #        raise ValueError("Genus %s does not have a registered action type for %s" %
        #             (repr(name), repr(action.lower())) )

class IntrinsicAttack(AttrConfig):
    attrs = (
        ('damage', 'dice'),
        ('condition', 'text'),
        ('protection', 'text'),
        ('chance', 'float'),
        ('verb', 'text'),
    )

    def __repr__(self):
        return "<IntrinsicAttack {} chance:{}>".format(self.name, self.chance)

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
        ('weight', 'int'),
        ('nutrition', 'int'),
        ('sound', 'text'),
        ('size', 'text'),
        ('resistances', 'textlist'),
        ('resistances_conferred', 'textlist'),
        ('flags', 'textlist'),
        ('color', 'qtcolor'),

        ('nogenerate', 'boolean', True),
    )

    ''' Factory class for initializing monsters.'''

    def __init__(self, name):
        super(Species, self).__init__(name)
        self.genus = Genus(self.genus)
        self.i_attacks = []
        #if self.intrinsic_attack:
        #    for attack in self.intrinsic_attack:
        #        self.i_attacks.append(IntrinsicAttack(attack))
        self.i_attacks = []
            
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


class Being(Messenger):
    '''The instance of a Species.'''


    __signals__ = [
        Signal('stats_updated', ('stats',)),
        Signal('intrinsics_updated', ('intrinsics',)),
        Signal('condition_added', ('intrinsics',)),
        Signal('condition_cleared', ('intrinsics',)),
    ]

    NORMAL_SPEED = 12
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
        
        Being.guid += 1 #FIXME
        self.guid = Being.guid
        self.species = species
        self.actions = Action.from_being(controller, self) 
        self.is_player = is_player
        self.inventory = BeingInventory(species.genus.usable)
        self.vision = Vision()
        self.value = species.value

        self._wizard = False
        self._direction = None
        hp = Dice(species.level, 8)
        self._stats = {
            'hit_points': hp,
            'max_hit_points': hp,
            'spell_points': 10,
            'vision': 10,
            'turns': 0,
            'experience': 0,
            'movement_points': species.speed
        }
        self._timed_conditions = []
        self._intrinsics = []

    def __str__(self):
        return '{}'.format(self.species.name)

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
            self._timed_condition.remove(r)

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
            or c in self._intrinsics
            or ct in self._timed_conditions
        )

    def clear_condition(self, name):
        c = Condition(name)
        if c not in self._timed_conditions:
            raise KeyError(name)
        self._timed_conditions.remove(c)

    def set_condition(self, name, time):
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
            + self.species.intrinsics
            + self.intrinsics
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
    def max_hit_points(self): 
        return self._stats['hit_points']

    @property
    def hit_points(self): 
        return self._stats['hit_points']
    @hit_points.setter
    def hit_points(self, value): 
        value = max(min(0, value), self._stats['max_hit_points'])
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
    def melee(self): return self.species.melee

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

    @property
    def can_melee(self):
        #FIXME
        return True


          

if __name__ == '__main__':

     human = Species('orc')
     being = Being(None, human)


