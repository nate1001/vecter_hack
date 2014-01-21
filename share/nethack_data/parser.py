
#/*
# *	Entry Format:		(from permonst.h)
# *
# *	name, symbol (S_* defines),
# *	level level, move rate, armor class, magic resistance,
# *	alignment, creation/geno flags (G_* defines),
# *	6 * attack structs ( type , damage-type, # dice, # sides ),
# *	weight (WT_* defines), nutritional value, extension length,
# *	sounds made (MS_* defines), physical size (MZ_* defines),
# *	resistances, resistances conferred (both MR_* defines),
# *	3 * flag bitmaps (M1_*, M2_*, and M3_* defines respectively)
# *	symbol color (C(x) macro)

####MON("giant ant", S_ANT,
####LVL(2, 18, 3, 0, 0), (G_GENO|G_SGROUP|3),
####A(ATTK(AT_BITE, AD_PHYS, 1, 4),
####  NO_ATTK, NO_ATTK, NO_ATTK, NO_ATTK, NO_ATTK),
####SIZ(10, 10, 0, MS_SILENT, MZ_TINY), 0, 0,
####M1_ANIMAL|M1_NOHANDS|M1_OVIPAROUS|M1_CARNIVORE,
####M2_HOSTILE, 0, CLR_BROWN),

class Genus(object):
    
    names = {
        'ant':			'a',
        'blob': 		'b',
        'cockatrice':	'c',
        'dog':			'd',
        'eye':			'e',
        'feline':		'f',
        'gremlin':		'g',
        'humanoid':		'h',
        'imp':			'i',
        'jelly':		'j',
        'kobold':		'k',
        'leprechaun':	'l',
        'mimic':		'm',
        'nymph':		'n',
        'orc':			'o',
        'piercer':		'p',
        'quadruped':	'q',
        'rodent':		'r',
        'spider':		's',
        'trapper':		't',
        'unicorn':		'u',
        'vortex':		'v',
        'worm':		    'w',
        'xan':			'x',
        'light':		'y',
        'zruty':		'z',
        'angel':		'A',
        'bat':			'B',
        'centaur':		'C',
        'dragon':		'D',
        'elemental':	'E',
        'fungus':		'F',
        'gnome':		'G',
        'giant':		'H',
        #invisible':	'I',
        'jabberwock':	'J',
        'kop':			'K',
        'lich':		    'L',
        'mummy':		'M',
        'naga':		    'N',
        'ogre':		    'O',
        'pudding':		'P',
        'quantmech':    'Q',
        'rustmonst':    'R',
        'snake':		'S',
        'troll':		'T',
        'umber':		'U',
        'vampire':		'V',
        'wraith':		'W',
        'xorn':		    'X',
        'yeti':		    'Y',
        'zombie':		'Z',
        'human':		'@',
        'ghost':		' ',
        'golem':		'\'',
        'demon':		'&',
        'eel':			';',
        'lizard':		':',
        #worm_tail':		'~',
    }


    def __init__(self, name, flags):
        self.name = name
        self.flags = flags

    def to_config(self):
        s = '[{}]\n'.format(self.name)
        s += 'ascii: {}\n'.format(self.names[self.name])

        #if 'is infravisible' in self.flags:
        #    warm_blooded = True
        #    self.flags.remove('is infravisible')
        #else:
        #    warm_blooded = False
        #s += 'warm_blooded: {}\n'.format(warm_blooded)

        #cant pickup is always with 'has no limbs' #hmmm!?
        if 'cant pickup' in self.flags:
            self.flags.remove('cant pickup')

        s += 'flags: {}\n'.format(', '.join(self.flags))
        return s
            


