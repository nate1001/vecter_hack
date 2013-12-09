
from collections import OrderedDict

templates = {}
adapters = {}

templates['monster.txt'] = '''
        # N: serial number : monster name
        # T: template name
        # G: symbol 
        # C: color
        # I: speed : hit points : vision : armor class : alertness
        # W: depth : rarity : unused (always 0) : experience for kill
        # B: attack method : attack effect : damage
        # S: spell frequency
        # S: spell type | spell type | etc
        # F: flag | flag | etc
        # -F: flag | flag | etc
        # D: Description
        # drop: tval : sval : percent drop chance : min : max
        # drop-artifact: name
        # mimic: tval : sval
    '''
adapters['monster.txt'] = OrderedDict((
        ('name', ('N', 1)),
        ('ascii', ('G', 0)),
        ('color', ('C', 0)),
        ('genus', ('T', 0)),
        ('hit points', ('I', 1)),
        ('ac', ('I', 3)),
        ('attacks', ('B',0)),
        ('speed', ('I', 0)),
        ('vision', ('I', 2)),
        ('alertness', ('I', 4)),
        ('depth', ('W', 0)),
        ('rarity', ('W', 1)),
        ('experience to kill', ('W', 3)),
        ('flags', ('F',0)),
        ('remove flags', ('-F',0)),
        ('spells', ('S',0)),
        ('description', ('D', 0)),

        ))

templates['object.txt'] = '''
        # N: serial number : & object name~
        # G: symbol : color
        # I: tval : sval
        # W: depth : rarity : weight : cost
        # P: base armor class : base damage : plus to-hit : plus to-dam : plus to-ac
        # A: commonness : min " to " max
        # C: charges
        # M: chance of being generated in a pile : dice for number of items
        # E: effect when used : recharge time (if applicable)
        # F: flag | flag | etc.
        # L: pval : flag | flag | etc.
        # D: description
        '''
adapters['object.txt'] = OrderedDict((
    ('name',    ('N', 1)), 

    ('ascii',   ('G', 0)), 
    ('color',   ('G', 1)), 

    ('depth',   ('W', 0)),
    ('rarity',  ('W', 1)),
    ('weight',  ('W', 2)),
    ('cost',    ('W', 3)),

    ('ac',      ('P', 0)),
    ('damage',  ('P', 1)),
    ('plus hit',('P', 2)),
    ('plus dam',('P', 3)),
    ('plus ac', ('P', 4)),

    ('common depth',    ('A', 0)),
    ('common range',    ('A', 1)),

    ('charges', ('C', 0)),

    ('pile perct',   ('M', 0)),
    ('pile dice',    ('M', 1)),

    ('flags', ('F', 0)),
    ('spell', ('S', 0)),
    ))

templates['monster_base.txt'] = '''
    # N : template name
    # G : default display character
    # M : pain message index
    # F : flag | flag | ...
    # S : spell flag | spell flag | ...
    # D : description
    '''
adapters['monster_base.txt'] = OrderedDict((
    ('name', ('N', 0)), 
    ('ascii', ('G', 0)), 
    ('flags', ('F', 0)),
    ('spell', ('S', 0)),
    ))


color = {
    'd':'black',
    'w':'white',
    's':'slate',
    'o':'orange',
    'r':'red',
    'g':'green',
    'b':'blue',
    'u':'umber',
    'D':'light dark',
    'W':'light slate',
    'P':'light purple',
    'y':'yellow',
    'R':'light red',
    'G':'light green',
    'B':'light blue',
    'U':'light umber',
    'p':'purple',
    'v':'violet',
    't':'teal',
    'm':'mud',
    'Y':'light yellow',
    'i':'magenta-pink',
    'T':'light teal',
    'V':'light violet',
    'I':'light pink',
    'M':'mustard',
    'z':'blue slate',
    'Z':'deep light blue',
}



