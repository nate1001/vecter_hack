

class Flags(object):

    def __init__(self, size):

        self._size = size
        self._num = 0

    @classmethod
    def from_tiles_attr(cls, tiles, attr):

        w, h = len(tiles[0]), len(tiles)
        f = Flags((w,h))

        l = [('1' if getattr(tile, attr) else '0') for row in tiles for tile in row]
        l.reverse()
        f._num = long(''.join(l), 2)
        return f

    def copy(self):
        return self.__new_from_number(self, self._num)

    def __setitem__(self, idx, is_on):

        x, y = idx
        if type(is_on) != bool:
            raise ValueError(is_on)
        if x >= self._size[0] or y >= self._size[1] or x < 0 or y < 0:
            raise KeyError(idx)

        i = y * self._size[0] + x
        if is_on:
            self._num = self._num | 1<<i
        else:
            self._num = self._num & ~(-1*(1<<(i+1) - 1))


    def __getitem__(self, idx):

        x, y = idx
        if x >= self._size[0] or y >= self._size[1] or x < 0 or y < 0:
            raise KeyError(idx)
        i = y * self._size[0] + x

        return (self._num & 1<<i) > 0

    def __eq__(self, other):
        return self._num == other._num

    def __ne__(self, other):
        return not self.__eq__(other)

    def __nonzero__(self):
        return self._num != 0

    def __new_from_number(self, other, num):

        if self._size != other._size:
            return ValueError('size {} != size {}'.format(self._size, other._size))
        new = Flags(self._size)
        new._num = num
        return new
        
    def __and__(self, other):
        return self.__new_from_number(other, self._num & other._num)

    def __or__(self, other):
        return self.__new_from_number(other, self._num | other._num)
        
    def __xor__(self, other):
        return self.__new_from_number(other, self._num ^ other._num)

    def __invert__(self):
        
        #FIXME
        #return self.__new_from_number(self, ~self._num)

        new = Flags(self._size)
        w, h = self._size

        l = [
            ('0' if  ((self._num & 1 << (y * w + x))) > 0 else '1') 
            for y in range(h) for x in range(w)]
        l.reverse()
        new._num = long(''.join(l), 2)

        return new

    def __str__(self):

        w, h = self._size
        string = bin(self._num)[2:]
        # we have to add on leading zeros
        string = '0' * ( (w*h) - len(string)) + string

        s = ''
        for y in sorted(range(h), reverse=True):
            if y != h-1:
                s += '\n'
            for x in sorted(range(w), reverse=True):
                s += string[y * w + x]
        return s + '\n'

    @property
    def number(self):
        return self._num

    @property
    def size(self):
        return self._size

    def clear(self):
        self._num = 0

    def fill(self):
        self._num = long('1' * (self._size[0] * self._size[1]), 2)


if __name__ == '__main__':

    from grid import Grid

    class TileType(object):
        def __init__(self, name, char, is_open):
            
            self.name = name
            self.char = char
            self.is_open = is_open
    

    tiletypes = {
        ' ' : TileType('rock', ' ', False),
        '-' : TileType('horizontal wall', '-', False),
        '|' : TileType('vertical wall', '|', False),
        '+' : TileType('open door', '+', True),
        '.' : TileType('floor', '.', True),
        '#' : TileType('passage', '#', True),
    }

    map_ ='''
                                             
           -----------             ----------
           |.........|           ##+........|
           |.........|          #  |........|
           |.........+##########   |........|
           |.........|             |........|
           |.........|             ----------
           |.........|                       
           -----------                       
    '''

    tiles = []
    for row in map_.split('\n')[1:-1]:
        tiles.append([])
        for char in row:
            tiles[-1].append(tiletypes[char])

    #size = len(tiles[0]), len(tiles)
    #grid = Grid(size)
    #open_ = Flags.from_tiles_attr(tiles, 'is_open')
    #print open_

    #seen = grid.fov(open_, (23,5), 4)
    #print seen

    #fov lit walls
    #print ~open_ & seen

    #path = Flags(size)
    #for idx in grid.get_path(open_, (15, 5), (40,5)):
    #    path[idx] = True
    #print path 

    #print Flags.from_tiles_attr(tiles, 'is_open')

    f = Flags((3,2))
    f[2,1] = True
    f[1,1] = True

    o = Flags((3,2))
    o[1,1] = True
    o[0,1] = True

    print f

    print  ~f

    print o

    print f & o

    print f | o

    print f ^ o

    if f:
        print 'true'

    f.fill()
    print f

    f.clear()
    print f

    if not f:
        print 'false'