class Attack(object):

    ways = {
        'AT_NONE':  'passive',
        'AT_CLAW':  'claws',
        'AT_BITE':  'bites',
        'AT_KICK':  'kicks',
        'AT_BUTT':  'butts',
        'AT_TUCH':  'touches',
        'AT_STNG':  'stings',
        'AT_HUGS':  'crushes',
        'AT_SPIT':  'spits',
        'AT_ENGL':  'engulfs',
        'AT_BREA':  'breaths',
        'AT_EXPL':  'explodes at you',
        'AT_BOOM':  'explodes by you', #when killed
        'AT_GAZE':  'gazes', # ranged
        'AT_TENT':  'uses tentacles', # what is the verb here?
        'AT_WEAP':  'wields',
        'AT_MAGC':  'casts',
    }
    means = {
        'AD_PHYS': 'melee',   #ordinary physical */
        'AD_MAGM': 'cast magic_missile',   #magic missiles */
        'AD_FIRE': 'burn',  #fire damage */
        'AD_COLD': 'freeze',  #frost damage */
        'AD_SLEE': 'soothe',  #sleep ray */
        'AD_DISN': 'disintigrate',  #disintegration (death ray) */
        'AD_ELEC': 'shock',  #shock damage */
        'AD_DRST': 'drain strength',  #drains str (poison) */
        'AD_ACID': 'acidify',  #acid damage */
        #'AD_SPC1':   #for extension of buzz() */
        #'AD_SPC2':   #for extension of buzz() */
        'AD_BLND': 'blind',  #blinds (yellow light) */
        'AD_STUN': 'stun',  #stuns */
        'AD_SLOW': 'slow',  #slows */
        'AD_PLYS': 'paralyze',  #paralyses */
        'AD_DRLI': 'drain life',  #drains life levels (Vampire) */
        'AD_DREN': 'drain spell points',  #drains magic energy */
        'AD_LEGS': 'damage legs',  #damages legs (xan) */
        'AD_STON': 'petrify',  #petrifies (Medusa, cockatrice) */
        'AD_STCK': 'stick',  #sticks to you (mimic) */
        'AD_SGLD': 'steal gold',  #steals gold (leppie) */
        'AD_SITM': 'steal item',  #steals item (nymphs) */
        'AD_SEDU': 'seduce and steal',  #seduces & steals multiple items */
        'AD_TLPT': 'teleport',  #teleports you (Quantum Mech.) */
        'AD_RUST': 'rust',  #rusts armour (Rust Monster)*/
        'AD_CONF': 'confuse',  #confuses (Umber Hulk) */
        'AD_DGST': 'digest',  #digests opponent (trapper, etc.) */
        'AD_HEAL': 'heal',  #heals opponents wounds (nurse) */
        'AD_WRAP': 'wrap',  #special "stick" for eels */
        'AD_WERE': 'lycanthrope',  #confers lycanthropy */
        'AD_DRDX': 'drain dexterity', #drains dexterity (quasit) */
        'AD_DRCO': 'drain constitution',  #drains constitution */
        'AD_DRIN': 'drain intellgence',  #drains intelligence (mind flayer) */
        'AD_DISE': 'sicken',  #confers diseases */
        'AD_DCAY': 'decay',  #decays organics (brown Pudding) */
        'AD_SSEX': 'seduce',  #Succubus seduction (extended) */
        'AD_HALU': 'hallicinate',  #causes hallucination */
        'AD_DETH': 'cast Death',  #for Death only */
        'AD_PEST': 'cast Pestilence',  #for Pestilence only */
        'AD_FAMN': 'cast Famine',  #for Famine only */
        'AD_SLIM': 'slime',  #turns you into green slime */
        'AD_ENCH': 'drain enchantment',  #remove enchantment (disenchanter) */
        'AD_CORR': 'corrode',  #corrode armor (black pudding) */
        'AD_CLRC': 'cast random clerical spell',  #random clerical spell */
        'AD_SPEL': 'cast random magic spell',  #random magic spell */
        'AD_RBRE': 'cast random breath spell',  #random breath weapon */
        'AD_SAMU': 'steal amulet',  #hits, may steal Amulet (Wizard) */
        'AD_CURS': 'curse',  #random curse (ex. gremlin) */
    }
    def __init__(self, flags):
        self.way = self.ways[flags[0]]
        self.means = self.means[flags[1]]
        self.rolls = flags[2]
        self.sides = flags[3]

    def __repr__(self):
        return '<Attack "{} to {}" for {}d{}>'.format(self.way, self.means, self.rolls, self.sides)

    def __str__(self):
        return '{}|{}|{}d{}'.format(self.way, self.means, self.rolls, self.sides)

