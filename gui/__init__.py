from common.text import *
from common.logger import logger
# from common.table import TableManager
from common import tool

from utils.camera import BaslerCam
from utils.ocr import OcrEngine
from utils.db import DBManager, NODBManager
from utils.poly import MultiPolyDetector
from utils.plc import PLCManager, DummyPLC
from utils import process

from gui.showwin import ShowWindow
from gui.labelwin import LabelWindow

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as font
import tkinter.filedialog as filedialog
from tkinter import messagebox as mb

from collections import defaultdict
from threading import Thread, Lock
from queue import Queue
from glob import glob
import numpy as np
import traceback
import serial
import time
import json
import os

from json import JSONDecodeError

class MainWindow(tk.Tk):
    def __init__(self, *arg, nodb=False, hand=False, **kwargs):
        super().__init__(*arg, **kwargs)
        self.iconbitmap(ICON_PATH)
        self.title(TITLE)
        
        # 화면 사이즈
        self.state("zoomed")
        self.geometry(f"{self.winfo_screenwidth()//5*2}x{self.winfo_screenheight()//5*2}")
        self.minsize(self.winfo_screenwidth()//5*2, self.winfo_screenheight()//5*2)
        
        # 셋팅값 가져오기
        with open(SETTING_PATH, "r", encoding='utf-8') as f:
            self.setting_dic = json.load(f)
        
        nodb = self.setting_dic["nodb_mode"] if "nodb_mode" in self.setting_dic else nodb
        hand = self.setting_dic["hand_mode"] if "hand_mode" in self.setting_dic else hand
        font_size_factor = self.setting_dic["font_size_factor"] if "font_size_factor" in self.setting_dic else 1080
        
        # 글자크기 조정
        self.win_factor = self.winfo_screenheight() / font_size_factor
        
        # 디자인
        self.logo_img = tk.PhotoImage(file=LOGO_PATH)
        self.__configure()
        self.set_bind()
        
        self.start_button.configure(text="..", command=lambda:time.sleep(0.1))
        
        # 쓰레드 통신용
        self.stop_signal = True
        self.trigger_Q = Queue()
        self.trigger2_Q = Queue()
        self.OKNG_Q = Queue()
        self.control_Q = Queue()
        self.raw_Q = Queue()
        self.analy_Q = Queue()
        self.draw_Q = Queue()
        self.image_Q = Queue()
        self.data_Q = Queue()
        self.db_Q = Queue()
        self.recode_Q = Queue()
        self.thr_lock = Lock() # for serial
        
        # 기타
        self.today = tool.get_time_str(day=True)
        self.make_recode_dir()
        
        if hand:
            mb.showwarning(title="", message="수동모드 활성화\n카메라 노출시간 증가\nPLC 비활성화\nDB비활성화")
        
        # 카메라 로드
        ExposureTime = self.setting_dic["cam_exp_time"] if "cam_exp_time" in self.setting_dic else EXPOSURE_TIME
        try:
            if hand: ExposureTime = 25000
            self.cam = BaslerCam(ExposureTime=ExposureTime, logger=logger, gray_scale=False)
            logger.info("카메라 로드됨")
        except:
            logger.error("카메라 로딩 실패")
            mb.showwarning(title="", message="카메라 로딩 실패")
            self.cam = None
        
        # PLC 로드
        port = self.setting_dic["serial_port"] if "serial_port" in self.setting_dic else SERIAL_PORT
        try:
            if hand:
                self.plc_mng = DummyPLC()
                self.trigger_btn.place(relx=0.9, rely=0.0, relwidth=0.1, relheight=0.1)
            else:
                self.plc_mng = PLCManager(port=port, command_dic=BYTES_DIC)
                logger.info("PLC 로드됨")
        except:
            logger.warn("PLC 로딩 실패")
            mb.showwarning(title="", message="PLC 로딩 실패...\n수동 트리거 버튼 생성")
            self.plc_mng= None
            self.trigger_btn.place(relx=0.9, rely=0.0, relwidth=0.1, relheight=0.1)
        
        # DB 로드
        if nodb: self.db_mng = NODBManager(NODB_PATH)
        else:
            try:
                self.db_mng = DBManager(db_info_path=DB_INFO_PATH, key_path=KEY_PATH, sql_path=SQL_PATH)
                logger.info("DB 로드됨")
            except JSONDecodeError:
                logger.warn("DB 정보 복호화 실패")
                mb.showwarning(title="", message="DB 정보 복호화 실패\n테스트버전으로 전환")
                self.db_mng = NODBManager(NODB_PATH)
                logger.error(traceback.format_exc())
            except:
                logger.warn("DB 로드 실패")
                mb.showwarning(title="", message="DB 로드 실패...\n테스트 DB로 전환.")
                self.db_mng = NODBManager(NODB_PATH)
                logger.error(traceback.format_exc())
            
        
        # 판독자 로드
        self.poly_detector = MultiPolyDetector(IMG_DIR_PATH, JSON_DIR_PATH, logger=logger, 
                                               pick_names=self.db_mng.code2name)
        logger.info("판독자 로드됨")
        
        # code2 데이터 초기화
        self.code2data = defaultdict(lambda:{"ALL":0, "OK":0, "NG":0, "exist":"X"})
        for code in self.db_mng.code2name:
            self.code2data[code]["exist"] = "O" if code in self.poly_detector.names else "X"
        self.update_table()
        print(self.db_mng.code2name)
        print(self.poly_detector.names)
        
        
        # self.label_win = LabelWindow("141592", self.db_mng.code2name["141592"], self.cam, self.plc_mng, 
        #                              self.setting_dic, callback=self.complete_apply)################
        # return
        # 오래걸리는 로딩
        self.ocr_engine = None
        self.load_check_stop = False
        Thread(target=self.load_check, args=(), daemon=True).start()
        Thread(target=self.load_ocr, args=(OCR_MODEL_PATH,), daemon=True).start()
        
        # 자동 DB, GUI 업데이트
        Thread(target=self.auto_update, args=(), daemon=True).start()
        
    #######################################################################
    def load_ocr(self, model_path):
        try:
            self.ocr_engine = OcrEngine(model_path)
            logger.info("Loaded OcrEngine.")
        except:
            self.load_check_stop = True
            mb.showwarning(title="", message="OCR 모델 로딩 실패")
    
    def load_check(self):
        while True:
            time.sleep(0.1)
            if self.load_check_stop: break
            if (self.cam is not None) and (self.ocr_engine is not None):
                self.start_button.configure(text="...", command=lambda:time.sleep(0.1))
                time.sleep(0.3)
                self.start_button.configure(text="▶시작", bg="#334B35", fg="#D9D9D9", command=self.read_mode)
                break
                
        self.load_check_stop = True
        
    #######################################################################
    def update_table(self):
        # 모든 리스트박스 청소
        self.listbox1.delete(0, 'end') # 품목코드
        self.listbox2.delete(0, 'end') # 품목이름
        self.listbox3.delete(0, 'end') # 총 갯수
        self.listbox4.delete(0, 'end') # OK 갯수
        self.listbox5.delete(0, 'end') # NG 갯수
        self.listbox6.delete(0, 'end') # 등록여부
        
        for i, code in enumerate(self.db_mng.code2name):
            self.listbox1.insert(i, code) # 품목코드
            self.listbox2.insert(i, self.db_mng.code2name[code]) # 품목이름
            self.listbox3.insert(i, self.code2data[code]['ALL']) # 총 갯수
            self.listbox4.insert(i, self.code2data[code]['OK']) # OK 갯수
            self.listbox5.insert(i, self.code2data[code]['NG']) # NG 갯수
            self.listbox6.insert(i, self.code2data[code]['exist']) # 등록여부
        
        self.listbox1.insert('end', "None") # 품목코드
        self.listbox2.insert('end', "미분류") # 품목이름
        self.listbox3.insert('end', self.code2data[None]['ALL']) # 총 갯수
        self.listbox4.insert('end', "") # OK 갯수
        self.listbox5.insert('end', "") # NG 갯수
        self.listbox6.insert('end', "") # 등록여부
            
    #######################################################################
    def auto_update(self):
        update_cycle = self.setting_dic["update_cycle"] if "update_cycle" in self.setting_dic else 10
        
        while True:
            time.sleep(update_cycle)
            logger.info("Auto Update!")
            
            # DB, poly reload
            self.db_mng.update_order_today()
            self.poly_detector.update(pick_names=self.db_mng.code2name)
            
            # 날짜 바뀜 체크
            today = tool.get_time_str(day=True)
            if self.today != today:
                self.today = today
                self.code2data = defaultdict(lambda:{"ALL":0, "OK":0, "NG":0, "exist":"X"})
                
            # poly 존재여부 체크
            for code in self.db_mng.code2name:
                self.code2data[code]["exist"] = "O" if code in self.poly_detector.names else "X"
                
            # GUI 적용
            self.update_table()
            
    #######################################################################
#     def select_code(self, event):
#         Thread(target=self.select_code2, args=(), daemon=True).start()
        
#     def select_code2(self):
#         time.sleep(0.01)
#         tup = self.listbox1.curselection()
#         code = None
#         # 선택검사
#         if not tup:
#             self.selected_code = None
#         else:
#             idx = tup[0]
#             name = self.listbox1.get(idx,idx)[0]
#             code = self.db_mng.name2code[name]
            
#         # 실행 여부
#         if not self.stop_signal:
#             mb.showinfo(title="", message="이미 실행 중입니다.\n중지 후에 선택해주세요.")
#             return
        
#         self.selected_code = code
            
#         # GUI 적용
#         self.selected_label.configure(text=name if self.selected_code else "선택안됨")
        
    #######################################################################
    def stop(self):
        logger.info("Stop button clicked.")
        self.stop_signal = True
    
    #######################################################################
    def read_mode(self):
        logger.info("read_mode button clicked.")
        if not self.load_check_stop:
            logger.error("로드 안됐는데 시작 버튼 눌림.")
            return

        # 시작
        self.stop_signal = False
        Thread(target=self.read_thread, args=(), daemon=True).start()

    def read_thread(self):
        tool.clear_Q(self.trigger_Q)
        tool.clear_Q(self.trigger2_Q)
        tool.clear_Q(self.OKNG_Q)
        tool.clear_Q(self.control_Q)
        tool.clear_Q(self.raw_Q)
        tool.clear_Q(self.analy_Q)
        tool.clear_Q(self.draw_Q)
        tool.clear_Q(self.image_Q)
        tool.clear_Q(self.data_Q)
        tool.clear_Q(self.db_Q)
        tool.clear_Q(self.recode_Q)
        
        image_frame_list = [self.image_frame1, self.image_frame2, self.image_frame3, ]
        image_label_list = [self.image_label1, self.image_label2, self.image_label3, ]
        
        Thread(target=process.image_eater, args=(self, image_frame_list, image_label_list), daemon=True).start()
        Thread(target=process.data_eater, args=(self,), daemon=True).start()
        Thread(target=process.sensor_listener, args=(self,), daemon=True).start()
        Thread(target=process.sensor_listener2, args=(self,), daemon=True).start()
        Thread(target=process.snaper, args=(self,), daemon=True).start()
        Thread(target=process.read, args=(self,), daemon=True).start()
        Thread(target=process.analysis, args=(self,), daemon=True).start()
        Thread(target=process.controller, args=(self,), daemon=True).start()
        Thread(target=process.solenoid, args=(self,), daemon=True).start()
        Thread(target=process.draw, args=(self,), daemon=True).start()
        Thread(target=process.recode, args=(self,), daemon=True).start()

        self.start_button.configure(text="...", command=lambda:time.sleep(0.1))
        time.sleep(0.3)
        self.start_button.configure(text="■중지", bg="#4C3232", fg="#D9D9D9", command=self.stop)
        
        # 중지 대기
        while not self.stop_signal: time.sleep(0.1)
        
        # 혹시모를 모든 조명 끄기
        self.plc_mng.write("red_off")
        self.plc_mng.write("yellow_off")
        self.plc_mng.write("green_off")
        self.plc_mng.write("light_off")
        self.plc_mng.write("sol_off")
            
        # GUI 초기화
        self.start_button.configure(text="...", command=lambda:time.sleep(0.1))
        time.sleep(0.3)
        self.start_button.configure(text="▶시작", bg="#334B35", fg="#D9D9D9", command=self.read_mode)
        self.ok_label.configure(text='', bg="#181B34", anchor='center')
        
    #######################################################################
    def add_mode(self, event):
        logger.info("add_mode button clicked.")
        
        # 아직 로드가 안됐을때
        if not self.load_check_stop:
            mb.showinfo(title="", message="잠시만 기다려주세요.")
            return
        
        # 실행중인데 등록하기버튼 눌렸을때
        if not self.stop_signal:
            mb.showinfo(title="", message="■중지 버튼을 먼저 눌러주세요.")
            return
        
        # 코드 가져오기
        tup = self.listbox6.curselection()
        if not tup: return
        idx = tup[0]
        code = self.listbox1.get(idx, idx)[0]
        name = self.listbox2.get(idx, idx)[0]
        if code == "None": return
        
        # 여부 묻기
        answer = mb.askquestion("등록하기", f"{name}\n\n해당 품목을 등록하시겠습니까?")
        if answer == "no": return
        
        # 새창 띄우기
        self.label_win = LabelWindow(code, name, self.cam, self.plc_mng, self.setting_dic, 
                                     callback=self.complete_apply)
    
    def complete_apply(self, code): # 등록하고 나올때
        # poly 판독자 업데이트
        self.poly_detector.update(pick_names=self.db_mng.code2name)
        
        # poly 존재여부 체크
        if code in self.db_mng.code2name:
            self.code2data[code]["exist"] = "O" if code in self.poly_detector.names else "X"
        
        # GUI 적용
        self.update_table()
        
        logger.info(f"{code} 등록완료!")
    
    #######################################################################
    def make_recode_dir(self):
        if not os.path.isdir(SAVE_IMG_DIR): os.mkdir(SAVE_IMG_DIR)
        if not os.path.isdir(SAVE_DEBUG_IMG_DIR): os.mkdir(SAVE_DEBUG_IMG_DIR)
        if not os.path.isdir(SAVE_RAW_IMG_DIR): os.mkdir(SAVE_RAW_IMG_DIR)
        if not os.path.isdir(SAVE_OK_IMG_DIR): os.mkdir(SAVE_OK_IMG_DIR)
        if not os.path.isdir(SAVE_NG_IMG_DIR): os.mkdir(SAVE_NG_IMG_DIR)
        if not os.path.isdir(IMG_DIR_PATH): os.mkdir(IMG_DIR_PATH)
        if not os.path.isdir(JSON_DIR_PATH): os.mkdir(JSON_DIR_PATH)
    
    #######################################################################
    def open_dir(self, event, ok=True):
        tup = self.listbox4.curselection() if ok else self.listbox5.curselection()
        if not tup: return
        
        # 코드 가져오기
        idx = tup[0]
        code = self.listbox1.get(idx, idx)[0]
        
        # 폴더 열기
        dir_path = SAVE_OK_IMG_DIR if ok else SAVE_NG_IMG_DIR
        path = os.path.join(dir_path, code)
        path = os.path.realpath(path)
        if os.path.isdir(path): os.startfile(path)
    
    #######################################################################
    def set_bind(self):
        btn_list = [self.tf_btn1, self.tf_btn2, self.tf_btn3, self.tf_btn4, ]
        frame_list = [self.bottom_frame2, self.bottom_frame3, self.bottom_frame4]
        
        def switch(event, i):
            # 버튼 외관 변경
            for btn in btn_list: btn.configure(bg="#393945", fg="#A6A6A6")
            btn_list[i].configure(bg="#0153B0", fg="#FFFFFF")
            
            # 현재 프레임 변경
            for frame in frame_list: frame.place_forget()
            frame_list[i].place(relx=0.0, rely=0.4, relwidth=1, relheight=0.6)
        
        
        self.tf_btn1.bind("<Button-1>", lambda _:switch(_, 0)) # 판독영상
        self.tf_btn2.bind("<Button-1>", lambda _:switch(_, 1)) # 집계
        self.tf_btn3.bind("<Button-1>", lambda _:switch(_, 2)) # 설정
        # self.tf_btn4.bind("<Button-1>", self.add_mode) # 등록
        
        self.listbox4.bind("<Double-Button-1>", lambda x:self.open_dir(x, ok=True))
        self.listbox5.bind("<Double-Button-1>", lambda x:self.open_dir(x, ok=False))
        self.listbox6.bind("<Double-Button-1>", self.add_mode)
        
        self.trigger_btn.configure(command=lambda:self.trigger_Q.put(1))
        
        # self.listbox1.bind("<Button-1>", self.select_code)
        # self.listbox3.bind("<Double-Button-1>", lambda x:self.open_dir(x, ok=True))
        # self.listbox4.bind("<Double-Button-1>", lambda x:self.open_dir(x, ok=False))
    #######################################################################
    def __configure(self):
        # 배경
        bg_color = "#181B34"
        self.configure(bg=bg_color)
        
        # 제목
        self.title_label = tk.Label(self, bd=0, relief="solid") # "solid"
        self.title_label.place(relx=0.0, rely=0.0, relwidth=1, relheight=0.1)
        self.title_label['font'] = font.Font(family='Helvetica', size=int(50*self.win_factor), weight='bold')
        self.title_label.configure(text='머신비전 판독기', bg='#26262F', fg="#A6A6A6", anchor='center')
        self.logo_label = tk.Label(self, bd=0, relief="solid") # "solid"
        self.logo_label.place(relx=0.0, rely=0.0, relwidth=0.1, relheight=0.1)
        self.logo_label.configure(image=self.logo_img, bg="#26262F")
        
        # 상단프레임
        self.top_frame = tk.Frame(self, bd=1, relief="solid", bg=bg_color)
        self.top_frame.place(relx=0.0, rely=0.1, relwidth=1, relheight=0.3)
        
        # 상단프레임 - 좌측프레임
        self.tf_left_frame = tk.Frame(self.top_frame, bd=1, relief="solid", bg=bg_color)
        self.tf_left_frame.place(relx=0.0, rely=0.0, relwidth=0.2, relheight=1)
        
        # 상단프레임 - 좌측프레임 - 버튼들
        self.tf_btn1 = tk.Label(self.tf_left_frame, bd=1, relief="solid", anchor='center', text='판독\n영상')
        self.tf_btn1.place(relx=0.0, rely=0.0, relwidth=0.5, relheight=0.5)
        self.tf_btn2 = tk.Label(self.tf_left_frame, bd=1, relief="solid", anchor='center', text='집계')
        self.tf_btn2.place(relx=0.5, rely=0.0, relwidth=0.5, relheight=0.5)
        self.tf_btn3 = tk.Label(self.tf_left_frame, bd=1, relief="solid", anchor='center', text='설정')
        self.tf_btn3.place(relx=0.0, rely=0.5, relwidth=0.5, relheight=0.5)
        self.tf_btn4 = tk.Label(self.tf_left_frame, bd=1, relief="solid", anchor='center', text='')
        self.tf_btn4.place(relx=0.5, rely=0.5, relwidth=0.5, relheight=0.5)
        for btn in [self.tf_btn1, self.tf_btn2, self.tf_btn3, self.tf_btn4]:
            btn['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
            btn.configure(bg="#393945", fg="#A6A6A6")
            # btn.configure(bg="#0153B0", fg="#FFFFFF")
        
        # 상단프레임 - OK라벨
        self.ok_label = tk.Label(self.top_frame, relief="solid", bd=1, anchor='center') # "solid"
        self.ok_label.place(relx=0.2, rely=0.0, relwidth=0.35, relheight=1)
        self.ok_label['font'] = font.Font(family='Calibri', size=int(250*self.win_factor), weight='bold')
        self.ok_label.configure(text='OK', bg="#181B34", fg="#00B050")
        # self.ok_label.configure(text='NG', bg="#FF0000", fg="#FFFFFF")
        
        # 상단프레임 - 우측프레임
        self.tf_right_frame = tk.Frame(self.top_frame, bd=1, relief="solid", bg=bg_color)
        self.tf_right_frame.place(relx=0.55, rely=0.0, relwidth=0.45, relheight=1)
        
        # 상단프레임 - 우측프레임 - 라벨들
        self.name_label1 = tk.Label(self.tf_right_frame, anchor="center", text='판독품목', bg="#595959", fg="#FFF")
        self.value_label1 = tk.Label(self.tf_right_frame, anchor="center", text='귤123', bg="#7F7F7F", fg="#FFF")
        self.name_label2 = tk.Label(self.tf_right_frame, anchor="center", text='판독날짜', bg="#595959", fg="#FFF")
        self.value_label2 = tk.Label(self.tf_right_frame, anchor="center", text='12345', bg="#7F7F7F", fg="#FFF")
        self.name_label3 = tk.Label(self.tf_right_frame, anchor="center", text='품목코드', bg="#595959", fg="#FFF")
        self.value_label3 = tk.Label(self.tf_right_frame, anchor="center", text='12345', bg="#7F7F7F", fg="#FFF")
        self.name_label4 = tk.Label(self.tf_right_frame, anchor="center", text='총 개수', bg="#595959", fg="#FFF")
        self.value_label4 = tk.Label(self.tf_right_frame, anchor="center", text='12345', bg="#7F7F7F", fg="#FFF")
        self.name_label5 = tk.Label(self.tf_right_frame, anchor="center", text='OK 개수', bg="#595959", fg="#FFF")
        self.value_label5 = tk.Label(self.tf_right_frame, anchor="center", text='12345', bg="#7F7F7F", fg="#FFF")
        self.name_label6 = tk.Label(self.tf_right_frame, anchor="center", text='NG 개수', bg="#595959", fg="#FFF")
        self.value_label6 = tk.Label(self.tf_right_frame, anchor="center", text='12345', bg="#7F7F7F", fg="#FFF")
        
        self.name_label1.place(relx=0.0, rely=0.125*0, relwidth=1, relheight=0.125)
        self.value_label1.place(relx=0.0, rely=0.125*1, relwidth=1, relheight=0.125)
        self.name_label2.place(relx=0.0, rely=0.125*2, relwidth=0.5, relheight=0.125)
        self.value_label2.place(relx=0.0, rely=0.125*3, relwidth=0.5, relheight=0.125)
        self.name_label3.place(relx=0.0, rely=0.125*4, relwidth=0.25, relheight=0.125)
        self.value_label3.place(relx=0.25, rely=0.125*4, relwidth=0.25, relheight=0.125)
        self.name_label4.place(relx=0.0, rely=0.125*5, relwidth=0.25, relheight=0.125)
        self.value_label4.place(relx=0.25, rely=0.125*5, relwidth=0.25, relheight=0.125)
        self.name_label5.place(relx=0.0, rely=0.125*6, relwidth=0.25, relheight=0.125)
        self.value_label5.place(relx=0.25, rely=0.125*6, relwidth=0.25, relheight=0.125)
        self.name_label6.place(relx=0.0, rely=0.125*7, relwidth=0.25, relheight=0.125)
        self.value_label6.place(relx=0.25, rely=0.125*7, relwidth=0.25, relheight=0.125)
        
        self.name_label1['font'] = font.Font(family='Calibri', size=int(20*self.win_factor), weight='bold')
        self.value_label1['font'] = font.Font(family='Calibri', size=int(20*self.win_factor), weight='bold')
        self.name_label2['font'] = font.Font(family='Calibri', size=int(20*self.win_factor), weight='bold')
        self.value_label2['font'] = font.Font(family='Calibri', size=int(20*self.win_factor), weight='bold')
        self.name_label3['font'] = font.Font(family='Calibri', size=int(20*self.win_factor), weight='bold')
        self.value_label3['font'] = font.Font(family='Calibri', size=int(20*self.win_factor), weight='bold')
        self.name_label4['font'] = font.Font(family='Calibri', size=int(20*self.win_factor), weight='bold')
        self.value_label4['font'] = font.Font(family='Calibri', size=int(20*self.win_factor), weight='bold')
        self.name_label5['font'] = font.Font(family='Calibri', size=int(20*self.win_factor), weight='bold')
        self.value_label5['font'] = font.Font(family='Calibri', size=int(20*self.win_factor), weight='bold')
        self.name_label6['font'] = font.Font(family='Calibri', size=int(20*self.win_factor), weight='bold')
        self.value_label6['font'] = font.Font(family='Calibri', size=int(20*self.win_factor), weight='bold')
        
        # 상단프레임 - 우측프레임 - 시작버튼
        self.start_button = tk.Button(self.tf_right_frame, bd=1)
        self.start_button.place(relx=0.5, rely=0.250, relwidth=0.5, relheight=0.75)
        self.start_button['font'] = font.Font(family='Helvetica', size=int(70*self.win_factor), weight='bold')
        self.start_button.configure(text="▶시작", bg="#334B35", fg="#D9D9D9", command=None)
        # self.start_button.configure(text="■중지", bg="#4C3232", fg="#D9D9D9", command=None)
        
        
        # 하단프레임0(초기화면)
        self.bottom_frame1 = tk.Frame(self, bd=1, relief="solid", bg=bg_color)
        self.bottom_frame1.place(relx=0.0, rely=0.4, relwidth=1, relheight=0.6)
        self.hi_label = tk.Label(self.bottom_frame1, relief="solid", bd=1, anchor='center') # "solid"
        self.hi_label.place(relx=0.0, rely=0.0, relwidth=1, relheight=1)
        self.hi_label['font'] = font.Font(family='Calibri', size=int(50*self.win_factor), weight='bold')
        self.hi_label.configure(text='안녕하세요.', bg=bg_color, fg="#FFF")
        # self.bottom_frame1.place_forget()
        # self.bottom_frame1.place(relx=0.0, rely=0.4, relwidth=1, relheight=0.6)
        
        # 하단프레임1(판독영상)
        self.bottom_frame2 = tk.Frame(self, bd=1, relief="solid", bg=bg_color)
        self.bottom_frame2.place(relx=0.0, rely=0.4, relwidth=1, relheight=0.6)
        self.bottom_frame2.place_forget()
        
        # 하단프레임2(집계)
        self.bottom_frame3 = tk.Frame(self, bd=20, relief=None, bg=bg_color)
        self.bottom_frame3.place(relx=0.0, rely=0.4, relwidth=1, relheight=0.6)
        self.bottom_frame3.place_forget()
        
        # 하단프레임3(설정)
        self.bottom_frame4 = tk.Frame(self, bd=1, relief="solid", bg=bg_color)
        self.bottom_frame4.place(relx=0.0, rely=0.4, relwidth=1, relheight=0.6)
        self.bottom_frame4.place_forget()
        
        # 하단프레임1(판독영상) - 이미지프레임1
        self.image_frame1 = tk.Frame(self.bottom_frame2, bd=1, relief="solid") # "solid"
        self.image_frame1.place(relx=0.0, rely=0.0, relwidth=0.55, relheight=1)
        self.image_label1_ = tk.Label(self.image_frame1, anchor="center", text='No Image')
        self.image_label1_.configure(fg="#fff", bg=bg_color)
        self.image_label1_.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.image_label1 = tk.Label(self.image_frame1)
        self.image_label1.configure(fg="#fff", bg=bg_color)
        self.image_label1.pack(expand=True, fill="both")
        self.image_label1.pack_forget()
        
        # 하단프레임1(판독영상) - 이미지프레임2
        self.temp = tk.Label(self.bottom_frame2, anchor="center", text='제품 이미지', bg="#44546A", fg="#FFF")
        self.temp.place(relx=0.55, rely=0.0, relwidth=0.45, relheight=0.1)
        self.temp['font'] = font.Font(family='Calibri', size=int(25*self.win_factor), weight='bold')
        self.image_frame2 = tk.Frame(self.bottom_frame2, bd=1, relief="solid") # "solid"
        self.image_frame2.place(relx=0.55, rely=0.1, relwidth=0.45, relheight=0.6)
        self.image_label2_ = tk.Label(self.image_frame2, anchor="center", text='No Image')
        self.image_label2_.configure(fg="#fff", bg=bg_color)
        self.image_label2_.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.image_label2 = tk.Label(self.image_frame2)
        self.image_label2.configure(fg="#fff", bg=bg_color)
        self.image_label2.pack(expand=True, fill="both")
        self.image_label2.pack_forget()
        
        # 하단프레임1(판독영상) - 이미지프레임3
        self.temp = tk.Label(self.bottom_frame2, anchor="center", text='날짜 이미지', bg="#44546A", fg="#FFF")
        self.temp.place(relx=0.55, rely=0.7, relwidth=0.45, relheight=0.1)
        self.temp['font'] = font.Font(family='Calibri', size=int(25*self.win_factor), weight='bold')
        self.image_frame3 = tk.Frame(self.bottom_frame2, bd=1, relief="solid") # "solid"
        self.image_frame3.place(relx=0.55, rely=0.8, relwidth=0.45, relheight=0.2)
        self.image_label3_ = tk.Label(self.image_frame3, anchor="center", text='No Image')
        self.image_label3_.configure(fg="#fff", bg=bg_color)
        self.image_label3_.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.image_label3 = tk.Label(self.image_frame3)
        self.image_label3.configure(fg="#fff", bg=bg_color)
        self.image_label3.pack(expand=True, fill="both")
        self.image_label3.pack_forget()
        
        # 하단프레임2(집계) - columns 이름들
        self.detail_col_frame = tk.Frame(self.bottom_frame3, bd=0, relief="solid", bg="#2F324E")
        self.detail_col_frame.place(relx=0.0, rely=0.0, relwidth=1, relheight=0.15)
        self.temp = tk.Label(self.detail_col_frame, text="품목코드", bg="#565C8F", fg="#fff", relief="solid", bd=1)
        self.temp['font'] = font.Font(family='Helvetica', size=int(30*self.win_factor), weight='bold')
        self.temp.place(relx=0.0, rely=0.0, relwidth=0.15, relheight=1)
        self.temp = tk.Label(self.detail_col_frame, text="품목이름", bg="#565C8F", fg="#fff", relief="solid", bd=1)
        self.temp['font'] = font.Font(family='Helvetica', size=int(30*self.win_factor), weight='bold')
        self.temp.place(relx=0.15, rely=0.0, relwidth=0.45, relheight=1)
        self.temp = tk.Label(self.detail_col_frame, text="총 개수", bg="#565C8F", fg="#fff", relief="solid", bd=1)
        self.temp['font'] = font.Font(family='Helvetica', size=int(30*self.win_factor), weight='bold')
        self.temp.place(relx=0.60, rely=0.0, relwidth=0.10, relheight=1)
        self.temp = tk.Label(self.detail_col_frame, text="OK 개수", bg="#565C8F", fg="#fff", relief="solid", bd=1)
        self.temp['font'] = font.Font(family='Helvetica', size=int(30*self.win_factor), weight='bold')
        self.temp.place(relx=0.70, rely=0.0, relwidth=0.10, relheight=1)
        self.temp = tk.Label(self.detail_col_frame, text="NG 개수", bg="#565C8F", fg="#fff", relief="solid", bd=1)
        self.temp['font'] = font.Font(family='Helvetica', size=int(30*self.win_factor), weight='bold')
        self.temp.place(relx=0.80, rely=0.0, relwidth=0.10, relheight=1)
        self.temp = tk.Label(self.detail_col_frame, text="등록여부", bg="#565C8F", fg="#fff", relief="solid", bd=1)
        self.temp['font'] = font.Font(family='Helvetica', size=int(30*self.win_factor), weight='bold')
        self.temp.place(relx=0.90, rely=0.0, relwidth=0.10, relheight=1)
        
        # 하단프레임2(집계) - 테이블들
        self.list_frame = tk.Frame(self.bottom_frame3, bd=0, relief="solid", bg="#2F324E")
        self.list_frame.place(relx=0.0, rely=0.15, relwidth=1, relheight=0.85)
        
        func = lambda x,y:(self.scrollbar.set(x,y),
                           self.listbox1.yview("moveto",x), self.listbox2.yview("moveto",x), 
                           self.listbox3.yview("moveto",x), self.listbox4.yview("moveto",x), 
                           self.listbox5.yview("moveto",x), self.listbox6.yview("moveto",x), )
        self.listbox1 = tk.Listbox(self.list_frame, yscrollcommand=func, bg="#2F324E", fg="#FFF")
        self.listbox1.place(relx=0.0, rely=0.0, relwidth=0.15, relheight=1.0)
        self.listbox1['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
        self.listbox2 = tk.Listbox(self.list_frame, yscrollcommand=func, bg="#2F324E", fg="#FFF")
        self.listbox2.place(relx=0.15, rely=0.0, relwidth=0.45, relheight=1.0)
        self.listbox2['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
        self.listbox3 = tk.Listbox(self.list_frame, yscrollcommand=func, bg="#2F324E", fg="#FFF")
        self.listbox3.place(relx=0.60, rely=0.0, relwidth=0.10, relheight=1.0)
        self.listbox3['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
        self.listbox4 = tk.Listbox(self.list_frame, yscrollcommand=func, bg="#2F324E", fg="#FFF")
        self.listbox4.place(relx=0.70, rely=0.0, relwidth=0.10, relheight=1.0)
        self.listbox4['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
        self.listbox5 = tk.Listbox(self.list_frame, yscrollcommand=func, bg="#2F324E", fg="#FFF")
        self.listbox5.place(relx=0.80, rely=0.0, relwidth=0.10, relheight=1.0)
        self.listbox5['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
        self.listbox6 = tk.Listbox(self.list_frame, yscrollcommand=func, bg="#2F324E", fg="#FFF")
        self.listbox6.place(relx=0.90, rely=0.0, relwidth=0.10, relheight=1.0)
        self.listbox6['font'] = font.Font(family='Helvetica', size=int(40*self.win_factor), weight='bold')
        
        
        # style = ttk.Style(self.list_frame)
        # style.layout('arrowless.Vertical.TScrollbar', 
        #      [('Vertical.Scrollbar.trough',
        #        {'children': [('Vertical.Scrollbar.thumb', 
        #                       {'expand': '1', 'sticky': 'nswe'})],
        #         'sticky': 'ns'})])
        # self.scrollbar = ttk.Scrollbar(self.list_frame, style='arrowless.Vertical.TScrollbar')
        # self.scrollbar.pack(side="right", fill="y")
        
        self.scrollbar = tk.Scrollbar(self.list_frame, orient=tk.VERTICAL)
        self.scrollbar.pack(side="right", fill="y")
        
        
        func = lambda *args:(self.listbox1.yview(*args), self.listbox2.yview(*args), 
                             self.listbox3.yview(*args), self.listbox4.yview(*args), 
                             self.listbox5.yview(*args), self.listbox6.yview(*args), )
        self.scrollbar.config(command=func)
        
#         self.listbox1.bind("<Button-1>", self.select_code)
        
#         self.image_label.bind("<Double-Button-1>", self.popup_show_win)
        
#         # test
        for i in range(20):
            self.listbox1.insert(tk.END, f"사과{i:02d}")
            self.listbox2.insert(tk.END, f"{i:02d}")
            self.listbox3.insert(tk.END, f"{i:02d}")
            # self.listbox4.insert(tk.END, f"{i:02d}")
            # self.listbox5.insert(tk.END, f"{i:02d}")
            
        # 수동 촬영 (PLC 없을때)
        self.trigger_btn = tk.Button(self, bd=1, text="Trigger", command=None)
        self.trigger_btn.place(relx=0.9, rely=0.0, relwidth=0.1, relheight=0.1)
        self.trigger_btn.place_forget()
        
#         # debug 프레임
#         self.debug_frame = tk.Frame(self, bd=0, relief="solid") # "solid"
#         self.debug_frame.place(relx=0.0, rely=0.0, relwidth=0.3, relheight=0.1)
        
#         self.debug_label1 = tk.Label(self.debug_frame, text='')
#         self.debug_label1.place(relx=0.0, rely=0.0, relwidth=1, relheight=0.2)
#         self.debug_label1['font'] = font.Font(family='Helvetica', size=int(12*self.win_factor), weight='bold')
#         self.debug_label1.configure(text='', bg='#008', fg="#fff", anchor='w')
        
#         self.debug_label2 = tk.Label(self.debug_frame, text='')
#         self.debug_label2.place(relx=0.0, rely=0.2, relwidth=1, relheight=0.2)
#         self.debug_label2['font'] = font.Font(family='Helvetica', size=int(12*self.win_factor), weight='bold')
#         self.debug_label2.configure(text='', bg='#008', fg="#fff", anchor='w')
        
#         self.debug_label3 = tk.Label(self.debug_frame, text='')
#         self.debug_label3.place(relx=0.0, rely=0.4, relwidth=1, relheight=0.2)
#         self.debug_label3['font'] = font.Font(family='Helvetica', size=int(12*self.win_factor), weight='bold')
#         self.debug_label3.configure(text='', bg='#008', fg="#fff", anchor='w')
        
#         self.debug_label4 = tk.Label(self.debug_frame, text='')
#         self.debug_label4.place(relx=0.0, rely=0.6, relwidth=1, relheight=0.2)
#         self.debug_label4['font'] = font.Font(family='Helvetica', size=int(12*self.win_factor), weight='bold')
#         self.debug_label4.configure(text='', bg='#008', fg="#fff", anchor='w')
        
#         self.debug_label5 = tk.Label(self.debug_frame, text='')
#         self.debug_label5.place(relx=0.0, rely=0.8, relwidth=1, relheight=0.2)
#         self.debug_label5['font'] = font.Font(family='Helvetica', size=int(12*self.win_factor), weight='bold')
#         self.debug_label5.configure(text='', bg='#008', fg="#fff", anchor='center')