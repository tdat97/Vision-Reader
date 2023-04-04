from gui.labelwin import LabelWindow
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

class AddWindow(tk.Toplevel):
    def __init__(self, code, name, cam, plc_mng, setting_dic, *args, logo_img_tk=None, callback=None, **kwargs):
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
        self.logo_img_tk = logo_img_tk
        
        # images
        self.image1 = None
        self.image2 = None
        self.image3 = None
        # polys
        self.poly1 = None
        self.poly2 = None
        # M
        self.M1 = None
        self.M2 = None
        
        self.auto_stopper = process.Stopper()
        
        # GUI 및 bind
        self.__configure()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.set_bind()
        
        # 항상 실행
        self.stop_signal = False
        self.trigger_Q = Queue()
        self.trigger2_Q = Queue() # 에러방지용
        self.raw_Q = Queue()
        self.image_Q = Queue()
        self.recode_Q = Queue()
        image_frame_list = [self.tf1_frame, self.tf2_frame, self.tf3_frame, ]
        image_label_list = [self.tf1f_label, self.tf2f_label, self.tf3f_label, ]
        Thread(target=process.image_eater, args=(self, image_frame_list, image_label_list), daemon=True).start()
        Thread(target=process.snaper, args=(self,), daemon=True).start()
        Thread(target=process.find_poly_thread, args=(self,), daemon=True).start()
        Thread(target=process.recode, args=(self,), daemon=True).start()
        
###########################################################################################
    def stop(self):
        self.stop_signal = True
        time.sleep(0.1)
        self.destroy()

    def on_closing(self):
        Thread(target=self.stop, args=(), daemon=True).start()

###########################################################################################
    def auto_cam(self, switch_on):
        if switch_on:
            self.auto_stopper.stop_signal = False
            Thread(target=process.sensor_listener, args=(self, self.auto_stopper), daemon=True).start()
        else:
            self.auto_stopper.stop_signal = True
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
        
        self.bf_btn4.configure(bg="#393945", fg="#A6A6A6")
        
###########################################################################################
    def submit(self):
        if self.image1 is None or self.image2 is None:
            mb.showwarning(title="", message="촬영되지 않았습니다.")
            return
        
        answer = mb.askquestion("등록하기", f"해당 품목을 등록하시겠습니까?")
        if answer == "no": return
            
        
        obj_poly = self.poly1
        date_poly = self.poly2
        img = self.image1
        
        # 날짜 poly 변환
        if date_poly is not None:
            obj_poly, date_poly = obj_poly.astype(np.float32), date_poly.astype(np.float32)
            h, w = self.image2.shape[:2]
            pos = np.float32([[0,0], [w,0], [w,h], [0,h]])
            M = cv2.getPerspectiveTransform(pos, obj_poly)
            
            date_poly = cv2.perspectiveTransform(date_poly.reshape(-1,1,2), M).reshape(-1,2)
        
        # json 저장
        path = os.path.join(JSON_DIR_PATH, f"{self.code}.json")
        if date_poly is not None:
            tool.poly2json(path, ["object", "date"], [obj_poly, date_poly])
        else:
            tool.poly2json(path, ["object"], [obj_poly])

        # img 저장
        path = os.path.join(IMG_DIR_PATH, f"{self.code}.png")
        tool.imwrite(path, img)

        # 메인창 GUI업데이트
        self.callback(self.code)
        
        self.on_closing()
        # self.destroy()