class Generation(object):

    defs = {
        'G_UNIQ': 'unique',
        'G_NOHELL': 'nohell',
        'G_HELL': 'hell',
        'G_SGROUP': 'small_groups',
        'G_LGROUP': 'large_groups',
        'G_GENO': 'genocidable',
        'G_NOCORPSE': 'no_corpse',
        'G_NOGEN': 'nogen',
    }
    
    def __init__(self, flags):
        
        self.unique = False
        self.nohell = False
        self.hell = False
        self.small_groups = False
        self.large_groups = False
        self.genocidable = False
        self.no_corpse = False
        self.frequency = None
        self.nogen = None

        for flag in flags:
            try:
                attr = self.defs[flag]
                setattr(self, attr, True)
            except KeyError:
                self.frequency = int(flag)
        if self.nogen:
            self.frequency = 0
        
        if self.nohell and self.hell:
            raise ValueError()
        if self.small_groups and self.large_groups:
            raise ValueError()
        #XXX A few monsters (watchman, giant, watch captain)  had nogen and 1 set?
        # Think probably one will probably override other in code
        # I edited monst.c to have them read just nogen
        if self.nogen and self.frequency:
            raise ValueError()
        #XXX babies and hatchlings dont have frequency set?
        # me thinks they inherit it from daddy?
        #if not self.nogen and not self.frequency:


    def __repr__(self):
        flags = ''
        if self.unique:
            flags += ' U'
        if self.hell:
            flags += ' H'
        if self.nohell:
            flags += ' NH'
        if self.small_groups:
            flags += ' SG'
        if self.large_groups:
            flags += ' LG'
        if self.genocidable:
            flags += ' GEN'
        flags += ' ' + str(self.frequency)
        return '<Generation {}>'.format(flags.strip())

    def __str__(self):
        flags = []
        flags.append(str(self.frequency))
        if self.unique:
            flags.append('unique')
        if self.hell:
            flags.append('hell')
        if self.nohell:
            flags.append('no hell')
        if self.small_groups:
            flags.append('small groups')
        if self.large_groups:
            flags.append('large groups')
        if self.genocidable:
            flags.append('genocidable')
        return '|'.join(flags)



