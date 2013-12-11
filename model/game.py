
from species import Being, Species, PlayerView
from action import Controller
from generate import LevelGenerator, ObjectGenerator, MonsterGenerator
from ai import AI
from level import Level
from messenger import Messenger, Signal, register_command, registered_commands
import config

from equipment import Light, EquipmentStack, Armor, MeleeWeapon


class Game(Messenger):

    __signals__ = [
            Signal('game_started', ('level',)),
            Signal('game_ended', (),),
            Signal('turn_finished', ('turn_number',),),
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


    def __init__(self, settings):
        super(Game, self).__init__()
        
        self.settings = settings
        self.controller = Controller(self)
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
        self._monster_generator = MonsterGenerator()

    @property
    def turns(self):
        return self._turn_num

    @property
    def level(self):
        return self._current_level

    def new(self):
        self.levels = []
        self.player = self._create_player()
        self._level_count = 0
        self._turn_num = 0
        self._current_level = self.generate_level()

    def view(self):
        return Game.View(self)


    #FIXME move to view
    def die(self):
        self.events['game_ended'].emit()

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

        self.events['turn_finished'].emit(self._turn_num)
        self._turn_num += 1
        config.logger.info('new turn: {}.'.format(self._turn_num))

    def _create_player(self):
        player = Being(self.controller, Species('hacker'), is_player=True)
        player.condition.asleep = False

        torch = EquipmentStack.from_cls(Light, 'torch')
        player.inventory.append(torch)

        armor = EquipmentStack.from_cls(Armor, 'leather armor')
        player.inventory.append(armor)

        sword = EquipmentStack.from_cls(MeleeWeapon, 'long sword')
        player.inventory.append(sword)

        player.wizard = self.settings['model', 'wizard'] 

        return player

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


