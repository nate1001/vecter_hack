
from collections import OrderedDict


class Messenger(object):
#XXX bases can overwrite signals of one another depending on 
#    which order they are in the var __bases__.

#FIXME signal will overwrite existing attrs
#   need to figure out how to get attr list of all bases 

    def __init__(self):

        self.events = {}

        for cls in list(self.__class__.__bases__) + [self.__class__]:
            if hasattr(cls, '__signals__'):
                for signal in cls.__signals__:
                    self.events[signal.name] = Event(signal.name, signal.args)


class Signal(object):
    
    def __init__(self, name, args, doc=None):
        self.name = name
        self.args = args
        self.doc = doc

    def __repr__(self):
        return "<Signal {}>".format(self.name)

class Event(object):

    def __init__(self, name, args):
        if not (isinstance(args, tuple) or isinstance(args, list)):
            raise TypeError("arguments for event {} must be a sequence not a {}".format(name, type(args)))
        self.__handlers = []
        self.name = name
        self.args = args

    def __repr__(self):
        return "<Event {}>".format(self.name)

    def connect(self, handler):
        self.__handlers.append(handler)
        return self

    def disconnect(self, handler):
        self.__handlers.remove(handler)
        return self

    def emit(self, *args, **kwargs):

        if len(args) != len(self.args):
            raise ValueError('incorrect amount of arguments {} for signal {}'.format(repr(args), repr(self.name)))
        
        for handler in self.__handlers:
            #try:
                handler(*args, **kwargs)
            #FIXME when this pops some how it recurses one time ???
            #except TypeError, e:
            #    raise TypeError("Bad argument count for handler {} from {}. original error: {}".format(
            #        repr(handler), self, str(e)))
                
                

    def clear(self):
        '''Remove all handlers from Event.'''
        self.__handlers = []

    def rebroadcast(self, obj):
        '''Clone signal to object and set a private handler to emit when orignal event fires.'''

        #XXX should check if new object is Messenger type
        
        name = '__on_' + self.name
        event = Event(self.name, self.args)
        events = obj.events

        setattr(events, name, lambda *x, **y: event.emit(*x, **y))

        self.connect(getattr(obj, name))
        setattr(obj, self.name, event)



registered_commands = OrderedDict()
def register_command(group, name, key):
    '''Decorator for registering key and action names.'''
    def decorator(func):
        if not registered_commands.has_key(group):
            registered_commands[group] = OrderedDict()
        registered_commands[group][key] = (name, func.func_name)
        return func
    return decorator


if __name__ == '__main__':
    
    class Stuff(Messenger):

        __signals__ = [
            Signal('clicked', ('arg1',))
        ]


    class OtherStuff(Messenger):

        __signals__ = [
            Signal('pressed', ('arg1',))
        ]

    class Foo(Stuff, OtherStuff):


        def __init__(self):
            print 3

            #Stuff.__init__(self)
            #OtherStuff.__init__(self)
            super(Foo, self).__init__()

    def handler(arg):
        print 11, arg
    
    stuff = Foo()
    stuff.clicked.connect(handler)
    stuff.pressed.connect(handler)
    stuff.clicked.emit('hi!')
