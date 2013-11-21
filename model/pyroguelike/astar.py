

#http://www.laurentluce.com/posts/solving-mazes-using-python-simple-recursivity-and-a-search/

import heapq
from itertools import product

class Cell(object):
    def __init__(self, x, y, reachable):
        """
        Initialize new cell

        @param x cell x coordinate
        @param y cell y coordinate
        @param reachable is cell reachable? not a wall?
        """
        self.reachable = reachable
        self.x = x
        self.y = y
        self.parent = None
        self.g = 0
        self.h = 0
        self.f = 0


class AStar(object):

    def __init__(self, flags, start, end):
        self.op = []
        heapq.heapify(self.op)
        self.cl = set()
        self.cells = {}

        for x,y in [(x,y) for y in range(flags.size[1]) for x in range(flags.size[0])]:
            self.cells[(x,y)] = (Cell(x, y, flags[x,y]))

        self.start = self.cells[start]
        self.end = self.cells[end]

    def get_heuristic(self, cell):
        """
        Compute the heuristic value H for a cell: distance between
        this cell and the ending cell multiply by 10.

        @param cell
        @returns heuristic value H
        """
        return 10 * (abs(cell.x - self.end.x) + abs(cell.y - self.end.y))

    def get_adjacent_cells(self, cell):

        cells = []
        of = [-1, 0, 1]
        for xo, yo in [p for p in product(of, of) if p != (0,0)]:
            #dont care if were of the board ... get returns None
            c = self.cells.get((cell.x+xo, cell.y+yo))
            if c:
                cells.append(c)
        return cells

    def path(self):
        path = []
        cell = self.end
        if not cell.parent:
            return []
        while cell.parent is not self.start:
            cell = cell.parent
            path.append((cell.x, cell.y))
        return path

    def update_cell(self, adj, cell):
        """
        Update adjacent cell

        @param adj adjacent cell to current cell
        @param cell current cell being processed
        """
        adj.g = cell.g + 10
        adj.h = self.get_heuristic(adj)
        adj.parent = cell
        adj.f = adj.h + adj.g

    def process(self):
        # add starting cell to open heap queue
        heapq.heappush(self.op, (self.start.f, self.start))
        while len(self.op):
            # pop cell from heap queue 
            f, cell = heapq.heappop(self.op)
            # add cell to closed list so we don't process it twice
            self.cl.add(cell)
            # if ending cell, display found path
            if cell is self.end:
                return self.path()
                break
            # get adjacent cells for cell
            adj_cells = self.get_adjacent_cells(cell)
            for c in adj_cells:
                if c.reachable and c not in self.cl:
                    if (c.f, c) in self.op:
                        # if adj cell in open list, check if current path is
                        # better than the one previously found for this adj cell.
                        if c.g > cell.g + 10:
                            self.update_cell(c, cell)
                    else:
                        self.update_cell(c, cell)
                        # add adj cell to open list
                        heapq.heappush(self.op, (c.f, c))




if __name__ == '__main__':
    
    from grid import Flags

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

    flags = Flags.from_tiles_attr(tiles, 'is_open')
    astar = AStar(flags, (13,7), (20,5))
    astar.process()
    print astar.path()
