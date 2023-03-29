from common.logger import logger
from common.text import *
from common import tool

from collections import defaultdict
from PIL import ImageFont, ImageDraw, Image, ImageTk
from threading import Thread
from functools import reduce
import numpy as np
import tkinter as tk
import traceback
import time
import cv2
import os
import re

class Stopper():
    def __init__(self):
        self.stop_signal = False

##################################################### 실시간 이미지 조정
def image_eater(self, image_frame_list, image_label_list): # 쓰레드 # self.image_Q에 있는 이미지 출력
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
    origin_image_list = []
    last_winfo_list = [(frame.winfo_height(), frame.winfo_width()) for frame in image_frame_list]
    
    try:
        while not self.stop_signal:
            time.sleep(thread_cycle)

            # 현재 프레임 크기 가져오기
            current_winfo_list = [(frame.winfo_height(), frame.winfo_width()) for frame in image_frame_list]

            # GUI 이미지 업데이트 조건 검사
            if current_winfo_list == last_winfo_list and self.image_Q.empty(): continue
            if current_winfo_list != last_winfo_list: last_winfo_list = current_winfo_list
            if not self.image_Q.empty(): origin_image_list = self.image_Q.get() # BGR
            if not origin_image_list: continue
            assert len(origin_image_list) == len(image_frame_list)

            # 이미지 변형
            # imgtk_list = [None, None, None]
            # self.current_origin_image = origin_image_list[0]
            
            for i in range(len(origin_image_list)):
                frame, img, label = image_frame_list[i], origin_image_list[i], image_label_list[i]
                winfo = frame.winfo_height(), frame.winfo_width()
                if winfo == (1,1): continue

                # GUI 이미지 업데이트
                if img is None:
                    # label.configure(image=None)
                    # label.image = None
                    # imgtk_list[i] = None
                    label.pack_forget()
                else:
                    img, _ = fit_img(img[:,:,::-1], winfo)
                    imgtk = ImageTk.PhotoImage(Image.fromarray(img), master=self)
                    label.configure(image=imgtk)
                    label.image = imgtk
                    # imgtk_list[i] = imgtk
                    label.pack(expand=True, fill="both")
                
    
    except Exception as e:
        logger.error("an error in [image_eater]")
        logger.error(traceback.format_exc())
        self.stop_signal = True
        
    # 이미지 없애기
    for label in image_label_list:
        # label.configure(image=None)
        # label.image = None
        label.pack_forget()

    self.current_origin_image = None # 파일 저장용
    
def fit_img(img, size, margin=15):
    wh, ww = size
    wh, ww = wh-margin, ww-margin
    h, w = img.shape[:2]
    magnf_value = min(wh/h, ww/w)
    new_img = cv2.resize(img, dsize=(0,0), fx=magnf_value, fy=magnf_value)
    return new_img, magnf_value

# 실시간 데이터 수정####################################################
def data_eater(self):
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
        
    while not self.stop_signal:
        time.sleep(thread_cycle)
        
        if self.data_Q.empty(): continue    
        code, isok, date = self.data_Q.get()
        
        # 전체 데이터에 추가
        self.code2data[code]["ALL"] += 1
        if code is not None:
            self.code2data[code]["OK"] += isok
            self.code2data[code]["NG"] += not isok
        
        # 세부데이터 업데이트
        self.value_label1.configure(text=self.db_mng.code2name[code] if code else "미탐지 또는 새로운 품목") # 판독품목
        self.value_label2.configure(text=date if date else "") # 판독날짜
        self.value_label3.configure(text=code if code else "None") # 품목코드
        self.value_label4.configure(text=self.code2data[code]["ALL"]) # 총 개수
        self.value_label5.configure(text=self.code2data[code]["OK"] if code else "") # OK 개수
        self.value_label6.configure(text=self.code2data[code]["NG"] if code else "") # NG 개수
        
        # 테이블 업데이트
        self.update_table()

        # OK, NG
        if isok: self.ok_label.configure(text='OK', bg="#181B34", fg="#00B050")
        else: self.ok_label.configure(text='NG', bg="#FF0000", fg="#FFFFFF")

#######################################################################
def sensor_listener(self, mini_stopper=None):
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
    value_Q = [False]*4 # 센서 안정성을 위한것
    sensor_lock = False
    
    while not self.stop_signal:
        time.sleep(thread_cycle)
        if mini_stopper and mini_stopper.stop_signal: break
        
        # 센서 값 읽기
        value = self.plc_mng.write("get_sensor1") # True or False
        value_Q = value_Q[1:] + [value]
        
        # 잠금이 풀려있고 센서 감지 됐을 경우
        if not sensor_lock and sum(value_Q):
            self.trigger_Q.put(1)
            sensor_lock = True
        elif sum(value_Q) == 0:
            sensor_lock = False

