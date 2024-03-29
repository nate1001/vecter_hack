
from being import Being, Species, PlayerView
from generate import LevelGenerator, ObjectGenerator, SpeciesGenerator
from ai import AI
from level import Level
from messenger import Messenger, Signal, register_command, registered_commands
from attr_reader import AttrReader
from spell import Spell
from config import logger


from equipment import Equipment, Light, EquipmentStack, Armor, MeleeWeapon, Potion, Wand, Scroll, init_appearance, equipment_classes


class Game(Messenger):

    __signals__ = [
            Signal('game_started', ('level',)),
            Signal('game_ended', (),),
            Signal('turn_finished', ('turn_number', 'player_can_move'),),
            Signal('redraw', ('level',)),
    ]

    class View(object):
        _settings_group = 'model'

        def __init__(self, dungeon):

            self.commands = registered_commands
            self.events = dungeon.events
            self.__dungeon = dungeon

        @property
        def player(self):
            if not self.__dungeon.player:
                return None
            return PlayerView(self.__dungeon.player)

        @property
        def level(self):
            return self.__dungeon.level.view()

        @register_command('game', 'New', 'ctrl+n')
        def new(self):
            self.__dungeon.new()
            self.events['game_started'].emit(self.level)

        @register_command('game', 'Redraw Screen', 'Ctrl+R')
        def redraw_screen(self):
            self.events['redraw'].emit(self.level)

        def get_setting(self, setting, value):
            return self.__dungeon.settings[self._settings_group, setting]

        def set_setting(self, setting, value):

            if setting == 'wizard':
                if self.player:
                    self.__dungeon.player.wizard = value
                    self.events['level_changed'].emit(self.level)
            else:
                raise KeyError(setting)

            self.__dungeon.settings[self._settings_group, setting] = value


    def __init__(self, controller, settings):
        super(Game, self).__init__()

        #check to make sure that the controller
        #can handle all of the registered spells
        #so it does not pop randomly in the middle 
        #of game ;)
        for spell in AttrReader.items_from_klass(Spell):
            controller.get_spell_handler(spell)

        controller.set_game(self)
        self.controller = controller
        self.settings = settings
        self.ai = AI(self.controller._send_msg)
        self.levels = None
        self.player = None

        for event in self.controller.events.values():
            self.events[event.name] = event

        self._turn_num = None
        self._level_count = None
        self._current_level = None

        self._level_generator = LevelGenerator()
        self._object_generator = ObjectGenerator()
        self._species_generator = SpeciesGenerator()

    @property
    def turns(self):
        return self._turn_num

    @property
    def level(self):
        return self._current_level

    def new(self):
        init_appearance()
        self.levels = []
        self.player = self._create_player()
        self._level_count = 0
        self._turn_num = 0
        self._current_level = self.generate_level()

    def view(self):
        return Game.View(self)

    def die(self):
        self.events['game_ended'].emit()

    def generate_level(self):
        self._level_count += 1
        min_rooms = 5
        size = 20,20

        # generate the tile types
        tiletypes, rooms = self._level_generator.generate( size, min_rooms)
        level = Level(self.player, tiletypes, self._level_count)

        # generate the objects
        objects = self._object_generator.generate(min_rooms, self._level_count)
        self._object_generator.place_objects(objects, level)

        # generate monsters
        species = self._species_generator.generate_level(self._level_count)
        beings = [Being(self.controller, s) for s in species]
        self._species_generator.place_beings(beings, level)

        # set the player on a up staircase
        tile = level.staircases_up[0]
        level.add_being(tile, self.player)

        self.levels.append(level)
        self._current_level = level

        #housekeeping
        #FIXME this will need to move to change_level
        for being in [b for b in level.beings]:
            being.new_level(level._size)
        self.turn_done(move_monsters=False)

        for being in [t.being for t in level.values() if t.being and self.player.vision.can_see(t)]:
            being.has_been_seen = True

        return level


    def turn_done(self, move_monsters=True):
        
        if self.player.is_dead:
            return

        level = self._current_level
        #housekeeping
        level._set_torch_map()
        level.set_fov(self.player)

        #ai
        if move_monsters:
            monsters = [b for b in level.beings if b is not self.player]
            self.ai.move_monsters(level, self.player, monsters)

        self.events['turn_finished'].emit(self._turn_num, self.player.can_move)
        for being in level.beings:
            being.new_turn()

        #FIXME add custom logger class for this
        #logger.turn_number = self._turn_num

        self._turn_num += 1

        if not self.player.can_move:
            self.turn_done()

    def _create_player(self):
        player = Being(self.controller, Species('player'), is_player=True)

        #get everything!
        for klass in equipment_classes:
            for item in AttrReader.items_from_klass(klass):
                item = EquipmentStack.from_cls(klass, item.name)
                player.inventory.append(item)

        player.wizard = self.settings['model', 'wizard'] 

        return player

    def create_being_by(self, being, species_name):

        tile = self.level.tile_for(being)
        species = Species(species_name)
        being = Being(self.controller, species)

        for other in self.level.adjacent_tiles(tile):
            #FIXME is_open wont work for ghost types
            if not other.being and other.tiletype.is_open:
                self.level.add_being(other, being)
                return being
        return None
    
    def create_being(self):
        species = self._species_generator.generate(self._level_count)
        being = Being(self.controller, species)
        return being

    def create_item_by(self, being, name):
        first = name.strip().split(' ')[0]
        klass = Equipment.klass_by_name(first)
        third = name.strip().split(' of ')[1]
        stack = EquipmentStack.from_cls(klass, third)

        tile = self.tile_for(being)
        tile.inventory.append(stack)
        return stack

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



