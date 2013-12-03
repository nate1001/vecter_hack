
from operator import itemgetter
from random import randint, choice, normalvariate, random
from collections import OrderedDict

from attr_reader import AttrReader
from tile import TileType
from equipment import equipment_classes, EquipmentStack
from species import Species, Being
from pyroguelike.grid import Grid, Flags
from config import logger



class Room(object):
    min_size = (3,3)
    max_size = (7,7)

    def __init__(self, size, x, y, label=None):
        # 4th quadrant
        self.label = label
        self.size = size
        xo, yo = size[0], size[1]
        self.nw = x, y
        self.ne = x+xo, y
        self.se = x+xo, y+yo
        self.sw = x, y+yo
        self.connected_to = []

        # take away corners
        xo, yo = xo-1, yo-1

        self.door_n = (randint(x+1, x+xo-1), y)
        self.door_s = (randint(x+1, x+xo-1), y+yo+1)
        self.door_w = (x, randint(y+1, y+yo-1))
        self.door_e = (x+xo+1, randint(y+1, y+yo-1))

    def __str__(self):
        return "<Room {} {}x{} ({},{})>".format(repr(self.label), self.size[0], self.size[1], self.nw[0], self.nw[1])

    @classmethod
    def from_x_y(cls, x, y, label=None, min_size=min_size, max_size=max_size):
        minw, minh = min_size
        maxw, maxh = max_size
        size = (
            int(random() * (maxw-minw) + minw),
            int(random() * (maxh-minh) + minh), 
        )
        return Room(size, x, y, label=label)
    
    @property
    def doors(self):
        return (self.door_n, self.door_s, self.door_w, self.door_e)

    def get_door_wall(self, door):
        if door == self.door_n:
            return 'north wall'
        elif door == self.door_s:
            return 'south wall'
        elif door == self.door_w:
            return 'west wall'
        elif door == self.door_e:
            return 'east wall'
        else:
            raise ValueError()

    def get_tiletype(self, point):

        if self.is_door(point):
            if point == self.door_n:
                kind = 'north door'
            elif point == self.door_s:
                kind = 'south door'
            elif point == self.door_w:
                kind = 'west door'
            elif point == self.door_e:
                kind = 'east door'
            else:
                raise ValueError(point)

        elif point == self.nw:
            kind = 'nw wall'
        elif point == self.ne:
            kind = 'ne wall'
        elif point == self.sw:
            kind = 'sw wall'
        elif point == self.se:
            kind = 'se wall'

        elif self.is_north_wall(point):
            kind = 'north wall'
        elif self.is_south_wall(point):
            kind = 'south wall'
        elif self.is_west_wall(point):
            kind = 'west wall'
        elif self.is_east_wall(point):
            kind = 'east wall'

        # else were in inside of the room
        #FIXME check if were in the room
        else:
            kind = 'floor'
        return kind
    
    def intersect(self, other):
        left = self.nw[0]
        right = self.ne[0]
        top  = self.nw[1]
        bottom = self.sw[1]

        oleft = other.nw[0]
        oright = other.ne[0]
        otop  = other.nw[1]
        obottom = other.sw[1]
        return (left < oright and right > oleft and top < obottom and bottom > otop)

    
    def is_close(self, other, tiles, pixels):
        
        x, y = self.nw
        w, h = self.size
        new = Room((w+pixels, h+pixels), x-(pixels/2), y-(pixels/2))
        return new.intersect(other)

    def is_door(self, point):
        if point in [self.door_n, self.door_s, self.door_w, self.door_e]:
            return True
        return False
    
    def iter_index(self):
        return [(x,y) 
            for y in range(self.nw[1], self.sw[1]) 
            for x in range(self.nw[0], self.ne[0])]
                

    #XXX functions below return true on corners
    def _is_wall(self, point, corner, idx):
        x, y = point
        if self.is_door(point):
            return False
        if idx == 1:
            return corner[1] == y
        elif idx == 0:
            return corner[0] == x
        else:
            raise ValueError(idx)

    def is_north_wall(self, point):
        return self._is_wall(point, self.nw, 1)
    def is_south_wall(self, point):
        return self._is_wall(point, self.sw, 1)
    def is_west_wall(self, point):
        return self._is_wall(point, self.nw, 0)
    def is_east_wall(self, point):
        return self._is_wall(point, self.se, 0)