#######################################################################
def snaper(self):
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
    hand_mode = self.setting_dic["hand_mode"] if "hand_mode" in self.setting_dic else False
    
    while not self.stop_signal:
        time.sleep(thread_cycle)
        if self.trigger_Q.empty(): continue
        
        # 트리거 받으면 촬영
        self.trigger_Q.get()
        self.plc_mng.write("light_on")
        time.sleep(0.07)
        img = self.cam.get_image()
        self.plc_mng.write("light_off")
        self.raw_Q.put(img)
        
#######################################################################
def raw_Q2image_Q(self): # 촬영모드 전용
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
    
    while not self.stop_signal:
        time.sleep(thread_cycle)
        
        if self.raw_Q.empty(): continue
        self.image_Q.put(self.raw_Q.get())
        
#######################################################################
def read(self):
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
    
    try:
        while not self.stop_signal:
            time.sleep(thread_cycle)
            if self.raw_Q.empty(): continue

            # get image
            img = self.raw_Q.get()
            if img is None: self.analy_Q.put([None, None, None, None])
            
            # Detect Polys
            start_time = time.time()
            best_obj, dst_polys, crop_imgs = self.poly_detector.predict(img)
            end_time = time.time()
            logger.info(f"Detect Time : {end_time-start_time:.3f}")
            
            self.analy_Q.put([img, best_obj, dst_polys, crop_imgs])
            
    except Exception as e:
        logger.error("an error in [read]")
        logger.error(traceback.format_exc())
        self.stop_signal = True

#######################################################################
def policy_check(text, today):
    assert type(text) == str
    
    # 6글자 보다 작으면 NG
    if len(text) < 6: return False
    
    # 22.22.22 꼴이 아니면 False
    date = re.findall("[0-9]{2}[^0-9][0-9]{2}[^0-9][0-9]{2}", text)
    if not date: return False

    # 현재 날짜보다 과거이면 False
    date = date[0]
    date = re.sub(r'[^0-9]', '', date)
    today = re.sub(r'[^0-9]', '', today)[2:]
    if today > date: return False
    
    return True
    
def analysis(self):
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
    use_alram = self.setting_dic["alram"] if "alram" in self.setting_dic else False
    debug_mode = self.setting_dic["debug_mode"] if "debug_mode" in self.setting_dic else True
    
    try:
        while not self.stop_signal:
            time.sleep(thread_cycle)
            if self.analy_Q.empty(): continue

            # poly 결과 받기
            img, best_obj, dst_polys, crop_imgs = self.analy_Q.get()
            
            #
            isok = True
            date_str = None
            
            # 미탐지한 경우
            if best_obj is None:
                isok = False
            # 날짜있는 제품인 경우
            elif "date" in best_obj.labels:
                i = best_obj.labels.index("date")
                date_img = crop_imgs[i]
                date_str = self.ocr_engine(date_img)
                isok = policy_check(date_str, self.today)
                
            # 경광등
            if isok: self.control_Q.put("green")
            else: self.control_Q.put("red")
            
            code = best_obj.name if best_obj else None
            
            self.OKNG_Q.put(isok)
            self.data_Q.put([code, isok, date_str])
            self.draw_Q.put([img, isok, date_str, best_obj, dst_polys, crop_imgs]) # recode 때문에 isok필요
        
    except Exception as e:
        logger.error("an error in [analysis]")
        logger.error(traceback.format_exc())
        self.stop_signal = True
        
#######################################################################
def controller(self, on_off_time={"red":3, "yellow":2, "green":1, "sol":1}):
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
    on_off_time = self.setting_dic["on_off_time"] if "on_off_time" in self.setting_dic else on_off_time
    
    tps = int(1/thread_cycle)
    time_value_dic = {name:0 for name in on_off_time}
    try:
        while not self.stop_signal:
            time.sleep(thread_cycle)

            for name in time_value_dic:
                # 남은 시간이 1일때 끄기
                if time_value_dic[name] == 1:
                    self.plc_mng.write(f"{name}_off")

                # 사이클마다 1씩 감소
                if time_value_dic[name]:
                    time_value_dic[name] -= 1

            if self.control_Q.empty(): continue

            # 켜고, 시간 조정
            name = self.control_Q.get() # red, yellow, green
            self.plc_mng.write(f"{name}_on")
            time_value_dic[name] = on_off_time[name] * tps
    
    except Exception as e:
        logger.error("an error in [controller]")
        logger.error(traceback.format_exc())
        self.stop_signal = True
        