class Monster(object):
    
    defs = {
        'A_NONE': None,
        'WT_HUMAN':    1450,
        'WT_DRAGON': 4500,
        'WT_ELF': 800,
        'MS_SILENT': None,
        '0': None,
    }
    flag_items = {
        'M1_FLY': 'can fly',
        'M1_SWIM': 'can swim',
        'M1_AMORPHOUS': 'can pass under doors', # pass under closed doors
        'M1_WALLWALK': 'can pass through walls',
        'M1_CLING': 'can cling to ceilings',
        'M1_TUNNEL': 'can tunnel',
        'M1_NEEDPICK': 'needs a pick to tunnel',
        'M1_CONCEAL': 'hides under objects',
        'M1_HIDE':'can mimic',
        'M1_AMPHIBIOUS': 'is amphibious',
        'M1_BREATHLESS': 'is breathless',
        'M1_NOTAKE': 'cant pickup',
        'M1_NOEYES': 'cant look',
        'M1_NOHANDS': 'cant grab',
        'M1_NOLIMBS': 'has no limbs',
        'M1_NOHEAD': 'is headless',
        'M1_MINDLESS':'is mindless',
        'M1_HUMANOID': 'is a humanoid',
        'M1_ANIMAL': 'is an animal',
        'M1_SLITHY': 'is slithy',
        'M1_UNSOLID': 'is not solid',
        'M1_THICK_HIDE': 'has a thick hide',
        'M1_OVIPAROUS': 'can lay eggs',
        'M1_REGEN': 'can regenerate',
        'M1_SEE_INVIS': 'can see invisible',
        'M1_TPORT': 'can teleport',
        'M1_TPORT_CNTRL': 'has teleport control',
        'M1_ACID': 'is acidic',
        'M1_POIS': 'is poisonous',
        'M1_CARNIVORE': 'is a carnivore',
        'M1_HERBIVORE': 'is a herbivore',
        'M1_OMNIVORE': 'is a omnivore',
        'M1_METALLIVORE': 'is a metallivore',
        'M2_NOPOLY': 'cant be polymorphed into',
        'M2_UNDEAD': 'is undead',
        'M2_WERE': 'is a lycanthrope',#werewolf
        'M2_HUMAN': 'is a human',
        'M2_ELF': 'is an elf',
        'M2_DWARF': 'is a dwarf',
        'M2_GNOME': 'is a gnome',
        'M2_ORC': 'is an orc',
        'M2_DEMON': 'is a demon',
        'M2_MERC': 'is a mercenary',
        'M2_LORD': 'is a lord',
        'M2_PRINCE': 'is a prince',
        'M2_MINION': 'is a minion',
        'M2_GIANT': 'is a giant',
        'M2_MALE': 'is always male',
        'M2_FEMALE': 'is always female',
        'M2_NEUTER': 'is always non-gendered',
        'M2_PNAME': 'has a proper name',
        'M2_HOSTILE': 'is always hostile',
        'M2_PEACEFUL': 'is always peaceful',
        'M2_DOMESTIC': 'can be tamed',
        'M2_WANDER': 'wanders',
        'M2_STALK': 'stalks',
        'M2_NASTY': 'is nasty',
        'M2_STRONG': 'is strong',
        'M2_ROCKTHROW': 'can throw rocks',
        'M2_GREEDY': 'likes gold',
        'M2_JEWELS': 'likes gems',
        'M2_COLLECT': 'likes weapons and food',
        'M2_MAGIC': 'likes magical items',
        'M3_WANTSAMUL': 'wants the amulet',
        'M3_WANTSBELL': 'wants the bell',
        'M3_WANTSBOOK': 'wants the book',
        'M3_WANTSCAND': 'wants the candelabrum',
        'M3_WANTSARTI': 'wants the quest artifact',
        'M3_WANTSALL': 'wants all artifacts',
        'M3_WAITFORU': 'will wait for you',
        'M3_CLOSE': 'will let you close',
        'M3_COVETOUS': 'wants something',
        'M3_WAITMASK': 'is waiting',
        'M3_INFRAVISION': 'has infravision',
        'M3_INFRAVISIBLE': 'is infravisible',
    }
    

    resist_names = {
        'stone': 'stoning resistance',
        'elec': 'shock resistance', 
        'fire': 'fire resistance', 
        'poison': 'poison resistance', 
        'sleep': 'sleep resistance', 
        'disint': 'disintigration resistance',
        'cold': 'cold resistance',
        'acid': 'acid resistance',
    }

    def __init__(self):
        self.name = None
        self.genus = None
        self.level = None
        self.speed = None
        self.ac = None
        self.magic_resistance = None
        self.alignment = None
        self.generation = None
        self.frequency = None
        self.attacks = []
        self.weight = None;
        self.nutrition = None;
        self.length = None # will be deleted
        self.sound = None
        self.size = None
        self.resistances = []
        self.resistances_conferred = []
        self.m1 = None # will be deleted
        self.m2 = None # will be deleted
        self.m3 = None # will be deleted
        self.flags = []
        self.color = None
        self.diet = None


    def __repr__(self):
        return '<Monster {}>'.format(self.name)

    def to_config(self):
        s = '[{}]\n'.format(self.name)
        s += 'genus: {}\n'.format(self.genus)
        s += 'level: {}\n'.format(self.level)
        s += 'speed: {}\n'.format(self.speed)
        s += 'ac: {}\n'.format(self.ac)
        s += 'magic_resistance: {}\n'.format(self.magic_resistance)
        s += 'alignment: {}\n'.format(self.alignment)
        s += 'generation: {}\n'.format(self.generation)
        s += 'attacks: {}\n'.format(', '.join([str(a) for a in self.attacks]))
        s += 'weight: {}\n'.format(self.weight)
        s += 'nutrition: {}\n'.format(self.nutrition)
        s += 'sound: {}\n'.format(self.sound)
        s += 'size: {}\n'.format(self.size)
        s += 'resistances: {}\n'.format(', '.join(self.resistances))
        s += 'resistances_conferred: {}\n'.format(', '.join(self.resistances_conferred))
        s += 'diet: {}\n'.format(self.diet)
        s += 'flags: {}\n'.format(', '.join(self.flags))
        s += 'color: {}\n'.format(self.color)

        return s

    def finalize(self):
        self.level = int(self.level)
        self.speed = int(self.speed)
        self.ac = int(self.ac)
        self.magic_resistance = int(self.magic_resistance)

        try:
            self.alignment = int(self.alignment)
        except ValueError:
            self.alignment = self.defs[self.alignment]

        self.generation = Generation(self.generation)

        attacks = []
        for attack in self.attacks:
            attacks.append(Attack(attack))
        self.attacks = attacks

        try:
            self.weight = int(self.weight)
        except ValueError:
            self.weight = self.defs[self.weight]
        self.nutrition = int(self.nutrition)
        del self.length # for C memory management

        if self.defs.get(self.sound):
            self.sound = self.defs[self.sound]
        else:
            self.sound = self.sound.replace('MS_','').lower()
        self.size = self.size.replace('MZ_','').lower()

        r = [(None if r.strip()=='0' else r.replace('MR_','').lower().strip()) for r in self.resistances]
        self.resistances = [self.resist_names[r] for r in r if r]
        r = [(None if r.strip()=='0' else r.replace('MR_','').lower().strip()) for r in self.resistances_conferred]
        self.resistances_conferred = [self.resist_names[r] for r in r if r]

        flags = []
        flags.extend(self.m1.split('|'))
        flags.extend(self.m2.split('|'))
        flags.extend(self.m3.split('|'))
        for flag in [f for f in flags if f != '0']:
            self.flags.append(self.flag_items[flag])
        self.flags = sorted(self.flags)
        del self.m1
        del self.m2
        del self.m3

        if 'is a carnivore' in self.flags:
            diet = 'carnivore'
            self.flags.remove('is a carnivore')
        elif 'is a herbivore' in self.flags:
            diet = 'herbivore'
            self.flags.remove('is a herbivore')
        elif 'is a omnivore' in self.flags:
            diet = 'omnivore'
            self.flags.remove('is a omnivore')
        elif 'is a metallivore' in self.flags:
            diet = 'metallivore'
            self.flags.remove('is a metallivore')
        else:
            diet = None
        self.diet = diet
            
        