class Parser(object):

    def parse(self, template):
        
        info = templates[template]
        flags = OrderedDict()
        for line in info.strip().split('\n'):
            flag = line.strip()[2:].split(':')[0].strip()
            values = line.strip()[2:].split(':')[1:]
            flags[flag] = [v.strip() for v in values]

        sentental = flags.keys()[0]

        items = OrderedDict()
        
        current = None
        for line in open(fname):
            if not line.strip() or line.startswith('#'):
                continue

            if line.strip().startswith(sentental + ':'):
                current = line.strip().split(':')[1]
                items[current] = {}

            if current:
                flag = line.strip().split(':')[0]
                values = [v.strip() for v in line.strip().split(':')[1:]]

                # if we have custom handling
                m = '_handle_' + template.split('.')[0] + '_' + flag
                if hasattr(self, m):
                    getattr(self, m)(items[current], flag, values)

                else:
                    if len(values) != len(flags[flag]):
                        raise ValueError(line.strip())

                    if not items[current].get(flag):
                        items[current][flag] = values
                    else:
                        items[current][flag].extend(values)

        return items

    def _handle_monster_S(self, item, flag, values):
        #spells

        value = '-'.join(values)
        if item.get(flag):
            item[flag][0] += ' - ' + value
        else:
            item[flag] = [value]

    def _handle_monster_F(self, item, flag, values):
        #attacks

        value = ''.join(values)
        if item.get(flag):
            item[flag][0] += ' - ' + value
        else:
            item[flag] = [value]

    def _handle_monster_base_F(self, item, flag, values):
        self._handle_monster_F(item, flag, values)

    def _handle_monster_B(self, item, flag, values):
        #flags

        value = '-'.join(values)
        if item.get(flag):
            item[flag][0] += ' - ' + value
        else:
            item[flag] = [value]

    def _handle_monster_D(self, item, flag, values):
        #description

        # cfg file uses ; for new lines
        # parser seperates by :
        value = ':'.join(values).replace(';', '.')
        if item.get(flag):
            item[flag][0] += ' ' + value
        else:
            item[flag] = [value]

class Adapter(object):
    
    def adapt(self, adapter, items):
        
        attrs = adapters[adapter]
        flag, idx = attrs[attrs.keys()[0]]
        
        adapted = OrderedDict()
        
        for item in items.values():
            adapted[item[flag][idx]] = {}
            for key, value in attrs.items():
                if item.get(value[0]):
                    adapted[item[flag][idx]][key] = item[value[0]][value[1]]

        return adapted

    def to_string(self, name, adapted):
        
        l = []
        for item in adapted.values():
            for i, key in enumerate(adapters[name].keys()):
                if i == 0:
                    l.append('[{}]'.format(item[key]))
                elif item.has_key(key):
                    m = '_handle_' + name.split('.')[0] + '_' + key
                    if hasattr(self, m):
                        method = getattr(self, m)
                        l.append('{} : {}'.format(key, method(item[key])))
                    else:
                        l.append('{} : {}'.format(key, item[key]))
            l.append('')
        return '\n'.join(l)

    def _handle_monster_color(self, value):
        return color[value]

    def write(self, name, adapted):
        
        f = open(name.split('.')[0]+ '.cfg', 'w')
        f.write(self.to_string(name, adapted))
        f.close()

    def sort(self, adapted, attr, typ=None):

        def _cmp(a, b):
            if typ:
                a = a.get(attr) and typ(a[attr])
                b = b.get(attr) and typ(b[attr])
                return cmp(a,b)
            else:
                return cmp(a.get(attr), b.get(attr))
            
        d = OrderedDict()
        for value in sorted(adapted.values(), _cmp):
            d[value['name']] = value
        return d

    def histogram(self, adapted, attr, typ=None):
        
        d = OrderedDict()
        for value in self.sort(adapted, attr, typ).values():

            v = value.get(attr)
            if v is not None and typ:
                v = typ(v)

            if d.get(v):
                d[v] += 1
            else:
                d[v] = 1

        return d


if __name__ == '__main__':
    
    fname = 'monster_base.txt'
    p = Parser()
    a = Adapter()
    items = p.parse(fname)
    items = a.adapt(fname, items)
    print a.to_string(fname, items)
    a.write(fname, items)

    #items = a.sort(items, 'speed', int)
    #items = a.histogram(items, 'speed', int)
    #for k,v in items.items():
    #    print k, v