#######################################################################
def sensor_listener2(self):
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
    value_Q = [False]*4 # 센서 안정성을 위한것
    sensor_lock = False
    
    while not self.stop_signal:
        time.sleep(thread_cycle)
        
        # 센서 값 읽기
        value = self.plc_mng.write("get_sensor2") # True or False
        value_Q = value_Q[1:] + [value]
        
        # 잠금이 풀려있고 센서 감지 됐을 경우
        if not sensor_lock and sum(value_Q):
            self.trigger2_Q.put(1)
            sensor_lock = True
        elif sum(value_Q) == 0:
            sensor_lock = False

def solenoid(self):
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
    
    while not self.stop_signal:
        time.sleep(thread_cycle)
        if not self.trigger2_Q.empty() and not self.OKNG_Q.empty(): continue
        
        isok = self.OKNG_Q.get()
        self.trigger2_Q.get()
        
        if not isok:
            self.control_Q.put("sol")
    
#######################################################################
def draw(self):
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
    
    # 색깔 초기화
    fc = lambda x,y:np.random.randint(x,y)
    colors = [(fc(50,255), fc(50,255), fc(0,150)) for _ in range(len(self.poly_detector.names))]
    color_dic = dict(zip(self.poly_detector.names, colors))
    font_cv = cv2.FONT_HERSHEY_SIMPLEX
    font_pil = ImageFont.truetype(FONT_PATH, 40)
    
    try:
        while not self.stop_signal:
            time.sleep(thread_cycle)
            if self.draw_Q.empty(): continue
            
            img, isok, date_str, best_obj, dst_polys, crop_imgs = self.draw_Q.get()

            # 미탐지인 경우
            if best_obj is None:
                self.image_Q.put([img, None, None])
                self.recode_Q.put([img, isok, None])
                continue
            
            #
            code = best_obj.name
            label2idx = dict(zip(best_obj.labels, range(len(best_obj.labels))))
            dst_polys = dst_polys.astype(np.int32)
            obj_img, date_img = None, None
            
            # draw all over
            # draw poly
            color = color_dic[code]
            cv2.polylines(img, dst_polys, True, color, thickness=5)
            
            # draw number
            for dst_poly in dst_polys:
                cv2.putText(img, "1", dst_poly[0], font_cv, fontScale=2, thickness=2, color=(255,0,255))
                cv2.putText(img, "2", dst_poly[1], font_cv, fontScale=2, thickness=2, color=(255,0,255))
                cv2.putText(img, "3", dst_poly[2], font_cv, fontScale=2, thickness=2, color=(255,0,255))
                cv2.putText(img, "4", dst_poly[3], font_cv, fontScale=2, thickness=2, color=(255,0,255))
            
            # ndarr -> pil
            img_pil = Image.fromarray(img)
            img_draw = ImageDraw.Draw(img_pil)
            
            # draw anno1
            name = self.db_mng.code2name[code]
            i = label2idx["object"]
            obj_img = crop_imgs[i]
            x, y = dst_polys[i, 0, 0], dst_polys[i, 0, 1]-40
            img_draw.text((x,y), name, font=font_pil, fill=(*color, 0))
            
            # draw anno2
            if "date" in label2idx:
                i = label2idx["date"]
                date_img = crop_imgs[i]
                x, y = dst_polys[i, 0, 0], dst_polys[i, 0, 1]-40
                img_draw.text((x,y), date_str, font=font_pil, fill=(*color, 0))
            
            # pil -> ndarr
            img = np.array(img_pil)
            
            self.image_Q.put([img, obj_img, date_img])
            self.recode_Q.put([img, isok, code])
        
    except Exception as e:
        logger.error("an error in [draw]")
        logger.error(traceback.format_exc())
        self.stop_signal = True

#######################################################################
# def json_saver(self):
#     img, poly, name = None, None, None
    
#     while not self.stop_signal:
#         time.sleep(0.05)
        
#         # 데이터 받기
#         if not self.pair_Q.empty():
#             img, poly = self.pair_Q.get()
#         if not self.enter_Q.empty():
#             name = self.enter_Q.get()
            
#         if img is None or name is None: continue
        