class LevelGenerator(object):

    min_room_distance = 3

    #reuse TileType so we do not have too much object creation overhead
    tiletypes = {}
    for name in AttrReader('tiletype', TileType.attrs).read().keys():
        tiletypes[name] = TileType(name)
    

    def __str__(self):
        s = ''
        for y, row in enumerate(self.tiles):
            s += '\n'
            for x, tile in enumerate(row):
                rooms = [r for r in self.rooms if r.nw == (x,y)]
                if rooms and rooms[0].label:
                    s += rooms[0].label
                else:
                    s += tile.char
        return s

                    
    def generate(self, size, min_rooms):
        
        self.size = size
        self.min_rooms = min_rooms
        

        # While in the loop: 
        # First, generate a room then try to place it randomly.
        # It will not always work as room may fall off map or it will intersect
        # with another room. Keep going in the while loop until we get the 
        # mininum room number for the level. Once we have the rooms, get all
        # them connected, and then finaly place the stairs.


        dungeon_try_max = 100
        dungeon_tries = 0
        w, h = size
        while True:

            dungeon_tries += 1
            self.tiles = []
            self.rooms = []
            for y in range(h):
                self.tiles.append([])
                for x in range(w):
                    self.tiles[-1].append(self.tiletypes['undecided'])
            self.grid = Grid(self.size)

            room_fail_max = 50
            tries, count = 0,0

            while True:
                tries += 1
                x, y = int(random()*w), int(random()*h)
                room = Room.from_x_y(x, y, label=str(count))
                ok = self._place_room(room)

                if ok:
                    count += 1
                    self.rooms.append(room)

                if count >= self.min_rooms or tries > room_fail_max:
                    if tries > room_fail_max:
                        logger.debug('Could not place rooms ...')
                    break

            if count >= self.min_rooms:

                # if we can connect all the rooms were done
                ok = self._connect_rooms()
                if ok:
                    logger.debug('Succeeded in placing rooms.')
                    break

                logger.debug('Could not connect rooms.')

            if dungeon_tries > dungeon_try_max:
                raise ValueError(dungeon_tries)


        self._place_stairs()
   
        tiles = {}

        # cleanup
        self._fix_doors()
        for y in range(self.size[1]):
           for x in range(self.size[0]):
                if self.tiles[y][x] == self.tiletypes['undecided']:
                    self.tiles[y][x] = self.tiletypes['rock']
                tiles[(x,y)] = self.tiles[y][x]
   
        return self.tiles, self.grid, self.rooms

    def _fix_doors(self):

        # replace unused doors with walls
        offsets= {
            'north wall': ( (0,-1), (-1,-1), (1,-1) ),
            'south wall': ( (0,1), (-1,1), (1,1) ),
            'west wall': ( (-1,0), (-1,1), (-1,-1) ),
            'east wall': ( (1,0), (1,1), (1,-1) ),
        }
        for room in self.rooms:
            for door in room.doors:
                wall = room.get_door_wall(door)
                os = offsets[wall]
                found = False
                # check if there is passages by the door
                for o in os:
                    try:
                        if self.tiles[door[1]+o[1]][door[0]+o[0]] == self.tiletypes['path']:
                            self.tiles[door[1]+os[0][1]][door[0]+os[0][0]] = self.tiletypes['path']
                            found = True
                            break
                    except IndexError:
                        pass
                #TODO this would be a good place to add fake passages
                # if no passages; turn it back to a wall
                if not found:
                    self.tiles[door[1]][door[0]] = self.tiletypes[wall]

    def _connect_room(self, reachable, room, other):

        if room is other:
            raise ValueError()

        door = choice([d for d in room.doors])
        other_door = choice([d for d in other.doors])

        path = self.grid.get_path(reachable, door, other_door)
        if not path:
            return False

        # change open tiles to paths
        for x, y in path:
            if self.tiles[y][x] == self.tiletypes['undecided']:
                self.tiles[y][x] = self.tiletypes['path']

        return True

    def _connect_rooms(self):

        reachable = Flags.from_tiles_attr(self.tiles, 'is_open')
        S, T = self.rooms[:], []
        current = self.rooms[0]

        while S:
            neighbor = S[-1]
            if neighbor not in T:
                S.remove(neighbor)
                T.append(neighbor)
                if not self._connect_room(reachable, current, neighbor):
                    return False
                current = neighbor

        return True


    def _place_room(self, room):

        # if were off the grid
        w, h = self.size
        if room.nw[0] < 0 or room.nw[1] < 0 or room.se[0] >= w or room.se[1] >= h:
            return False

        # if were too close to other rooms
        for other in [r for r in self.rooms if r is not room]:
            if room.is_close(other, self.tiles, self.min_room_distance):
                return False

        w, h = room.size
        x, y = room.nw
        for yo in range(h + 1):
            for xo in range(w + 1):
                nx, ny = (x + xo, y + yo)
                # if we collided with a room / should not get here (is_close should find it)
                if self.tiles[ny][nx] != self.tiletypes['undecided']:
                    raise ValueError()
                # reset to proper wall type etc..
                self.tiles[ny][nx]= self.tiletypes[room.get_tiletype((nx, ny))]

        return True
    
    def _place_stairs(self):
   
        up = choice(self.rooms)
        down = choice([r for r in self.rooms if r is not up])

        for room, kind in [(up, 'staircase up'), (down, 'staircase down')]:
            idxs = room.iter_index()
            stair = choice([idx for idx in idxs if self.tiles[idx[1]][idx[0]] == self.tiletypes['floor']])
            self.tiles[stair[1]][stair[0]] = self.tiletypes[kind]


class BaseGenerator(object):

    def weighted_dist(self, items, exponential=1):
        "weighted_dist( [(item, value),...] )"
        
        # weights are based on items.value attr
        # returns dict of slices of percentage of what an item should randomly generate

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


class MonsterGenerator(BaseGenerator):
    
    base_mean = 10
    base_std_dev = 3

    def generate(self, player, controller, depth):

        # we cant do this in init because the dungeon will not know the player in its init
        items = [i for i in AttrReader.items_from_klass(Species) if player.species != i]
        self.species_weights = self.weighted_dist([(i, i.value) for i in items])

        monsters = []
        n = max(int(normalvariate(self.base_mean, self.base_std_dev)), 0)
        for i in range(n):
            # pick the object from the class
            species = self.pick_from_weights(self.species_weights)
            monster = Being(controller, species)
            monsters.append(monster)
        return monsters

    def place_monsters(self, monsters, level):

        tiles = [t for t in level.itervalues() if t.tiletype.is_open]
        for monster in monsters:
            tile = choice(tiles)
            tile.move_to(monster)
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
    
    tries = 100
    s = 0
    for i in range(tries):
        generator = LevelGenerator()
        tiles, grid = generator.generate()
        print tiles is not None
        if tiles:
            s += 1

    print s


    #generator = ObjectGenerator()
    #print (generator.generate(10, 0))




    
