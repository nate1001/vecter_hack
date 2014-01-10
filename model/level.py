
from pyroguelike.flags import Flags
from pyroguelike.grid import Grid
from tile import Tile
from config import logger

class Level(dict):

    neighbors = {
      ( 0,-1):  'n',  
      ( 0, 1):  's',  
      (-1, 0):  'w',  
      ( 1, 0):  'e',  
      (-1,-1):  'nw', 
      ( 1,-1):  'ne',  
      (-1, 1):  'sw', 
      ( 1, 1):  'se', 
    }

    class View(dict):

        def __init__(self, level):

            self.label = level.label
            self.size = level._size

            for tile in level.values():
                self[(tile.x, tile.y)] = tile.view(level._player)

        def values(self):
            return self.tiles()

        def tiles(self):
            
            t = []
            for y in range(self.size[1]):
                for x in range(self.size[0]):
                    tile = self[x,y]
                    tile.neighbors = {}
                    for off, direc in Level.neighbors.items():
                        tile.neighbors[direc] = self.get((x + off[0], y + off[1]))
                    t.append(tile)
            return t

    def __init__(self, player, tiletypes, label):

        self.label = label
        self._player = player
        self._size = (len(tiletypes[0]), len(tiletypes))
        self._grid = Grid(self._size)
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
        tiles = [t for t in self.values() if t.being is being]
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
        
        tile = self.tile_for(being)
        see = self._grid.fov(self._open_tiles & self._torch_map, tile.idx, radius)
        #fov does not set the inside square
        see[tile.idx] = True
        being.vision.set_see(see)

    def add_being(self, tile, being):
        tile.being = being
        being.direction = 'sw'
        being.new_level(self._size)

    def move_being(self, tile, being):
        old = self.tile_for(being)
        old.being = None
        if old is tile:
            raise ValueError(tile)
        tile.being = being

        o = old.get_offset(tile)
        direc = Level.neighbors[o]
        being.direction = direc

    def direction_from(self, being, tile):
        old = self.tile_for(being)
        of = old.get_offset(tile)
        return Level.neighbors[of]

    def tile_for(self, being):
        tiles = [t for t in self.values() if t.being is being]
        if len(tiles) != 1:
            logger.error('tiles %s length != 1', tiles)
            raise KeyError(tiles)
        return tiles[0]

    def being_distance(self, being, other):
        x1, y1 = self.tile_for(being).idx
        x2, y2 = self.tile_for(other).idx
        return ((x2 - x1)**2 + (y2 - y1)**2)**.5

    def chase_player(self, monster):

        blocked = Flags(self._size)
        for other in [
            b for b in self.beings 
            if b is not self._player and b is not monster]:
            t = self.tile_for(other)
            blocked[t.idx] = True
        
        p = self.tile_for(self._player)
        m = self.tile_for(monster)
        path = self._grid.get_path(self._open_tiles & ~blocked, p.idx, m.idx)
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

