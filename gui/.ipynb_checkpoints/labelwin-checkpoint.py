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
    def __init__(self, code, name, cam, plc_mng, setting_dic, *args, callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.win_factor = self.winfo_screenheight() / 1080
        self.geometry(f'{self.winfo_screenwidth()}x{self.winfo_screenheight()}')
        self.state("zoomed")
        self.title("Sub Window")
        self.focus() # 창 선택해줌
        self.grab_set() # 다른창 못건드림
        
        self.code = code
        self.name = name
        self.cam = cam
        self.plc_mng = plc_mng
        self.setting_dic = setting_dic
        self.callback = callback
        
        self.current_origin_image = None # 등록할때 보관용
        self.current_origin_poly = None
        self.current_M = None
        self.auto_stopper = process.Stopper()
        
        # GUI 및 bind
        self.logo_img = tk.PhotoImage(file=LOGO_PATH)
        self.__configure()
        self.set_bind()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 항상 실행
        self.stop_signal = False
        self.trigger_Q = Queue()
        self.raw_Q = Queue()
        self.image_Q = Queue()
        self.recode_Q = Queue()
        image_frame_list = [self.top_right_frame, ]
        image_label_list = [self.small_image_label, ]
        Thread(target=process.image_eater, args=(self, image_frame_list, image_label_list), daemon=True).start()
        Thread(target=process.snaper, args=(self,), daemon=True).start()
        Thread(target=process.add_processing, args=(self,), daemon=True).start()
        Thread(target=process.recode, args=(self,), daemon=True).start()
        
###########################################################################################
    def stop(self):
        self.stop_signal = True
        time.sleep(0.1)
        self.destroy()

    def on_closing(self):
        Thread(target=self.stop, args=(), daemon=True).start()

###########################################################################################
    def hide_obj(self, switch_on):
        if switch_on:
            self.canv.itemconfig(self.canv.poly_id, state="normal")
            self.canv.itemconfig(self.canv.point_ids[0], state="normal")
            self.canv.itemconfig(self.canv.point_ids[1], state="normal")
            self.canv.itemconfig(self.canv.point_ids[2], state="normal")
            self.canv.itemconfig(self.canv.point_ids[3], state="normal")
        else:
            self.canv.itemconfig(self.canv.poly_id, state="hidden")
            self.canv.itemconfig(self.canv.point_ids[0], state="hidden")
            self.canv.itemconfig(self.canv.point_ids[1], state="hidden")
            self.canv.itemconfig(self.canv.point_ids[2], state="hidden")
            self.canv.itemconfig(self.canv.point_ids[3], state="hidden")

###########################################################################################
    def auto_cam(self, switch_on):
        if switch_on:
            self.auto_stopper.stop_signal = False
            Thread(target=process.sensor_listener, args=(self, self.auto_stopper), daemon=True).start()
        else:
            self.auto_stopper.stop_signal = True

###########################################################################################
    def set_bind(self):
        def on_push(event):
            if not hasattr(event.widget, 'do_button'): return
            event.widget.configure(bg="#0153B0", fg="#FFFFFF")
            event.widget.do_button()

        def on_leave(event):
            if not hasattr(event.widget, 'do_button'): return
            event.widget.configure(bg="#393945", fg="#A6A6A6")
            
        def switch(event):
            if not hasattr(event.widget, 'switch_on'): return
            if not hasattr(event.widget, 'do_switch_func'): return
        
            # 스위치
            event.widget.switch_on ^= True
            
            # 켜져 있다면
            if event.widget.switch_on:
                event.widget.configure(bg="#0153B0", fg="#FFFFFF")
                event.widget.do_switch_func(event.widget.switch_on)
            else:
                event.widget.configure(bg="#393945", fg="#A6A6A6")
                event.widget.do_switch_func(event.widget.switch_on)

        # 클릭모션 부여
        btn_list = [self.bf_btn3, self.bf_btn4, self.bf_btn5, self.bf_btn6, self.bf_btn7, 
                    self.br_btn1, self.br_btn2, self.br_btn3, self.br_btn4, self.br_btn5, self.br_btn6, ]
        for btn in btn_list:
            btn.bind("<Button-1>", on_push)
            btn.bind("<ButtonRelease-1>", on_leave)
        
        # 스위칭 모션 부여
        self.bf_btn1.bind("<Button-1>", switch)
        self.bf_btn2.bind("<Button-1>", switch)
        
        # 날짜유무 스위칭 기능
        self.bf_btn1.switch_on = False
        self.bf_btn1.do_switch_func = self.hide_obj
        self.bf_btn1.do_switch_func(self.bf_btn1.switch_on)
        
        # 자동촬영 스위칭 기능
        self.bf_btn2.switch_on = False
        self.bf_btn2.do_switch_func = self.auto_cam
        self.bf_btn2.do_switch_func(self.bf_btn2.switch_on)
        
        # 수동촬영 버튼 기능
        self.bf_btn3.do_button = lambda:self.trigger_Q.put(1)
        # 파일열기 버튼 기능
        self.bf_btn4.do_button = self.open_file
        # 회전 버튼 기능
        self.bf_btn5.do_button = self.canv.rotate_img
        # 초기화 버튼 기능
        self.bf_btn6.do_button = lambda:(self.canv.reset_items(), self.image_Q.put([None]))
        # 등록완료 버튼 기능
        self.bf_btn7.do_button = self.submit
        
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
        self.title_label.configure(text='등록화면', bg='#26262F', fg="#A6A6A6", anchor='center')
        self.logo_label = tk.Label(self, bd=0, relief="solid") # "solid"
        self.logo_label.place(relx=0.0, rely=0.0, relwidth=0.1, relheight=0.1)
        self.logo_label.configure(image=self.logo_img, bg="#26262F")
        self.back_btn = tk.Button(self, bd=1, text="뒤로\n가기", command=self.on_closing)
        self.back_btn.place(relx=0.9, rely=0.0, relwidth=0.1, relheight=0.1)
        self.back_btn['font'] = font.Font(family='Helvetica', size=int(25*self.win_factor), weight='bold')
        self.back_btn.configure(bg="#393945", fg="#A6A6A6")
        
        # 좌측 프레임
        self.left_frame = tk.Frame(self, bd=1, relief="solid", bg=bg_color)
        self.left_frame.place(relx=0.0, rely=0.1, relwidth=0.7, relheight=0.7)
        
        # Canvas
        self.canv = LabelCanvas(self.left_frame, bg='gray', isrect=False)
        self.canv.place(relx=0.0, rely=0.0, relwidth=1, relheight=1)
        
        # 우측 프레임
        self.right_frame = tk.Frame(self, bd=0, relief="solid", bg=bg_color)
        self.right_frame.place(relx=0.7, rely=0.1, relwidth=0.3, relheight=0.7)
        
        # 우상단 프레임
        self.top_right_frame = tk.Frame(self.right_frame, bd=0, relief="solid", bg=bg_color)
        self.top_right_frame.place(relx=0.0, rely=0.0, relwidth=1, relheight=0.5)
        
        # 우상단 프레임 - 이미지 라벨
        self.small_image_label_ = tk.Label(self.top_right_frame, anchor="center", text='No Image')
        self.small_image_label_.configure(fg="#fff", bg=bg_color)
        self.small_image_label_.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.small_image_label = tk.Label(self.top_right_frame)
        self.small_image_label.configure(bg=bg_color)
        self.small_image_label.pack(expand=True, fill="both")
        self.small_image_label.pack_forget()
        
        # 우하단 프레임
        self.bottom_right_frame = tk.Frame(self.right_frame, bd=0, relief="solid", bg=bg_color)
        self.bottom_right_frame.place(relx=0.0, rely=0.5, relwidth=1, relheight=0.5)
        
        # 우하단 프레임 - 버튼들
        self.br_btn1 = tk.Label(self.bottom_right_frame, bd=1, relief="solid", anchor='center', text='축소')
        self.br_btn1.place(relx=0.0, rely=0.0, relwidth=0.33, relheight=0.43)
        self.br_btn2 = tk.Label(self.bottom_right_frame, bd=1, relief="solid", anchor='center', text='↑')
        self.br_btn2.place(relx=0.33, rely=0.0, relwidth=0.34, relheight=0.43)
        self.br_btn3 = tk.Label(self.bottom_right_frame, bd=1, relief="solid", anchor='center', text='확대')
        self.br_btn3.place(relx=0.67, rely=0.0, relwidth=0.33, relheight=0.43)
        self.br_btn4 = tk.Label(self.bottom_right_frame, bd=1, relief="solid", anchor='center', text='←')
        self.br_btn4.place(relx=0.0, rely=0.43, relwidth=0.33, relheight=0.43)
        self.br_btn5 = tk.Label(self.bottom_right_frame, bd=1, relief="solid", anchor='center', text='↓')
        self.br_btn5.place(relx=0.33, rely=0.43, relwidth=0.34, relheight=0.43)
        self.br_btn6 = tk.Label(self.bottom_right_frame, bd=1, relief="solid", anchor='center', text='→')
        self.br_btn6.place(relx=0.67, rely=0.43, relwidth=0.33, relheight=0.43)
        self.br_label= tk.Label(self.bottom_right_frame, bd=1, relief="solid", anchor='center', text=self.name)
        self.br_label.place(relx=0.0, rely=0.86, relwidth=1, relheight=0.14)
        self.br_label.configure(bg="#595959", fg="#FFF")
        for btn in [self.br_btn1, self.br_btn2, self.br_btn3, self.br_btn4, self.br_btn5, self.br_btn6]:
            btn['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
            btn.configure(bg="#393945", fg="#A6A6A6")
            # btn.configure(bg="#0153B0", fg="#FFFFFF")
        self.br_label['font'] = font.Font(family='Helvetica', size=int(20*self.win_factor), weight='bold')
        
        # 하단 프레임
        self.bottom_frame = tk.Frame(self, bd=1, relief="solid", bg=bg_color)
        self.bottom_frame.place(relx=0.0, rely=0.8, relwidth=1, relheight=0.2)
        
        # 하단 프레임 - 버튼들
        self.bf_btn1 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='날짜\n유무')
        self.bf_btn1.place(relx=0.1428*0, rely=0.0, relwidth=0.1428, relheight=1)
        self.bf_btn2 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='자동\n촬영')
        self.bf_btn2.place(relx=0.1428*1, rely=0.0, relwidth=0.1428, relheight=1)
        self.bf_btn3 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='수동\n촬영')
        self.bf_btn3.place(relx=0.1428*2, rely=0.0, relwidth=0.1428, relheight=1)
        self.bf_btn4 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='파일\n열기')
        self.bf_btn4.place(relx=0.1428*3, rely=0.0, relwidth=0.1428, relheight=1)
        self.bf_btn5 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='회전')
        self.bf_btn5.place(relx=0.1428*4, rely=0.0, relwidth=0.1428, relheight=1)
        self.bf_btn6 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='초기화')
        self.bf_btn6.place(relx=0.1428*5, rely=0.0, relwidth=0.1428, relheight=1)
        self.bf_btn7 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='등록\n완료')
        self.bf_btn7.place(relx=0.1428*6, rely=0.0, relwidth=0.1428, relheight=1)
        for btn in [self.bf_btn1, self.bf_btn2, self.bf_btn3, self.bf_btn4, 
                    self.bf_btn5, self.bf_btn6, self.bf_btn7]:
            btn['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
            btn.configure(bg="#393945", fg="#A6A6A6")
            # btn.configure(bg="#0153B0", fg="#FFFFFF")
        
###########################################################################################
    def open_file(self):
        # 이미지 가져오기, 포커스 고정
        top = tk.Toplevel(self)
        top.grab_set() # 포커스 고정
        top.withdraw() # 숨기기
        filename = filedialog.askopenfilename(initialdir="/", title="Select file",
                                              filetypes=(("image files", "*.png"),
                                                         ("image files", "*.jpg")))
        top.grab_release()
        # top.deiconify()
        top.destroy()
        self.grab_set() # 다시 서브창 포커스
        
        if not filename: return
        try:origin_img_arr = tool.imread(filename)
        except:
            mb.showwarning(title="", message="올바른 파일이 아닙니다.")
            return
        
        # 이미지 적용
        self.raw_Q.put(origin_img_arr)
        # self.apply_img(origin_img_arr)
        
        self.bf_btn4.configure(bg="#393945", fg="#A6A6A6")
        
###########################################################################################
    def submit(self): # 여기선 박스 xyxy
        date_poly = self.canv.get_points_with_img()
        print(date_poly)
        tool.imwrite('./temp/test.png', self.canv.origin_img)
        print(self.canv.origin_img.shape)
        if self.current_origin_poly is None or self.current_origin_image is None or date_poly is None: return
        
        obj_poly = self.current_origin_poly.astype(np.float32)
        inv_M = np.linalg.inv(self.current_M)
        date_poly = cv2.perspectiveTransform(date_poly.reshape(-1,1,2), inv_M).reshape(-1,2)
    
        # json 저장
        path = os.path.join(JSON_DIR_PATH, f"{self.code}.json")
        tool.poly2json(path, ["object", "date"], [obj_poly, date_poly])

        # img 저장
        img = self.current_origin_image
        path = os.path.join(IMG_DIR_PATH, f"{self.code}.png")
        tool.imwrite(path, img)

        # 메인창 GUI업데이트
        self.callback(self.code)
        
        self.on_closing()
        # self.destroy()