###########################################################################################
    def image_update(self):
        # step1
        image1 = self.image1.copy() if self.image1 is not None else None
        poly1 = self.poly1.astype(np.int32) if self.poly1 is not None else None
        if image1 is not None and self.poly1 is not None:
            self.image2, _ = tool.get_crop_img_and_M(image1, self.poly1)
        else: self.image2 = None
        cv2.polylines(image1, [poly1], True, (255,255,0), thickness=5)
        # step2
        image2 = self.image2.copy() if self.image2 is not None else None
        poly2 = self.poly2.astype(np.int32) if self.poly2 is not None else None
        if image2 is not None and self.poly2 is not None:
            self.image3, _ = tool.get_crop_img_and_M(image2, self.poly2)
        else: self.image3 = None
        cv2.polylines(image2, [poly2], True, (255,255,0), thickness=5)
        
        self.image_Q.put([image1, image2, self.image3])
    
    def apply_poly(self, poly, n):
        if n==0: self.poly1 = poly
        else: self.poly2 = poly
        
        self.image_update()
        
    def reset(self):
        self.image1, self.image2, self.image3 = None, None, None
        self.poly1, self.poly2 = None, None
        self.image_Q.put([None, None, None])
        
    def date_on_off(self, switch_on):
        if switch_on: self.poly2 = np.array([[0,0], [50,0], [50,50], [0,50]])
        else: self.poly2 = None
        
        self.image_update()
        
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
        btn_list = [self.bf_btn3, self.bf_btn4, self.bf_btn5, self.bf_btn6, ]
        for btn in btn_list:
            btn.bind("<Button-1>", on_push)
            btn.bind("<ButtonRelease-1>", on_leave)
        
        # 스위칭 모션 부여
        self.bf_btn1.bind("<Button-1>", switch)
        self.bf_btn2.bind("<Button-1>", switch)
        
        # 날짜유무 스위칭 기능
        self.bf_btn1.switch_on = False
        self.bf_btn1.do_switch_func = self.date_on_off
        # self.bf_btn1.do_switch_func(self.bf_btn1.switch_on)
        
        # 자동촬영 스위칭 기능
        self.bf_btn2.switch_on = False
        self.bf_btn2.do_switch_func = self.auto_cam
        self.bf_btn2.do_switch_func(self.bf_btn2.switch_on)
        
        # 수동촬영 버튼 기능
        self.bf_btn3.do_button = lambda:self.trigger_Q.put(1)
        # 파일열기 버튼 기능
        self.bf_btn4.do_button = self.open_file
        # 초기화 버튼 기능
        self.bf_btn5.do_button = self.reset
        # 등록완료 버튼 기능
        self.bf_btn6.do_button = self.submit
        
        def rotate_poly(n):
            if self.bf_btn2.switch_on:
                mb.showwarning(title="", message="자동촬영을 종료해주세요.")
                return
            
            if n == 0 and self.poly1 is not None:
                self.poly1 = self.poly1[[3,0,1,2]]
                self.image_update()
            elif n == 1 and self.poly1 is not None:
                self.poly2 = self.poly2[[3,0,1,2]]
                self.image_update()
            
        def edit_points(n):
            if self.bf_btn2.switch_on:
                mb.showwarning(title="", message="자동촬영을 종료해주세요.")
                return
            
            init_poly = self.poly1 if n==0 else self.poly2
            init_image = self.image1 if n==0 else self.image2
            if init_poly is not None:
                LabelWindow(init_image, points=init_poly, callback=lambda poly:self.apply_poly(poly,n), 
                            logo_img_tk=self.logo_img_tk)
        
        # 좌표수정1
        self.tf1_btn1["command"] = lambda:edit_points(0)
        # 회전1
        self.tf1_btn2["command"] = None
        # 좌표수정2
        self.tf2_btn1["command"] = lambda:edit_points(1)
        # 회전2
        self.tf2_btn2["command"] = lambda:rotate_poly(0)
        # 좌표수정3
        self.tf3_btn1["command"] = None
        # 회전3
        self.tf3_btn2["command"] = lambda:rotate_poly(1)
        
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
        self.logo_label.configure(image=self.logo_img_tk, bg="#26262F")
        self.back_btn = tk.Button(self, bd=1, text="뒤로\n가기", command=self.on_closing)
        self.back_btn.place(relx=0.9, rely=0.0, relwidth=0.1, relheight=0.1)
        self.back_btn['font'] = font.Font(family='Helvetica', size=int(25*self.win_factor), weight='bold')
        self.back_btn.configure(bg="#393945", fg="#A6A6A6")
        
        
        # 상단 프레임1
        self.top1_frame = tk.Frame(self, bd=1, relief="solid", bg=bg_color)
        self.top1_frame.place(relx=0.0, rely=0.1, relwidth=0.33, relheight=0.6)
        
        # 상단 프레임1 - 제목라벨
        self.tf1_label = tk.Label(self.top1_frame, bd=0, relief="solid") # "solid"
        self.tf1_label.place(relx=0.0, rely=0.0, relwidth=1, relheight=0.1)
        self.tf1_label['font'] = font.Font(family='Helvetica', size=int(25*self.win_factor), weight='bold')
        self.tf1_label.configure(bg="#565C8F", fg="#FFF", text='전체 이미지')
        
        # 상단 프레임1 - 이미지프레임
        self.tf1_frame = tk.Frame(self.top1_frame, bd=1, relief="solid", bg=bg_color)
        self.tf1_frame.place(relx=0.0, rely=0.1, relwidth=1, relheight=0.7)
        
        # 상단 프레임1 - 이미지프레임 - 이미지라벨
        self.tf1f_label_ = tk.Label(self.tf1_frame, anchor="center", text='No Image')
        self.tf1f_label_.configure(fg="#fff", bg=bg_color)
        self.tf1f_label_.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.tf1f_label = tk.Label(self.tf1_frame)
        self.tf1f_label.configure(bg=bg_color)
        self.tf1f_label.pack(expand=True, fill="both")
        self.tf1f_label.pack_forget()
        
        # 상단 프레임1 - 수정버튼
        self.tf1_btn1 = tk.Button(self.top1_frame, bd=1, text="좌표수정", command=None)
        self.tf1_btn1.place(relx=0.0, rely=0.8, relwidth=0.5, relheight=0.2)
        self.tf1_btn1['font'] = font.Font(family='Helvetica', size=int(35*self.win_factor), weight='bold')
        self.tf1_btn1.configure(bg="#393945", fg="#A6A6A6", activebackground="#0153B0", activeforeground="#FFF")
        self.tf1_btn2 = tk.Button(self.top1_frame, bd=1, text="", command=None)
        self.tf1_btn2.place(relx=0.5, rely=0.8, relwidth=0.5, relheight=0.2)
        self.tf1_btn2['font'] = font.Font(family='Helvetica', size=int(35*self.win_factor), weight='bold')
        self.tf1_btn2.configure(bg="#393945", fg="#A6A6A6", activebackground="#0153B0", activeforeground="#FFF")
        
        
        # 상단 프레임2
        self.top2_frame = tk.Frame(self, bd=1, relief="solid", bg=bg_color)
        self.top2_frame.place(relx=0.33, rely=0.1, relwidth=0.33, relheight=0.6)
        
        # 상단 프레임2 - 제목라벨
        self.tf2_label = tk.Label(self.top2_frame, bd=0, relief="solid") # "solid"
        self.tf2_label.place(relx=0.0, rely=0.0, relwidth=1, relheight=0.1)
        self.tf2_label['font'] = font.Font(family='Helvetica', size=int(25*self.win_factor), weight='bold')
        self.tf2_label.configure(bg="#565C8F", fg="#FFF", text='제품 이미지')
        
        # 상단 프레임2 - 이미지프레임
        self.tf2_frame = tk.Frame(self.top2_frame, bd=1, relief="solid", bg=bg_color)
        self.tf2_frame.place(relx=0.0, rely=0.1, relwidth=1, relheight=0.7)
        
        # 상단 프레임2 - 이미지프레임 - 이미지라벨
        self.tf2f_label_ = tk.Label(self.tf2_frame, anchor="center", text='No Image')
        self.tf2f_label_.configure(fg="#fff", bg=bg_color)
        self.tf2f_label_.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.tf2f_label = tk.Label(self.tf2_frame)
        self.tf2f_label.configure(bg=bg_color)
        self.tf2f_label.pack(expand=True, fill="both")
        self.tf2f_label.pack_forget()
        
        # 상단 프레임2 - 수정버튼
        self.tf2_btn1 = tk.Button(self.top2_frame, bd=1, text="좌표수정", command=None)
        self.tf2_btn1.place(relx=0.0, rely=0.8, relwidth=0.5, relheight=0.2)
        self.tf2_btn1['font'] = font.Font(family='Helvetica', size=int(35*self.win_factor), weight='bold')
        self.tf2_btn1.configure(bg="#393945", fg="#A6A6A6", activebackground="#0153B0", activeforeground="#FFF")
        self.tf2_btn2 = tk.Button(self.top2_frame, bd=1, text="회전", command=None)
        self.tf2_btn2.place(relx=0.5, rely=0.8, relwidth=0.5, relheight=0.2)
        self.tf2_btn2['font'] = font.Font(family='Helvetica', size=int(35*self.win_factor), weight='bold')
        self.tf2_btn2.configure(bg="#393945", fg="#A6A6A6", activebackground="#0153B0", activeforeground="#FFF")
        
        
        # 상단 프레임3
        self.top3_frame = tk.Frame(self, bd=1, relief="solid", bg=bg_color)
        self.top3_frame.place(relx=0.66, rely=0.1, relwidth=0.34, relheight=0.6)
        
        # 상단 프레임3 - 제목라벨
        self.tf3_label = tk.Label(self.top3_frame, bd=0, relief="solid") # "solid"
        self.tf3_label.place(relx=0.0, rely=0.0, relwidth=1, relheight=0.1)
        self.tf3_label['font'] = font.Font(family='Helvetica', size=int(25*self.win_factor), weight='bold')
        self.tf3_label.configure(bg="#565C8F", fg="#FFF", text='날짜 이미지')
        
        # 상단 프레임3 - 이미지프레임
        self.tf3_frame = tk.Frame(self.top3_frame, bd=1, relief="solid", bg=bg_color)
        self.tf3_frame.place(relx=0.0, rely=0.1, relwidth=1, relheight=0.7)
        
        # 상단 프레임3 - 이미지프레임 - 이미지라벨
        self.tf3f_label_ = tk.Label(self.tf3_frame, anchor="center", text='No Image')
        self.tf3f_label_.configure(fg="#fff", bg=bg_color)
        self.tf3f_label_.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.tf3f_label = tk.Label(self.tf3_frame)
        self.tf3f_label.configure(bg=bg_color)
        self.tf3f_label.pack(expand=True, fill="both")
        self.tf3f_label.pack_forget()
        
        # 상단 프레임3 - 수정버튼
        self.tf3_btn1 = tk.Button(self.top3_frame, bd=1, text="", command=None)
        self.tf3_btn1.place(relx=0.0, rely=0.8, relwidth=0.5, relheight=0.2)
        self.tf3_btn1['font'] = font.Font(family='Helvetica', size=int(35*self.win_factor), weight='bold')
        self.tf3_btn1.configure(bg="#393945", fg="#A6A6A6", activebackground="#0153B0", activeforeground="#FFF")
        self.tf3_btn2 = tk.Button(self.top3_frame, bd=1, text="회전", command=None)
        self.tf3_btn2.place(relx=0.5, rely=0.8, relwidth=0.5, relheight=0.2)
        self.tf3_btn2['font'] = font.Font(family='Helvetica', size=int(35*self.win_factor), weight='bold')
        self.tf3_btn2.configure(bg="#393945", fg="#A6A6A6", activebackground="#0153B0", activeforeground="#FFF")
        
        
        # 중단 프레임
        self.mid_frame = tk.Frame(self, bd=1, relief="solid", bg=bg_color)
        self.mid_frame.place(relx=0.0, rely=0.7, relwidth=1, relheight=0.1)
        
        # 중단 프레임 - 라벨
        self.mf_label_ = tk.Label(self.mid_frame, fg="#fff", bg="#595959", anchor="center", text='품목 이름')
        self.mf_label_.place(relx=0, rely=0, relwidth=0.2, relheight=1)
        self.mf_label_['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
        self.mf_label = tk.Label(self.mid_frame, fg="#fff", bg="#7F7F7F", anchor="center", text=self.name)
        self.mf_label.place(relx=0.2, rely=0, relwidth=0.8, relheight=1)
        self.mf_label['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
        
        
        # 하단 프레임
        self.bottom_frame = tk.Frame(self, bd=1, relief="solid", bg=bg_color)
        self.bottom_frame.place(relx=0.0, rely=0.8, relwidth=1, relheight=0.2)
        
        # 하단 프레임 - 버튼들
        self.bf_btn1 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='날짜\n유무')
        self.bf_btn1.place(relx=0.1666*0, rely=0.0, relwidth=0.1666, relheight=1)
        self.bf_btn2 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='자동\n촬영')
        self.bf_btn2.place(relx=0.1666*1, rely=0.0, relwidth=0.1666, relheight=1)
        self.bf_btn3 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='수동\n촬영')
        self.bf_btn3.place(relx=0.1666*2, rely=0.0, relwidth=0.1666, relheight=1)
        self.bf_btn4 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='파일\n열기')
        self.bf_btn4.place(relx=0.1666*3, rely=0.0, relwidth=0.1666, relheight=1)
        self.bf_btn5 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='초기화')
        self.bf_btn5.place(relx=0.1666*4, rely=0.0, relwidth=0.1666, relheight=1)
        self.bf_btn6 = tk.Label(self.bottom_frame, bd=1, relief="solid", anchor='center', text='등록\n완료')
        self.bf_btn6.place(relx=0.1666*5, rely=0.0, relwidth=0.1666, relheight=1)
        for btn in [self.bf_btn1, self.bf_btn2, self.bf_btn3, self.bf_btn4, 
                    self.bf_btn5, self.bf_btn6]:
            btn['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
            btn.configure(bg="#393945", fg="#A6A6A6")
            # btn.configure(bg="#0153B0", fg="#FFFFFF")
       