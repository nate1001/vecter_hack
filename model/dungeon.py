
from species import Being, Species, PlayerView
from equipment import Inventory
from action import Controller
from generate import LevelGenerator, ObjectGenerator, MonsterGenerator
from ai import AI
from messenger import Messenger, Signal, Event, register_command

from equipment import Light, EquipmentStack, Armor

from pyroguelike.grid import Grid, Flags



class Tile(object):
    '''A container of Beings and Equipment.'''

    class View(object):
        
        def __init__(self, tile):

            self.x = tile.x
            self.y = tile.y
            self.transitions = []

            self.name = tile.tiletype.name
            self.char = tile.tiletype.char
            self.color = tile.tiletype.color
            self.background = tile.tiletype.background
            self.zval = tile.tiletype.zval
            self.is_open = tile.tiletype.is_open
            self.inventory = tile.inventory.view()

            #self.char = player.vision[-1].get_char(tile, wizard)
            #self.color = player.vision[-1].get_color(tile, wizard)
            #self.vision = player.vision[-1].get_state(tile)

            if tile.being:
                self.being = tile.being.view()
            else:
                self.being = None

        def __repr__(self):
            return '<Tile.View ({},{})>'.format(self.x, self.y)


    def distance(self, other):
        x1, y1 = self.x, self.y
        x2, y2 = other.x, other.y
        return ((x2 - x1)**2 + (y2 - y1)**2)**.5

    def __init__(self, tiletype, x, y):

        self.tiletype = tiletype
        self.x = x 
        self.y = y
        self.inventory = Inventory()
        self.being = None
        self.portal = None

        self._permalit = False
        self._lit = False

    def __repr__(self):
        return "<Tile {},{} {} {} >".format(self.x, self.y, 
            self.being and repr(self.being.char) or '', 
            self.inventory and repr(self.inventory.char) or '')

    @property
    def idx(self): return (self.x, self.y)

    @property
    def char(self): return self.tiletype.char

    @property
    def color(self):
        return self.tiletype.color

    @property
    def lit(self):
        return self._permalit or self._lit

    @property
    def light(self):

        lights = []
        if self.being:
            lights.extend(self.being.inventory.get_by_class(Light))
        lights.extend(self.inventory.get_by_class(Light))

        lights = sorted([(es.item.radius, es.item) for es in lights])
        if lights:
            return lights[-1][1]
        return None

    def view(self):
        return self.__class__.View(self)

    #FIXME move to controller
    def move_to(self, being):

        if being.tile:
            being.tile.being = None
        self.being = being
        being.tile = self

    def get_offset(self, other):
        '''Return the offset from another tile.'''

        return (other.x - self.x, other.y - self.y)


    def ontop(self, nobeing=False):
        '''Return the object that can be seen from a birds eye view.'''
        if self.being and nobeing == False:
            return self.being
        elif self.inventory:
            return self.inventory
        else:
            return None

    def distance(self, other):
        x1, y1 = self.idx
        x2, y2 = other.idx
        return ((x2 - x1)**2 + (y2 - y1)**2)**.5



class Level(dict):

    class View(dict):

        def __init__(self, level, wizard=False):

            self.label = level.label
            self.size = level._size

            for tile in level.values():
                self[(tile.x, tile.y)] = tile.view()

        def values(self):
            return self.tiles()

        def tiles(self):
            
            neighbors = {
                'n':  ( 0,-1),
                's':  ( 0, 1),
                'w':  (-1, 0),
                'e':  ( 1, 0),
                'nw': (-1,-1),
                'ne': ( 1,-1), 
                'sw': (-1, 1),
                'se': ( 1, 1),
            }
            t = []
            for y in range(self.size[1]):
                for x in range(self.size[0]):
                    tile = self[x,y]
                    tile.neighbors = {}
                    for direc, off in neighbors.items():
                        tile.neighbors[direc] = self.get((x + off[0], y + off[1]))
                    t.append(tile)
            return t

    def __init__(self, player, tiletypes, grid, label):

        self.label = label
        self._player = player
        self._size = (len(tiletypes[0]), len(tiletypes))
        self._grid = grid
        self._open_tiles = Flags.from_tiles_attr(tiletypes, 'is_open')
        self._torch_map = Flags(self._size)

        for y, row in enumerate(tiletypes):
            for x, tiletype in enumerate(row):
                tile = Tile(tiletype, x, y)
                self[x,y] = tile

    def __repr__(self):
        return "<Level {}>".format(self.label)

    @property
    def staircases_up(self):
        return [t for t in self.itervalues() if t.tiletype.name == 'staircase up']

    @property
    def staircases_down(self):
        return [t for t in self.itervalues() if t.tiletype.name == 'staircase down']
    
    @property
    def beings(self):
        return [t.being for t in self.itervalues() if t.being]

    @property
    def lights(self):
        return [t for t in self.itervalues() if t.light]

    def kill_being(self, being):
        tiles = [t for t in self.itervalues() if t.being is being]
        if len(tiles) != 1:
            raise ValueError(being)
        tiles[0].being = None

    def view(self):
        return self.__class__.View(self)

    def _set_torch_map(self):

        flags = Flags(self._size)
        for tile, light in [(tile, tile.light) for tile in self.lights]:
            f = self._grid.fov(self._open_tiles, tile.idx, light.radius)
            flags = flags | f

        self._torch_map = flags

    def set_fov(self, being):
        
        if being.condition.blind:
            radius = 0
        else:
            radius = being.stats.vision
        
        see = self._grid.fov(self._open_tiles & self._torch_map, being.tile.idx, radius)
        #fov does not set the inside square
        see[being.tile.idx] = True
        being.vision[-1].set_see(see)

    def chase_player(self, monster):

        blocked = Flags(self._size)
        for other in [
            b for b in self.beings 
            if b is not self._player and b is not monster]:
            blocked[other.tile.idx] = True
        
        path = self._grid.get_path(self._open_tiles & ~blocked, self._player.tile.idx, monster.tile.idx)
        if not path:
            return None
        return self[path[0]]

    def get_adjacent(self, tile, offset):
        '''Return the adjacent tile by offset or None.'''

        x, y = tile.x + offset[0], tile.y + offset[1]
        return self.get((x,y))

    def get_all_adjacent(self, tile):
        '''Return all adjacent tiles to this tile.'''
        adj = [ (1,0), (-1,0), (0, -1), (0,1), (1,1), (-1,-1), (1, -1), (-1, 1)]
        return [t for t in [self.get((tile.x + idx[0],tile.y + idx[1])) for idx in adj] if t]

            

