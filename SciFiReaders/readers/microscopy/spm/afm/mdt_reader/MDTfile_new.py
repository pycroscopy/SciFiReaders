from abc import ABC

class MDTfile(list):
    def __init__(self,path):
        self.path = path
        pass
        #TODO

class Frame(ABC):
    '''
    Abstract class for frame description in general
    '''

    def smth(self):
        pass

class MDAFrame(Frame):
    pass