#         # 데이터 받은 후
#         path = os.path.join(IMG_DIR_PATH, f"{name}.jpg")
#         tool.imwrite(path, img)
#         path = os.path.join(JSON_DIR_PATH, f"{name}.json")
#         tool.poly2json(path, ["object"], [poly])
#         # self.write_sys_msg(f"[{name}] 등록되었습니다.")
#         logger.info(f"[{name}] applied.")
#         self.poly_detector.update_check()
#         self.update_table()
        
#         # 이미지 초기화
#         img, poly, name = None, None, None
        
#         self.current_origin_image = None
#         self.current_image = None
        
#         imgtk = ImageTk.PhotoImage(Image.fromarray(np.zeros((10,10,3), dtype=np.uint8)))
#         self.image_label.configure(image=imgtk)
#         self.image_label.image = imgtk
#         del imgtk
#         self.image_label.configure(image=None)
#         self.image_label.image = None
        
#######################################################################
def recode(self):
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
    max_recode_num = self.setting_dic["max_recode_num"] if "max_recode_num" in self.setting_dic else 500
    dir_dic = {'raw':SAVE_RAW_IMG_DIR, 'debug':SAVE_DEBUG_IMG_DIR, 
               True:SAVE_OK_IMG_DIR, False:SAVE_NG_IMG_DIR, None:""}
    
    while not self.stop_signal:
        time.sleep(thread_cycle)
        if self.recode_Q.empty(): continue
        
        # 데이터 받기
        img, isok, code = self.recode_Q.get()
        img = img if img is not None else np.zeros((100,100), dtype=np.uint8)
        
        file_name = f"{tool.get_time_str()}.jpg"
        if code is None: code = "None"
        
        # dir 없으면 만들기
        dir_path = dir_dic[isok]
        if code:
            dir_path = os.path.join(dir_path, code)
            if not os.path.isdir(dir_path): os.mkdir(dir_path)
        
        # 이미지 저장
        path = os.path.join(dir_path, file_name)
        tool.imwrite(path, img)
        tool.manage_file_num(dir_path, max_size=max_recode_num)
        
#######################################################################
def add_processing(self):
    thread_cycle = self.setting_dic["thread_cycle"] if "thread_cycle" in self.setting_dic else 0.05
    brightness = self.setting_dic["brightness"] if "brightness" in self.setting_dic else 60
    font = cv2.FONT_HERSHEY_SIMPLEX
    kernel = np.ones((3,3))
    
    try:
        while not self.stop_signal:
            time.sleep(thread_cycle)
            if self.raw_Q.empty(): continue

            # get image
            img = self.raw_Q.get()
            if img is None: continue
            img_copy = img.copy()
            
            # Detect Polys
            img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            img_mask = cv2.inRange(img_hsv, (0, 0, brightness), (360, 255, 255))
            img_mask = cv2.erode(img_mask, kernel, iterations=3)
            img_mask = cv2.dilate(img_mask, kernel, iterations=3)
            self.recode_Q.put([img_mask, 'debug', '']) # debug save
            polys = tool.find_polys_in_img(img_mask)
            if polys is None:
                self.image_Q.put([img_copy])
                self.current_origin_poly = None
                continue
            poly = polys[0]
            
            # 그리기
            clock_poly = tool.poly2clock(poly)
            cv2.polylines(img_copy, [clock_poly], True, (255,255,255), thickness=5)
            cv2.putText(img_copy, '1', clock_poly[0], font, fontScale=2, thickness=2, color=(255,0,255))
            cv2.putText(img_copy, '2', clock_poly[1], font, fontScale=2, thickness=2, color=(255,0,255))
            cv2.putText(img_copy, '3', clock_poly[2], font, fontScale=2, thickness=2, color=(255,0,255))
            cv2.putText(img_copy, '4', clock_poly[3], font, fontScale=2, thickness=2, color=(255,0,255))
        
            self.image_Q.put([img_copy])
            
            # Canvas에 그리기
            crop_img, M = tool.get_crop_img_and_M(img, clock_poly)
            self.canv.apply_img(crop_img)
            
            # 자동촬영 스위치 끄기
            self.auto_stopper.stop_signal = True
            self.bf_btn2.switch_on = False
            self.bf_btn2.configure(bg="#393945", fg="#A6A6A6")
            
            # 저장
            self.current_origin_image = img # 저장할 때를 위해
            self.current_origin_poly = clock_poly
            self.current_M = M
            
    except Exception as e:
        logger.error("an error in [add_processing]")
        logger.error(traceback.format_exc())
        self.stop_signal = True
        

#######################################################################
#######################################################################
#######################################################################
#######################################################################
#######################################################################











