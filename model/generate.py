'''
Generation classes for create levels, beings, objects etc...

Level generation depends on tile type names from AttrReader and data/tiletype.cfg.
'''

from operator import itemgetter
from random import randint, choice, normalvariate, random
from collections import OrderedDict

from attr_reader import AttrReader
from tiletype import TileType, TileTypeCategory
from equipment import equipment_classes, EquipmentStack
from being import Species, Being
from pyroguelike.grid import Grid, Flags
from config import logger, direction_by_name

class Door(object):
    kinds = [
        t for t in AttrReader.items_from_klass(TileTypeCategory) 
        if t.is_door
        ### XXX remember to remove
        and not t.is_locked
        ###
    ]
    tiletypes = [
        d for d in AttrReader.items_from_klass(TileType) 
        if d.direction
        and d.category in [k.name for k in kinds]
    ]
    @classmethod
    def generate(cls, direction):
        kind = choice(cls.kinds)
        types = [
            t for t in cls.tiletypes 
            if t.direction == direction
            and t.category == kind.name
        ]
        #should only be 1 type picked
        if len(types) != 1:
            raise ValueError(types)
        return types[0]

class Room(object):
    '''A room with size, position, walls, and doors.'''
    min_size = (3,3)
    max_size = (7,7)

    walls = {
        'east': TileType('east wall'),
        'west': TileType('west wall'),
        'north': TileType('north wall'),
        'south': TileType('south wall'),
        'nw': TileType('nw wall'),
        'ne': TileType('ne wall'),
        'sw': TileType('sw wall'),
        'se': TileType('se wall'),
    }
    floor = TileType('floor')

    @classmethod
    def from_x_y(cls, x, y, label=None, min_size=min_size, max_size=max_size):
        '''Generate a randomly sized.'''
        minw, minh = min_size
        maxw, maxh = max_size
        size = (
            int(random() * (maxw-minw) + minw),
            int(random() * (maxh-minh) + minh), 
        )
        return Room(size, x, y, label=label)

    def __init__(self, size, x, y, label=None):
        # 4th quadrant
        self._x = x
        self._y = y
        self._size = size
        self._tiletypes = {}
        self.label = label
        self.connected_to = []

        w, h = size
        for j in range(h):
            for i in range(w):
                if i == 0 and j == 0:
                    self._tiletypes[i,j] = self.walls['nw']
                elif i == 0 and j == h-1:
                    self._tiletypes[i,j] = self.walls['sw']
                elif i == w-1 and j == h-1:
                    self._tiletypes[i,j] = self.walls['se']
                elif i == w-1 and j == 0:
                    self._tiletypes[i,j] = self.walls['ne']
                elif i == 0:
                    self._tiletypes[i,j] = self.walls['west']
                elif i == w-1:
                    self._tiletypes[i,j] = self.walls['east']
                elif j == 0:
                    self._tiletypes[i,j] = self.walls['north']
                elif j == h-1:
                    self._tiletypes[i,j] = self.walls['south']
                else:
                    self._tiletypes[i,j] = self.floor

        # add doors
        # take away corners
        idxs = (
            ('north',(randint(1, i-1),   0)),
            ('west', (0,                 randint(1, j-1))),
            ('south',(randint(1, i-1),   j)),
            ('east', (i,                randint(1, j-1))),
        )
        for direction, (x,y) in idxs:
            self._tiletypes[x,y] = Door.generate(direction)

    def __str__(self):
        return "<Room {} {}x{} ({},{})>".format(repr(self.label), self.size[0], self.size[1], self.nw[0], self.nw[1])

    def __getitem__(self, idx):
        x, y = idx
        return self._tiletypes[x-self._x, y-self._y]

    def string(self):
        s = ''
        for y in range(self._size[1]):
            for x in range(self._size[0]):
                s += self._tiletypes[x,y].char
            s+='\n'
        s+='\n'
        return s

    def keys(self):
        return [(x+self._x, y+self._y) for (x,y) in self._tiletypes]

    def values(self):
        items = []
        for y in range(self._size[1]):
            for x in range(self._size[0]):
                items.append(self._tiletypes[x,y])
        return items

    @property
    def nw(self): return self._x, self._y
    @property
    def ne(self): return self._x + self._size[0]-1, self._y
    @property
    def se(self): return self._x + self._size[0]-1, self._y + self._size[1]-1
    @property
    def sw(self): return self._x, self._y + self._size[1]-1
    @property
    def size(self):
        return self._size
    @property
    def doors(self):
        return [(x+self._x, y+self._y) for x,y in self._tiletypes.keys() if self._tiletypes[x,y].is_door]


    def intersect(self, other):
        'Returns whether another door overlaps with this one.'''
        left = self.nw[0]
        right = self.ne[0]
        top  = self.nw[1]
        bottom = self.sw[1]

        oleft = other.nw[0]
        oright = other.ne[0]
        otop  = other.nw[1]
        obottom = other.sw[1]
        return (left < oright and right > oleft and top < obottom and bottom > otop)

    def is_close(self, other, distance):
        '''Returns whether another room is close within a distance.'''
        distance = 3
        x, y = self.nw
        w, h = self.size
        new = Room((w+distance*2, h+distance*2), x-(distance), y-(distance))
        return new.intersect(other)

                

