
from collections import OrderedDict

from attr_reader import AttrConfig
from action import Action, registered_actions_types
from equipment import Inventory
from messenger import Messenger, Signal, Event
from tile import TileType

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

    )
    '''Factory class for grouping common Species attributes.'''

    def __init__(self, name):
        super(Genus, self).__init__(name)

        for action in self.actions:
            if action.lower() not in [a.__name__.lower() for a in registered_actions_types]:
                raise ValueError("Genus %s does not have a registered action type for %s" %
                     (repr(name), repr(action.lower())) )

class Species(AttrConfig):
    attrs = (
        ('genus', 'text'),
        ('color', 'qtcolor'),

        ('hit points', 'int'),
        ('ac', 'int'),
        ('melee', 'dice'),
    )
    ''' Factory class for initializing monsters.'''

    def __init__(self, name):
        super(Species, self).__init__(name)
        self.genus = Genus(self.genus)

    def __repr__(self):
        return "<Species {}>".format(repr(self.name))

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return not self == other

    @property
    def value(self):
        return self.hit_points + self.ac + self.melee.mean


class Stats(Messenger):
    '''Holds the value of Being attribues such as hit points.'''

    __signals__ = [
        Signal('stats_updated', ('stats',)),
        Signal('intrinsics_updated', ('intrinsics',)),
    ]
    
    base_intrinsics = {
        'strength':     10,
        'intellect':    10,
        'wisdom':       10,
        'dexterity':    10,
        'constitution': 10,
        'charisma':     10,
    }

    base_items = [
        'ac',
        'melee',
        'infravision',
        'vision',
        'hit_points',
        'regenerate',
        'spell_points',
    ]

    display = [
        'hp',
        #'sp',
        'melee',
        'ac',
        'experience',
        'gold',
        'turns',
    ]

    hit_point_regen = .10

    def __init__(self, species):
        super(Stats, self).__init__()

        # Impliment strength, intellect, wisdom, dexterity, consitution, charisma
        # hp, maxhp, gold, ac, exp, sp, maxsp
        # turns, speed

        self._intrinsics = OrderedDict()
        for key in self.base_intrinsics:
            self._intrinsics[key] = self.base_intrinsics[key] + (getattr(species.genus, key) or 0)

        self._items = OrderedDict()
        self._base= OrderedDict()

        for key in self.base_items:
            if hasattr(species, key):
                value = getattr(species, key)
            else:
                value = getattr(species.genus, key)
            self._items[key] = value
            self._base[key] = value

        self._items['turns'] = 0
        self._items['experience'] = 0
        self._items['gold'] = 0
        
    @property
    def items(self):
        d = OrderedDict()
        for key in self.display:
            d[key] = getattr(self, key)
        return d

    @property
    def intrinsics(self):
        d = OrderedDict()
        for key in self._intrinsics:
            d[key] = self._intrinsics[key]
        return d
    
    @property
    def hp(self): 
        hp = self._items['hit_points']
        maxhp = self._base['hit_points']
        return '{}/{}'.format(hp, maxhp)

    @property
    def sp(self): 
        sp = self._items['spell_points']
        maxsp = self._base['spell_points']
        return '{}/{}'.format(sp, maxsp)

    @property
    def hit_points(self): 
        return self._items['hit_points']
    @hit_points.setter
    def hit_points(self, value): 
        if value < 0:
            value = 0
        elif value > self._base['hit_points']:
            value = self._base['hit_points']

        self._items['hit_points'] = value
        self.events['stats_updated'].emit(self.items)

    @property
    def turns(self): return self._items['turns']
    @turns.setter
    def turns(self, value): 
        self._items['turns'] = value

        if not value % self._base['regenerate']:
            self.hit_points += int(self._base['hit_points'] * self.hit_point_regen) or 1
        self.events['stats_updated'].emit(self.items)

    @property
    def experience(self): return self._items['experience']
    @experience.setter
    def experience(self, value):
        self._items['experience'] = value
        self.events['stats_updated'].emit(self.items)

    @property
    def ac(self): return self._items['ac']
    @property
    def melee(self): return self._items['melee']
    @property
    def infravision(self): return self._items['infravision']
    @property
    def vision(self): return self._items['vision']
    @property
    def gold(self): return self._items['gold']

    def _use_equip(self, equip, remove):

        d = {}
        for stat in self._items:
            if hasattr(equip, stat):
                d[stat] = getattr(equip, stat)

        for stat, value in d.items():
            # if its a bonus
            if type(value) is int and not remove:
                self._items[stat] +=  value
            elif type(value) is int:
                self._items[stat] -=  value

            elif not remove:
                self._items[stat] = value
            else:
                self._items[stat] = self._base[stat]
        if d:
            self.events['stats_updated'].emit(self.items)

    def add_equip(self, equip):
        self._use_equip(equip, False)
    def remove_equip(self, equip):
        self._use_equip(equip, True)

        

class Condition(Messenger):
    __signals__ = [
        Signal('condition_updated', ('new condition',)),
    ]

    def __init__(self, being):

        super(Condition,  self).__init__()

        self._can_see = being.species.genus.vision > 0

        self._items = OrderedDict()
        self._items['asleep'] = True
        self._items['blind'] = None

        self.blind = False


    @property
    def asleep(self): return self._items['asleep']
    @asleep.setter
    def asleep(self, is_asleep):
        self._items['asleep'] = is_asleep

    @property
    def blind(self): return self._items['blind']
    @blind.setter
    def blind(self, is_blind):
        self._items['blind'] = is_blind

