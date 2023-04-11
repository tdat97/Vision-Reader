from common.logger import logger
from utils.super import super_certification
from utils.crypto import hash_str
import tkinter as tk
import uuid
import os

class LoginWindow(tk.Toplevel):
    def __init__(self, db_con, sql_dir_path, *args, callback=None, mac_pass=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("로그인")
        self.geometry(f"300x150+{self.winfo_screenwidth()//2-150}+{self.winfo_screenheight()//2-75}")
        self.resizable(False, False)
        self.focus() # 창 선택해줌
        self.grab_set() # 다른창 못건드림
        self.protocol("WM_DELETE_WINDOW", lambda:(self.destroy(),self.callback(False),))
        self.bind("<Return>", self.login)
        
        self.callback = callback
        self.db_con = db_con
        self.sql_dir_path = sql_dir_path
        self.mac_pass = mac_pass
        self.check_list = ["drop", "select", "insert", "delete", "create", " ", ";", "-", "'", '"']
        
        self.label_username = tk.Label(self, text="아이디")
        self.label_username.pack()
        self.entry_username = tk.Entry(self)
        self.entry_username.pack()
        
        self.label_password = tk.Label(self, text="비밀번호")
        self.label_password.pack()
        self.entry_password = tk.Entry(self, show="*")
        self.entry_password.pack()
        
        self.button_login = tk.Button(self, text="로그인", command=self.login)
        self.button_login.pack()
        
        self.label_message = tk.Label(self, text="")
        self.label_message.pack()
        
        if self.mac_pass and self.db_con is not None and self.select_mac():
            logger.info("Login with MAC.")
            self.destroy()
        
    def select_mac(self):
        # 맥주소 가져오기
        hash_mac = hash_str(f"{uuid.getnode():012x}")
        
        # sql 가져오기
        with open(os.path.join(self.sql_dir_path, "mac", "select.txt"), 'r') as f:
            sql = f.read()
        
        # 쿼리 넣기
        sql = sql.format(hash_mac)
        cur = self.db_con.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        return bool(rows)
    
    def insert_mac(self):
        # 맥주소 가져오기
        hash_mac = hash_str(f"{uuid.getnode():012x}")
        
        # sql 가져오기
        with open(os.path.join(self.sql_dir_path, "mac", "insert.txt"), 'r') as f:
            sql = f.read()
        
        # 쿼리 넣기
        sql = sql.format(hash_mac)
        logger.info(sql)
        cur = self.db_con.cursor()
        cur.execute(sql)
        
    def login(self, event=None):
        username = self.entry_username.get()
        password = self.entry_password.get()
        
        # injection 검사
        for check in self.check_list:
            if check in username.lower() or check in password.lower():
                self.destroy()
                self.callback(False, injection_attack=True)
        
        # 인증
        certified = self.certification(username, password)
        
        # 맥주소 db에 추가
        if certified and self.db_con is not None and self.mac_pass:
            self.insert_mac()
            
        # 나가기
        self.destroy()
        self.callback(certified)

    def certification(self, username, password):
        # 개발자 검사
        if username == 'superadmin':
            return super_certification(password)
        
        # sql 가져오기
        with open(os.path.join(self.sql_dir_path, "login", "select.txt"), 'r') as f:
            sql = f.read()
            
        # 쿼리 넣기
        if self.db_con is None: return False
        sql = sql.format(username, hash_str(password))
        logger.info(sql)
        cur = self.db_con.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        return bool(rows)