from common import tool

import tkinter as tk
import tkinter.font as font


from threading import Thread, Lock
from PIL import ImageTk, Image
from queue import Queue
import numpy as np
import time
import cv2

class ShowWindow(tk.Toplevel):
    def __init__(self, *args, callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        # window size
        win_height = self.winfo_screenheight()
        win_width = self.winfo_screenwidth()
        self.fsize_factor = np.linalg.norm((win_height, win_width)) / 2202.9071700822983
        # self.geometry(f'{win_width}x{win_height}')
        self.geometry(f"{win_width//2}x{win_height//2}")
        self.state("zoomed")
        self.title("Sub Window")
        
        self.focus() # 창 선택해줌
        self.grab_set() # 다른창 못건드림
        self.protocol("WM_DELETE_WINDOW", self.on_close) # 닫기버튼누를시
        
        self.current_origin_image = None#np.zeros((100,100,3), dtype=np.uint8)
        self.current_image = None
        self.image_Q = Queue()
        self.stop_signal = False
        
        self.callback = callback
        self._configure()
        
        Thread(target=self.image_eater, args=(), daemon=True).start()
        
    def on_close(self):
        self.stop_signal = True
        Thread(target=self.destroy_window, args=(), daemon=True).start()
        
    def destroy_window(self):
        time.sleep(0.1)
        self.destroy()
        
    def _configure(self):
        # 이미지프레임
        self.image_frame = tk.Frame(self, bd=1, relief="solid") # "solid"
        self.image_frame.place(relx=0.0, rely=0, relwidth=1, relheight=1)
        # 이미지프레임 - 이미지
        self.image_label = tk.Label(self.image_frame, anchor="center", text='No Image')
        self.image_label.pack(expand=True, fill="both")
        
    ##################################################### 실시간 이미지 조정
    def image_eater(self): # 쓰레드 # self.image_Q에 있는 이미지 출력
        current_winfo = self.image_frame.winfo_height(), self.image_frame.winfo_width()
        while True:
            time.sleep(0.05)
            if self.stop_signal: break
            last_winfo = self.image_frame.winfo_height(), self.image_frame.winfo_width()

            if current_winfo == last_winfo and self.image_Q.empty(): continue
            if current_winfo != last_winfo: current_winfo = last_winfo
            if not self.image_Q.empty(): self.current_origin_image = self.image_Q.get() # BGR
            if self.current_origin_image is None: continue

            self.current_image, _ = self.fit_img(self.current_origin_image, current_winfo)
            # __auto_resize_img(self)
            # imgtk = ImageTk.PhotoImage(Image.fromarray(self.current_image[:,:,::-1]))
            imgtk = ImageTk.PhotoImage(Image.fromarray(self.current_image))
            self.image_label.configure(image=imgtk)
            self.image_label.image = imgtk

        self.current_origin_image = None #np.zeros((100,100,3), dtype=np.uint8)
        self.current_image = None
        self.image_label.configure(image=None)
        self.image_label.image = None
    
    def fit_img(self, img, size, margin=15):
        wh, ww = size
        wh, ww = wh-margin, ww-margin
        h, w = img.shape[:2]
        magnf_value = min(wh/h, ww/w)
        new_img = cv2.resize(img, dsize=(0,0), fx=magnf_value, fy=magnf_value)
        return new_img, magnf_value
        
        