class Dungeon(object):

    def __init__(self, game):
        
        self.game = game
        self.levels = None
        self.player = None
        self.controller = None
        self.ai = None

        self._turn_num = None
        self._player_view = None
        self._level_count = None
        self._current_level = None
        self._wizard = None

        self._level_generator = LevelGenerator()
        self._object_generator = ObjectGenerator()
        self._monster_generator = MonsterGenerator()

    def _create_player(self):
        player = Being(self.controller, Species('hacker'), is_player=True)
        player.condition.asleep = False

        torch = EquipmentStack.from_cls(Light, 'torch')
        player.inventory.append(torch)

        armor = EquipmentStack.from_cls(Armor, 'leather armor')
        player.inventory.append(armor)

        return player

    def new(self, wizard):

        self.levels = []
        self.controller = Controller(self)
        self.ai = AI()
        self.player = self._create_player()

        self._player_view = PlayerView(self.player)
        self._level_count = 0
        self._turn_num = 0
        self._wizard = wizard

        self._current_level = self.generate_level()


    @property
    def level_view(self):
        return self._current_level.view()

    @property
    def player_view(self):
        return self._player_view

    def generate_level(self):
        self._level_count += 1

        # generate the tiletypes
        tiles, grid, rooms = self._level_generator.generate( (20,20), 7)
        room_len = len(self._level_generator.rooms)
        level = Level(self.player, tiles, grid, self._level_count)

        # generate the objects
        objects = self._object_generator.generate(room_len, self._level_count)
        self._object_generator.place_objects(objects, level)

        # generate monsters
        monsters = self._monster_generator.generate(self.player, self.controller, self._level_count)
        self._monster_generator.place_monsters(monsters, level)

        # set the player on a up staircase
        tile = level.staircases_up[0]
        tile.being = self.player
        self.player.tile = tile

        self.levels.append(level)
        self._current_level = level

        #housekeeping
        #FIXME this will need to move to change_level
        for being in [b for b in level.beings]:
            being.new_level(level._size)
        self.turn_done(move_monsters=False)

        return level


    def turn_done(self, move_monsters=True):
        
        level = self._current_level
        #housekeeping
        level._set_torch_map()
        level.set_fov(self.player)

        #ai
        if move_monsters:
            monsters = [b for b in level.beings if b is not self.player]
            self.ai.move_monsters(level, self.player, monsters)

        self.game.events['turn_finished'].emit(self._turn_num)
        self._turn_num += 1


    def _move_level(self, being):
        if self.player is not being:
            raise ValueError("monster {} should not being changing levels.".format(being))

        old = being.tile.level
        old_tile = being.tile

        # if we are going back to a previous level
        if being.tile.portal:
            new = being.tile.portal
            new.visited.move_to(being)
        # else make a new level
        else:
            new = self.generate_level()

        being.tile.portal = old
        old_tile.portal = new

        self._current_level = new

        return new


class Game(Messenger):

    __signals__ = [
            Signal('game_started', ('level',)),
            Signal('game_ended', (),),
            Signal('turn_finished', ('turn_number',),),
    ]

    _settings = {
        'wizard': True
    }
    
    def __init__(self):
        super(Game, self).__init__()

        #FIXME
        # hack to get controller events before the instance exists
        #for signal in Controller.__signals__:
        #    self.events[signal.name] = None

        self.player = None
        #import late so we do not have to worry about file order
        from model.messenger import registered_commands
        self.commands = registered_commands

    def set_setting(self, setting, value):
        self._settings[setting] = value
        #FIXME
        #if setting == 'wizard':
        #    self._dungeon._wizard = value

    @property
    def settings(self):
        return self._settings.copy()


    @register_command('game', 'New', 'ctrl+n')
    def new(self):

        dungeon = Dungeon(self)
        dungeon.new(self._settings['wizard'])

        #FIXME controller events will be available until a new game has started
        for event in dungeon.controller.events.values():
            self.events[event.name] = event

        self.player = dungeon.player_view
        self.events['game_started'].emit(dungeon.level_view)

        return True

    def die(self):
        self.events['game_ended'].emit()

        

        
            
if __name__ == '__main__':
    
    game = Game()