class Vision(object):
    
    def __init__(self):
        
        self._levels = []
        self._current = None
        self._wizard = False

    def append_level(self, size):
        print 102, self._wizard
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
    def can_see_other(self, other): return self._current.can_see_other(other)
    def can_sense_other(self, other): return self._current.can_sense_other(other)

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







class Using(Messenger):
    #FIXME figure out better way to seperate views from actual items

    __signals__ = [
        Signal('using_updated', ('items',)),
    ]
    
    def __init__(self, usable, stats):
        super(Using,  self).__init__()

        self._stats = stats
        self._items = OrderedDict()
        for key in usable:
            self._items[key] = None

    @property
    def items(self):
        '''Items that are being worn and slots that could be worn.'''

        d = OrderedDict()
        for key, item in self._items.items():
            d[key] = item
        return d

    @property
    def in_use(self):
        '''Items that are being worn.'''
        d = OrderedDict()
        for key, item in self._items.items():
            if item:
                d[key] = item
        return d

    def could_use(self, inventory):
        '''Items that may be worn (could replace what is already being worn.)'''
        usable = []
        for stack in inventory:
            if stack.item.usable in self._items.keys():
                usable.append(stack)
        return usable
    
    def _get_item(self, idx):
        return self.in_use.values()[idx]

    def _remove_item(self, stack):
        
        if stack is None:
            raise ValueError(stack)

        ok = False
        for key, value in self.in_use.items():
            if stack is value:
                ok = True
                self._stats.remove_equip(stack.item)
                self._items[key] = None
                self.events['using_updated'].emit(self.items)
        return ok

    def _add_item(self, stack):
        if stack.usable not in self._items.keys():
            return False

        old = self._items[stack.usable]

        self._items[stack.usable] = stack
        self._stats.add_equip(stack.item)
        self.events['using_updated'].emit(self.items)
        return True



class PlayerView(Messenger):

    def __init__(self, player):

        super(PlayerView, self).__init__()
        
        self.name = player.species.name
        self.color = player.species.color
        self.char = player.species.genus
        self._stats = player.stats
        self._inventory = player.inventory
        self._using = player.using
        self._player_id = id(player)
        self._actions = player.actions
        self._vision = player.vision

        # expose events to this class
        events = (
            player.actions.events.values()
            + player.stats.events.values()
            + player.inventory.events.values()
            + player.using.events.values()
        )
        for event in events:
            self.events[event.name] = event

    @property
    def vision(self):
        return self._vision

    @property
    def stats(self):
        return self._stats

    @property
    def inventory(self):
        return self._inventory

    @property
    def using(self):
        return self._using

    def dispatch_command(self, name):
        
        method = getattr(self._actions, name)
        status = method()

        # has to return something (False - action failed / True action succeeded)
        if status is None:
            raise ValueError("callback {} returned None.".format(name))

        # else its information
        else:
            return status

    def emit_info(self):
        self.events['inventory_updated'].emit(self.inventory.items)
        self.events['using_updated'].emit(self._using.items)
        self.events['stats_updated'].emit(self.stats.items)
        self.events['intrinsics_updated'].emit(self.stats.intrinsics)


class Being(object):
    '''The instance of a Species.'''

    guid = 0

    class View(object):
        
        def __init__(self, being):

            self.is_player = being.is_player
            self.color = being.species.color
            self.char = being.species.genus.ascii
            self.category = being.species.genus.name
            self.name = being.species.name
            self.guid = being.guid

        def __str__(self):
            return '<Being.View {}>'.format(self.name)

    def __init__(self, controller, species, is_player=False):
        
        Being.guid += 1 #FIXME
        
        self.guid = Being.guid
        self.species = species
        
        self.controller = controller
        self.is_player = is_player
        self.stats = Stats(species)
        self.inventory = Inventory()
        self.using = Using(species.genus.usable, self.stats)
        self.condition = Condition(self)
        self.vision = Vision()
        self.value = species.value
        self._wizard = False

        self.actions = Action.from_being(self) 
        self.tile = None

    def __repr__(self):
        return "<Being {}{}>".format(self, self.tile and ' on {},{}'.format(self.tile.x, self.tile.y) or '(no tile)')

    def __str__(self):
        return '#{} {}'.format(self.guid, self.species.name)

    @property
    def wizard(self): return self._wizard
    @wizard.setter
    def wizard(self, is_wizard):
        print 99, is_wizard
        self.vision.wizard = is_wizard
        self._wizard = is_wizard

    @property
    def is_dead(self):
        return self.stats.hit_points < 1

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
    def can_see(self):
        return not self.condition.blind

    def new_level(self, size):
        self.vision.append_level(size)

    def view(self):
        return self.__class__.View(self)

    #FIXME
    def can_move(self):
        return True

    #FIXME
    def can_melee(self):
        return True

          

if __name__ == '__main__':

     human = Species('orc')
     being = Being(None, human)
     print dir(being.actions)


