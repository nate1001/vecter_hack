

class Settings(QtCore.QSettings):
    
    def __init__(self, name, default):
        super(Settings, self).__init__(name, name)

        self._dic = {}
        for key in default:
            value, klass, label = default[key]
            self._dic[key] = (klass, label)
            self.setValue(key, value)

    def __getitem__(self, key):
        
        if not self.contains(key):
            raise ValueError(key)

        value = self.value(key)
        klass, label = self._dic[key]
        if klass is int:
            return value.toInt()
        elif klass is str:
            return value.toString()
        elif klass is bool:
            return value.toBool()
        else:
            raise ValueError(klass)

    def __setitem__(self, key, value):
        if not self.contains(key):
            raise ValueError(key)
        self.setValue(key, value)




