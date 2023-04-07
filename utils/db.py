from common.logger import logger
from utils.crypto import glance
import pandas as pd
import pymysql
import json
import time
import os

import warnings
warnings.filterwarnings('ignore')


class DBManager():
    def __init__(self, db_info_path, sql_dir_path, key_path=None, add_cols=[], add_init=[]):
        assert len(add_cols) == len(add_init)
        self.add_cols = add_cols
        self.add_init = add_init
        
        # DB 정보 가져오기
        db_info_str = glance(db_info_path, key_path)
        db_info_dic = json.loads(db_info_str)
        
        # self.con = pymysql.connect(**db_info_dic, charset='utf8', autocommit=True,
        #                            cursorclass=pymysql.cursors.Cursor)
        self.con = pymysql.connect(**db_info_dic, charset='utf8', autocommit=True)
        self.cur = self.con.cursor()
        
        # sql 가져오기
        with open(os.path.join(sql_dir_path, "select.txt"), 'r') as f:
            self.select_sql = f.read()
        # with open(os.path.join(sql_dir_path, "update.txt"), 'r') as f:
        #     self.update_sql = f.read()
        # with open(os.path.join(sql_dir_path, "insert.txt"), 'r') as f:
        #     self.insert_sql = f.read()
        
        # 테이블 업데이트
        self.df = None
        self.update_order_today()
        
    def update_order_today(self):
        # 이전 df 저장
        old_df = self.df
        
        # DB에서 읽어 오기
        self.df = pd.read_sql(self.select_sql, self.con)
        
        # 미분류 행추가
        temp = pd.DataFrame([['NONE', '']], columns=['ITEM_CD', 'ITEM_NM'])
        self.df = pd.concat([df, temp], axis=0, ignore_index=True)
        
        # 열추가
        for col, v in zip(self.add_cols, self.add_init):
            self.df[col] = v
        
        if old_df is None or not self.add_cols:
            return
        
        # add_cols 옮기기
        for row in old_df.iloc:
            # 첫번째 열이 key라 가정
            idxs = self.df[self.df.iloc[:,0] == row[0]].index
            if len(idxs):
                idx = idxs[0]
                self.df.loc[idx] = row
                
    def update(self, value):
        sql = self.update_sql.format(value)
        self.cur.execute(sql)
        
    def insert(self, value):
        sql = self.insert_sql.format(value)
        self.cur.execute(sql)
        
        
    
class Dummy():
    def execute(self, *args, **kargs):
        pass
    
class NODBManager():
    def __init__(self, *args, add_cols=[], add_init=[], nodb_path="./source/nodb.json", **kargs):
        self.df = None
        self.cur = Dummy()
        self.add_cols = add_cols
        self.add_init = add_init
        self.nodb_path = nodb_path
        self.update_order_today()
        
    def update_order_today(self):
        # 이전 df 저장
        old_df = self.df
        
        # 로컬에서 읽어 오기
        with open(self.nodb_path, 'r', encoding='utf-8-sig') as f:
            dic = json.load(f)
        temp = list(zip(dic.keys(), dic.values()))
        df = pd.DataFrame(temp, columns=["ITEM_CD", "ITEM_NM"])
        
        # 미분류 행추가
        temp = pd.DataFrame([['NONE', '']], columns=['ITEM_CD', 'ITEM_NM'])
        self.df = pd.concat([df, temp], axis=0, ignore_index=True)
        
        # 열추가
        for col, v in zip(self.add_cols, self.add_init):
            self.df[col] = v
        
        if old_df is None or not self.add_cols:
            return
            
        # add_cols 옮기기
        for row in old_df.iloc:
            # 첫번째 열이 key라 가정
            idxs = self.df[self.df.iloc[:,0] == row[0]].index
            if len(idxs):
                idx = idxs[0]
                self.df.loc[idx] = row