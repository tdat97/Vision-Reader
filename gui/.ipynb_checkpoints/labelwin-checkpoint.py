from gui.canvas import LabelCanvas
import tkinter as tk
import tkinter.font as font
import tkinter.filedialog as filedialog

from tkinter import messagebox as mb
from PIL import ImageTk, Image
from threading import Thread, Lock
from queue import Queue
import numpy as np
import time
import cv2
import os

from common import tool
from common.text import *

from utils import process

class LabelWindow(tk.Toplevel):
    def __init__(self, origin_image, *args, points=None, logo_img_tk=None, callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.win_factor = self.winfo_screenheight() / 1080
        self.geometry(f'{self.winfo_screenwidth()}x{self.winfo_screenheight()}')
        self.resizable(False, False)
        self.overrideredirect(True)
        self.state("zoomed")
        self.title("세부조정 창")
        self.focus() # 창 선택해줌
        self.grab_set() # 다른창 못건드림
        
        
        self.callback = callback
        self.logo_img_tk = logo_img_tk
        self.origin_image = origin_image
        self.points = points
        
        # GUI 및 bind
        self.__configure()
        self.set_bind()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
        Thread(target=self.canv.init_canv, args=(self.origin_image, self.points), daemon=True).start()
        
###########################################################################################
    def submit(self): # 여기선 박스 xyxy
        poly = self.canv.get_real_poly()
        self.callback(poly)
        self.destroy()
        
###########################################################################################
    def set_bind(self):
        def on_push(event):
            if not hasattr(event.widget, 'do_button'): return
            event.widget.configure(bg="#0153B0", fg="#FFFFFF")
            event.widget.do_button()

        def on_leave(event):
            if not hasattr(event.widget, 'do_button'): return
            event.widget.configure(bg="#393945", fg="#A6A6A6")
            
        # 클릭모션 부여
        btn_list = [self.br_btn1, self.br_btn2, self.br_btn3, 
                    self.br_btn4, self.br_btn5, self.br_btn6, self.apply_btn]
        for btn in btn_list:
            btn.bind("<Button-1>", on_push)
            btn.bind("<ButtonRelease-1>", on_leave)
        
        # 등록완료 버튼 기능
        self.apply_btn.do_button = self.submit
        # 축소 버튼 기능
        self.br_btn1.do_button = self.canv.zoom_out
        # 위 버튼 기능
        self.br_btn2.do_button = self.canv.move_up
        # 확대 버튼 기능
        self.br_btn3.do_button = self.canv.zoom_in
        # 왼쪽 버튼 기능
        self.br_btn4.do_button = self.canv.move_left
        # 아래 버튼 기능
        self.br_btn5.do_button = self.canv.move_down
        # 오른쪽 버튼 기능
        self.br_btn6.do_button = self.canv.move_right

###########################################################################################
    def __configure(self):
        # 배경
        bg_color = "#181B34"
        self.configure(bg=bg_color)
        
        # 제목
        self.title_label = tk.Label(self, bd=0, relief="solid") # "solid"
        self.title_label.place(relx=0.0, rely=0.0, relwidth=1, relheight=0.1)
        self.title_label['font'] = font.Font(family='Helvetica', size=int(50*self.win_factor), weight='bold')
        self.title_label.configure(text='수정화면', bg='#26262F', fg="#A6A6A6", anchor='center')
        self.logo_label = tk.Label(self, bd=0, relief="solid") # "solid"
        self.logo_label.place(relx=0.0, rely=0.0, relwidth=0.1, relheight=0.1)
        self.logo_label.configure(image=self.logo_img_tk, bg="#26262F")
        self.back_btn = tk.Button(self, bd=1, text="뒤로\n가기", command=self.destroy)
        self.back_btn.place(relx=0.9, rely=0.0, relwidth=0.1, relheight=0.1)
        self.back_btn['font'] = font.Font(family='Helvetica', size=int(25*self.win_factor), weight='bold')
        self.back_btn.configure(bg="#393945", fg="#A6A6A6", activebackground="#0153B0", activeforeground="#FFF")
        
        # Canvas
        self.canv = LabelCanvas(self, bg='gray', isrect=False)
        self.canv.place(relx=0.0, rely=0.1, relwidth=0.7, relheight=0.9)
        
        # 우측 프레임
        self.right_frame = tk.Frame(self, bd=0, relief="solid", bg=bg_color)
        self.right_frame.place(relx=0.7, rely=0.4, relwidth=0.3, relheight=0.3)
        
        # 우측 프레임 - 버튼들
        self.br_btn1 = tk.Label(self.right_frame, bd=1, relief="solid", anchor='center', text='축소')
        self.br_btn1.place(relx=0.0, rely=0.0, relwidth=0.33, relheight=0.43)
        self.br_btn2 = tk.Label(self.right_frame, bd=1, relief="solid", anchor='center', text='↑')
        self.br_btn2.place(relx=0.33, rely=0.0, relwidth=0.34, relheight=0.43)
        self.br_btn3 = tk.Label(self.right_frame, bd=1, relief="solid", anchor='center', text='확대')
        self.br_btn3.place(relx=0.67, rely=0.0, relwidth=0.33, relheight=0.43)
        self.br_btn4 = tk.Label(self.right_frame, bd=1, relief="solid", anchor='center', text='←')
        self.br_btn4.place(relx=0.0, rely=0.43, relwidth=0.33, relheight=0.43)
        self.br_btn5 = tk.Label(self.right_frame, bd=1, relief="solid", anchor='center', text='↓')
        self.br_btn5.place(relx=0.33, rely=0.43, relwidth=0.34, relheight=0.43)
        self.br_btn6 = tk.Label(self.right_frame, bd=1, relief="solid", anchor='center', text='→')
        self.br_btn6.place(relx=0.67, rely=0.43, relwidth=0.33, relheight=0.43)
        for btn in [self.br_btn1, self.br_btn2, self.br_btn3, self.br_btn4, self.br_btn5, self.br_btn6]:
            btn['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
            btn.configure(bg="#393945", fg="#A6A6A6")
            # btn.configure(bg="#0153B0", fg="#FFFFFF")
        
        # 적용하기 버튼
        self.apply_btn = tk.Label(self, bd=1, relief="solid", anchor='center', text='적용하기')
        self.apply_btn.place(relx=0.7, rely=0.8, relwidth=0.3, relheight=0.2)
        self.apply_btn['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
        self.apply_btn.configure(bg="#393945", fg="#A6A6A6")
        # btn.configure(bg="#0153B0", fg="#FFFFFF")