class MonsterParser(object):

    def get_genus_flags(self, monsters):

        genus = {}
        for monster in monsters:
            g = monster.genus
            if not genus.get(g):
                genus[g] = monster.flags[:]
            else:
                for flag in genus[g]:
                    if flag not in monster.flags:
                        genus[g].remove(flag)
        return genus


    def parse_monster(self, fname):
        
        f = open(fname)
        monsters = []
        entry = []
        for line in f:
            line = line.strip()
            if not line or line.startswith('/*') or line.startswith('#') or line.startswith('*'):
                continue
            if line.startswith('MON('):
                if entry:
                    monsters.append(self.parse_entry(entry))
                    monsters[-1].finalize()

                entry = []
            entry.append(line)
        return monsters

    def parse_entry(self, entry):
        m = Monster()
        self.parse_line0(entry[0], m)
        self.parse_line1(entry[1], m)
        self.parse_line2(entry[2], m)
        if not entry[3].startswith('SIZ'):
            self.parse_line2(entry[3], m)
            entry.pop(3)
        if entry[3].startswith('NO_ATTK'):
            entry.pop(3)
        if entry[3].startswith('ATTK('):
            self.parse_line2(entry[3], m)
            entry.pop(3)
        self.parse_line3(entry[3], m)
        if entry[4].startswith('MR_'):
            r, rc, _ = entry[4].split(',')
            m.resistances = r.split('|')
            m.resistances_conferred = rc.split('|')
            entry.pop(4)
        self.parse_line4(' '.join(entry[4:]), m)
        return m

    def parse_line0(self, line, monster):
        # *	name, symbol (S_* defines),
        _, g = line.split('MON(')
        g = g.split(',')
        monster.name = g[0].replace('"','')
        monster.genus = g[1].replace('S_', '').lower().strip()

    def parse_line1(self, line, monster):
        # *	level level, move rate, armor class, magic resistance,
        # *	alignment, creation/geno flags (G_* defines),
        line = line.replace(' ', '')
        line = line.split('),')
        stuff = line.pop(0).replace('LVL(', '')
        diff, speed, ac, mr, al = stuff.split(',')

        monster.level = diff
        monster.speed = speed
        monster.ac = ac
        monster.magic_resistance = mr
        monster.alignment = al
        if len(line) > 1 and line[1]:
            raise ValueError(line)
        gen = line[0].replace('(', '')
        if gen.find('/*') > -1:
            gen = gen[:gen.find('/*')]
        monster.generation = gen.replace(',','').strip().split('|')

    def parse_line2(self, line, monster):
        line = line.replace('A(', '')
        attacks = line.split('ATTK(')
        if not attacks[0]:
            attacks.pop(0)
        for attack in attacks:
            a = self.parse_attack(attack, monster)
            if a:
                monster.attacks.append(a)

    def parse_attack(self, attack, monster):
        # *	6 * attack structs ( type , damage-type, # dice, # sides ),

        #self.weight = None; self.nutrition = None; self.length = length; self.sounds = sounds; self.size = size
        #self.resistances = []; self.resistances_conferred = None
        
        attack = attack.replace(' ','').replace(')','').split(',')
        attack = [a for a in attack if a and a != 'NO_ATTK']
        return attack

    def parse_line3(self, line, monster):
        # *	weight (WT_* defines), nutritional value, extension length,
        # *	sounds made (MS_* defines), physical size (MZ_* defines),
        # *	resistances, resistances conferred (both MR_* defines),
        line = line.replace('SIZ(','').replace(' ','')
        parts = line.split('),')
        if len(parts) != 2:
            raise ValueError(parts)
        w, n, l, so, si = parts[0].split(',')
        monster.weight = w
        monster.nutrition = n
        monster.length = l
        monster.sound = so
        monster.size = si
        if parts[1]:
            r, rc, _ = parts[1].split(',')
            monster.resistances = r.split('|')
            monster.resistances_conferred = rc.split('|')

    def parse_line4(self, line, monster):
        m1, m2, m3, color, _ = line.replace(' ','').split(',')
        monster.m1 = m1
        monster.m2 = m2
        monster.m3 = m3
        monster.color = color.replace('HI_','').replace('CLR_','').lower().replace(')','')


