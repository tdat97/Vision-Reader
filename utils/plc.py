from threading import Lock
import serial
import time

class PLCManager:
    def __init__(self, port, cmd_dic):
        self.thr_lock = Lock()
        self.cmd_dic = cmd_dic
        self.ser = serial.Serial(
                    port=port, 
                    baudrate = 9600,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=0.1
                    )
        
    def write(self, cmd, read_num=13):
        self.thr_lock.acquire()
        self.ser.write(self.cmd_dic[cmd])
        self.ser.read(7)
        self.thr_lock.release()
    
    def read(self, cmd, read_num=13):
        self.thr_lock.acquire()
        self.ser.read_all()
        self.ser.write(self.cmd_dic[cmd])
        read_out = self.ser.read(read_num)
        self.thr_lock.release()
        value = int(read_out[-3:-1].decode('ascii'), 16)
        return value
        

class DummyPLC:
    def __init__(self, *args, **kargs):
        pass
    
    def write(self, *args, **kargs):
        return 0
    
    def read(self, *args, **kargs):
        return 0
