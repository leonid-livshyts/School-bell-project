class Sensor:
    def __init__(self, name):
        self._name = name
        
    def read(self):
        raise AttributeError("not implemented")
    
    @property
    def name(self):
        return self._name
