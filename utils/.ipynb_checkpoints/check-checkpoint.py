from utils.crypto import hash_str, glance
from common.text import *

import tkinter as tk
import pymysql
import uuid
import json
import os

def get_mac_address():
    return f"{uuid.getnode():012x}"

class MacChecker(tk.Tk):
    def __init__(self, db_info_path, sql_dir_path, *arg, key_path=None, **kwargs):
        super().__init__(*arg, **kwargs)
        self.iconbitmap(ICON_PATH)
        self.title(TITLE)
        
        # DB 정보 가져오기
        db_info_str = glance(db_info_path, key_path)
        db_info_dic = json.loads(db_info_str)
        
        # DB 연결
        self.con = pymysql.connect(**db_info_dic, charset='utf8', autocommit=True)
        self.cur = self.con.cursor()
        
        # 
        self.sql_dir_path = sql_dir_path
        
        # 화면 사이즈
        # self.state("zoomed")
        self.geometry(f"{self.winfo_screenwidth()//5*2}x{self.winfo_screenheight()//5*2}")
        self.minsize(self.winfo_screenwidth()//5*2, self.winfo_screenheight()//5*2)
        
    def exist_mac(self):
        # 맥주소 가져오기
        mac = get_mac_address()
        mac_hash = hash_str(mac)
        
        # sql 가져오기
        with open(os.path.join(self.sql_dir_path, "select_mac.txt"), 'r') as f:
            sql = f.read()
        sql = sql.format(mac_hash)
        
        # 실행
        self.cur.execute(sql)
        rows = self.cur.fetchall()
        
        return bool(rows)
        