class LevelGenerator(object):
    '''Generates tile types that form connected rooms.'''

    path = TileType('path')
    rock = TileType('rock')
    undecided = TileType('undecided')
    stairs_up = TileType('staircase up')
    stairs_down  = TileType('staircase down')

    def string(self, tiles):
        s = ''
        for y, row in enumerate(tiles):
            s += '\n'
            for x, tile in enumerate(row):
                #rooms = [r for r in self.rooms if r.nw == (x,y)]
                #if rooms and rooms[0].label:
                #    s += rooms[0].label
                #else:
                s += tile.char
        return s

    def __init__(self, min_room_distance=1):
        self.min_room_distance=min_room_distance

    def generate(self, size, min_rooms, room_tries=50, level_tries=500):
        '''Returns a sequence of tile types.'''

        room_fail_max = 50
        w, h = size
        
        # While in the loop: 
        # First, generate a room then try to place it randomly.
        # It will not always work as room may fall off map or it will intersect  with another room. 
        # After we have done this X room tries.
        # See if we have a the minimum amount of rooms.
        # If not wipe the tiles and try again.
        # Once we have min room amount connect rooms, place stairs and remove uneaded doors

        while level_tries > 0:
            tiles, rooms = [], []
            #Initalize empty list
            for y in range(h):
                tiles.append([])
                for x in range(w):
                    tiles[-1].append(self.undecided)

            logger.debug('trying to generate rooms ...')
            r = room_tries
            #try to place rooms on the level
            while r > 0:
                room = self._generate_room(tiles, rooms, size)
                if room:
                    rooms.append(room)
                r -= 1
            # if we have enough rooms 
            if len(rooms) >= min_rooms:
                break
            level_tries -= 1

        if len(rooms) < min_rooms:
            raise ValueError('Could not generate level')
        if not self._connect_rooms(tiles, rooms, size):
            raise ValueError('could not connect level')

        #mark unused tiles as rock
        for y in range(h):
           for x in range(w):
                if tiles[y][x] == self.undecided:
                    tiles[y][x] = self.rock

        self._fix_doors(tiles, rooms)
        self._place_stairs(tiles, rooms)
        return tiles, rooms

    def _generate_room(self, tiles, rooms, size):

        # generate a random room
        w, h = size
        mw, mh = Room.min_size
        x, y = (
            int(random()*(w-mw)), 
            int(random()*(h-mh))
        )
        room = Room.from_x_y(x, y, label=str(len(rooms)+2))

        # if were off the grid
        if room.nw[0] < 0 or room.nw[1] < 0 or room.se[0] >= w or room.se[1] >= h:
            return None

        # if we are too close to other rooms
        for other in rooms:
            if room.is_close(other, self.min_room_distance):
                return None

        #add the room to level
        for x,y in room.keys():
            tiles[y][x] = room[x,y]
        return room

    def _fix_doors(self, tiles, rooms):

        offsets = ((-1, -1), (1, 1), (-1, 1), (1, -1), (1, 0), (-1, 0), (0, 1), (0, -1),)
        for room in rooms:
            for x,y in room.doors:
                found = False
                # check if there is passages by the door
                for xo,yo in offsets:
                    try:
                        if tiles[y+yo][x+xo] == self.path:
                            found = True
                            break
                    except IndexError:
                        pass

                if not found:
                    #TODO this would be a good place to add fake passages
                    # if no passages; turn it back to a wall
                    if not found:
                        direction = tiles[y][x].direction
                        tiles[y][x] = Room.walls[direction]
                else:
                    # make sure there is a path one tile directly outside the door
                    # (in case the path came in at diagnal)
                    d = direction_by_name[tiles[y][x].direction]
                    ny, nx = y+d.offset[1], x+d.offset[0]
                    if tiles[ny][nx] != self.path:
                        tiles[ny][nx] = self.path

    def _connect_room(self, tiles, grid, reachable, room, other):

        if room is other:
            raise ValueError()

        door = choice(room.doors)
        other_door = choice(other.doors)
        path = grid.get_path(reachable, door, other_door)
        if not path:
            return False
        # change open tiles to paths
        for x, y in path:
            if tiles[y][x] == self.undecided:
                tiles[y][x] = self.path
        return True

    def _connect_rooms(self, tiles, rooms, size):
        grid = Grid(size)
        open = Flags.from_tiles_attr(tiles, 'is_open')
        doors = Flags.from_tiles_attr(tiles, 'is_door')
        reachable = open | doors
        S, T = rooms[:], []
        current = rooms[0]
        while S:
            neighbor = S[-1]
            if neighbor not in T:
                S.remove(neighbor)
                T.append(neighbor)
                if not self._connect_room(tiles, grid, reachable, current, neighbor):
                    return False
                current = neighbor
        return True

    def _place_stairs(self, tiles, rooms):
   
        up = choice(rooms)
        down = choice([r for r in rooms if r is not up])
        for room, kind in [(up, self.stairs_up), (down, self.stairs_down)]:
            x,y = choice([idx for idx in room.keys() if tiles[idx[1]][idx[0]] == Room.floor])
            tiles[y][x] = kind