class Weapon(object):
    
    materials = {
        'wood': 'wood',
        'iron': 'iron',
        'minl': 'mineral',
        'bone': 'bone',
        'metl': 'metal',
        'plas': 'plastic',
        'silv': 'silver',
        'leat': 'leather',
        'none': None,
    }
        
    
    def __init__(self, klass):
        self.klass = klass
        self.name = None
        self.cost = None
        self.weight = None
        self.two_handed = False
        self.material = None
        self.appearance = None
        self.japanese = None

        self.hit_bonus = None
        self.small_damage = None
        self.small_avg = None
        self.large_damage = None
        self.large_avg = None

    def __repr__(self):
        b = '+{}'.format(self.hit_bonus) if self.hit_bonus else ''
        return '<Weapon {} {} {} {} {}>'.format(
            self.klass, repr(self.name), b, self.small_damage, self.large_damage)

    def to_config(self):
        s = ''
        s += '[{}]\n'.format(self.name)
        s += 'klass: {}\n'.format(self.klass)
        s += 'cost: {}\n'.format(self.cost)
        s += 'weight: {}\n'.format(self.weight)
        s += 'two_handed: {}\n'.format(self.two_handed)
        s += 'material: {}\n'.format(self.material)
        s += 'appearance: {}\n'.format(self.appearance)
        s += 'japances: {}\n'.format(self.japanese)
        s += 'hit_bonus: {}\n'.format(self.hit_bonus)
        s += 'small_damage: {}\n'.format(self.small_damage)
        s += 'large_damage: {}\n'.format(self.large_damage)
        return s
        

    def add_table_one(self, a, b, c):
        cost, w, p = b.split()
        if w.endswith('*'):
            self.two_handed = True
            w = w[:-1]
        parts = c.split()

        if a.find('(') > -1:
            a, j = a.split('(')
            self.japanese = j[:-1]
        self.name = a.strip()

        self.cost = int(cost)
        self.weight = int(w)
        #pick-axes and flint stones are included but dont have a prob in the
        # table becuase they are generated with tools.
        if p not in ('tool', 'gems'):
            self.prob = int(p)
        self.material = self.materials[parts[0].lower()]
        if parts[1] != '--':
            self.appearance = ' '.join(parts[1:])

    def add_table_two(self, a, b):
        try:
            hb, sdam, savg, ldam, lavg = b.split()
        except ValueError:
            sdam, savg, ldam, lavg = b.split()
            hb = 0

        self.hit_bonus = int(hb)
        self.small_damage = sdam
        self.small_avg = float(savg)
        self.large_damage = ldam
        self.large_avg = float(lavg)

