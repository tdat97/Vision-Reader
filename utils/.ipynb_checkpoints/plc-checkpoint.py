from threading import Lock
import serial

class PLCManager:
    def __init__(self, port, command_dic):
        self.thr_lock = Lock()
        
    def write(self):
        pass

class DummyPLC:
    def __init__(self, *args, **kargs):
        pass
    
    def write(self, *args, **kargs):
        return 0