class BaseGenerator(object):
    '''Assigns percentages of object generation.'''

    def weighted_dist(self, items, exponential=1):
        '''Returns a dictionary of probabilities of what an item should randomly generate.

        Probabilities shall sum to 1.

        Weights are based on item.value attribute and are relative to each other. If a value 
        is higher than another's it will have less probability. If exponential is used the items
        value attribute will be raised to that power before the distribution is calculated (Giving
        higher values of much smaller probability if exponential>1.)
        '''

        #XXX there seems to no way to distinguish from classes and instances

        weights = OrderedDict()
        values = [i[1] for i in items]
        if exponential:
            values = [v**exponential for v in values]

        s = sum(v for v in values)
        n = len(values)
        avg = s / float(n)
        sum_weight = sum([(avg / v) for v in values])

        new = []
        for idx, item in enumerate(items):
            weight = (avg / values[idx])
            weighted_percent = weight / sum_weight
            new.append((weighted_percent, item[0]))

        for w, i in sorted(new):
            weights[i] = w

        check = sum([w for w in weights.itervalues()])
        if round(check, 1) != 1:
            raise ValueError(check)

        return weights

    def pick_from_weights(self, items):
        '''Given a weighted distribution randomly pick an item from it.'''
        
        if round(sum([x for x in items.itervalues()]), 1) != 1.:
            raise ValueError('numbers do not add to 1')

        r = random()
        total = 0.
        pick = None
        for item, percent in items.iteritems():
            total += percent
            if r <= total:
                pick = item
                break
        if not pick:
            raise ValueError()
        return pick

    def generate(self, depth):
        '''Generate a sequence of items.'''
        raise NotImplementedError


class SpeciesGenerator(BaseGenerator):
    
    base_mean = 10
    base_std_dev = 3

    def __init__(self):

        items = [i for i in AttrReader.items_from_klass(Species) if not i.nogenerate]
        self.weights = self.weighted_dist([(i, i.value) for i in items])

    def generate_level(self, depth):

        l = []
        n = max(int(normalvariate(self.base_mean, self.base_std_dev)), 0)
        for i in range(n):
            # pick the object from the class
            species = self.generate(depth)
            l.append(species)
        return l

    def generate(self, depth):
        return self.pick_from_weights(self.weights)

    def place_beings(self, monsters, level):

        tiles = [t for t in level.itervalues() if t.tiletype.is_open]
        for monster in monsters:
            tile = choice(tiles)
            level.add_being(tile, monster)
        return monsters


class ObjectGenerator(BaseGenerator):

    def __init__(self):
        
        # distribution of different equipment classes
        self.klass_weights = self.weighted_dist([(i, i.value) for i in equipment_classes])
        # distribution of items within an equipment class

        self.object_weights = {}
        for klass in self.klass_weights:
            items = AttrReader.items_from_klass(klass)
            self.object_weights[klass] = self.weighted_dist([(i, i.value) for i in items])

    def place_objects(self, objects, level):
        tiles = [t for t in level.itervalues() if t.tiletype.is_open]

        for o in objects:
            tile = choice(tiles)
            tile.inventory.append(o)

    def generate(self, room_num, depth):

        objects = []
        n = int(normalvariate(room_num, room_num / 5.))
        for i in range(n):
            # pick class of object
            klass = self.pick_from_weights(self.klass_weights)

            # pick the object from the class
            item = self.pick_from_weights(self.object_weights[klass])
            equipment = EquipmentStack.from_item(item.clone())
            objects.append(equipment)

        return objects


if __name__ == '__main__':
    
    import sys
    generator = LevelGenerator()
    tiles, rooms = generator.generate((20,20), 5)
    sys.stdout.write(generator.string(tiles) + '\n')

    sys.exit(0)

    room = Room((3,5), 1,1)
    sys.stdout.write(str(room) + '\n')

    generator = ObjectGenerator()
    objects = generator.generate(10, 0)
    sys.stdout.write(str(objects) + '\n')

    generator = SpeciesGenerator()
    species = generator.generate(10)
    sys.stdout.write(str(species) + '\n')




    
