from collections import defaultdict, Counter
from utils.crypto import glance
import pymysql
import json
import time
import os


class DBManager():
    def __init__(self, db_info_path, sql_dir_path, key_path=None):
        self.whoami = "db"
        
        # DB 정보 가져오기
        db_info_str = glance(db_info_path, key_path)
        db_info_dic = json.loads(db_info_str)
        
        # DB 연결
        self.con = pymysql.connect(**db_info_dic, charset='utf8', autocommit=True, 
                                   cursorclass=pymysql.cursors.Cursor)
        self.cur = self.con.cursor()
        
        # sql 가져오기
        with open(os.path.join(sql_dir_path, "select.txt"), 'r') as f:
            self.select_sql = f.read()
        
        # 초기화
        self.code2name = None
        self.name2code = None
        self.update_order_today()
                    
    def update_order_today(self):
        self.cur.execute(self.select_sql)
        rows = self.cur.fetchall()
        self.code2name = dict(rows)
        self.name2code = dict(zip(self.code2name.values(), self.code2name.keys()))
        
    # def __del__(self):
    #     self.con.close()
        
        
class NODBManager():
    def __init__(self, nodb_path):
        self.whoami = "nodb"
        self.nodb_path = nodb_path
        self.code2name = None
        self.name2code = None
        self.update_order_today()
        
    def update_order_today(self):
        with open(self.nodb_path, 'r', encoding="utf-8-sig") as f:
            code2name = json.load(f)
        self.code2name = code2name
        self.name2code = dict(zip(self.code2name.values(), self.code2name.keys()))