class WeaponKind(object):
    
    def __init__(self, line):
        name, other = line.split(':')
        self.name = name.strip().lower()
        o = other.split()
        #if len(o) == 4:



class WeaponSpoilerParser(object):
    
    ignore = (
        'other rocks/gems/glass',
    )
    skills = (
        'Two weapon combat',
        'Riding',
        'Bare-handed combat',
        'Martial arts',
    )
    
    def parse(self, fname):
        weapons = {}
        f = open(fname)
        table = Weapon.add_table_one
        first = True
        for line in f:
            if line.startswith('#'):
                continue
            elif not line.strip() and first:
                first = False
                continue
            elif not line.strip():
                break

            if first:
                a,b,c = [a.strip() for a in line.split(':')]
                if not b and not c:
                    klass = a.lower()
                else:
                    if a not in self.ignore and a not in self.skills:
                        w = Weapon(klass)
                        w.add_table_one(a, b, c)
                        weapons[w.name] = w
            else:
                if line.startswith('  '):
                   a,b = [a.strip() for a in line.split(':')]
                   if a.strip() not in self.ignore:
                        if a.find('(') > -1:
                            a, j = a.split('(')
                            a = a.strip()
                        weapons[a].add_table_two(a, b)
                else:
                    kind = WeaponKind(line.strip())
        return weapons


if __name__ == '__main__':

    p = MonsterParser()
    monsters =  p.parse_monster('monst.c')
    genus_flags = p.get_genus_flags(monsters)

    #symbols = sorted(Genus.names.values())
    #keys = []
    #for s in symbols:
    #    keys.append([k for k in Genus.names if Genus.names[k] == s][0])

    #for key in keys:
    #    g = Genus(key, genus_flags[key])
    #    #print g.name, g.flags
    #    for monster in [m for m in monsters if m.genus == g.name]:
    #        for flag in g.flags:
    #            if flag in monster.flags:
    #                monster.flags.remove(flag)
    #        #print '    ' , monster.name, monster.flags
    #    #print g.to_config()


    #resistances = {}
    #for monster in monsters:
    #    pass
    #    #print monster.name, [str(a) for a in monster.attacks]
    #    #print monster.name, monster.generation
    #    print monster.to_config()
    #    for r in monster.resistances:
    #        resistances[r] = None
    #    for r in monster.resistances_conferred:
    #        resistances[r] = None
    ##print resistances

    #p = WeaponSpoilerParser()
    #weapons = p.parse('weap-341.txt')
    #for weapon in weapons.values():
    #    print weapon.to_config()

    #attacks_m = {}
    #for m in monsters:
    #    for attack in m.attacks:
    #        attacks_m[attack.means] = None

    #for m in sorted(attacks_m.keys()):
    #    print '[{}]'.format(m)

    attacks_w = {}
    for m in monsters:
        for attack in m.attacks:
            attacks_w[attack.way] = None

    for m in sorted(attacks_w.keys()):
        print '[{}]'.format(m)
    

