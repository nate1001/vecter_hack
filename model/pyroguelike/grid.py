

from raycasting import Ray
from astar import AStar

from flags import Flags


class Grid(object):

    def __init__(self, size):
        
        self._size = size
        self._raygen = Ray(max(size))


    def fov(self, reachable, origin, radius):
        
        seen = Flags(self._size)
        for ray in self._raygen.rays(origin, radius, self._size):
            for idx in ray:

                seen[idx] = True
                # Stop ray if it hit a wall.
                if not reachable[idx]:
                    break
        return seen

    def get_path(self, flags, start, end):

        astar = AStar(flags, start, end)
        astar.process()
        return astar.path()
        



if __name__ == '__main__':

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

    size = len(tiles[0]), len(tiles)
    grid = Grid(size)
    open_ = Flags.from_tiles_attr(tiles, 'is_open')
    print open_

    seen = grid.fov(open_, (23,5), 4)
    print seen

    #fov lit walls
    print ~open_ & seen

    #path = Flags(size)
    #for idx in grid.get_path(open_, (15, 5), (40,5)):
    #    path[idx] = True
    #print path 
