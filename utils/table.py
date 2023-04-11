import pandas as pd
import json
import time
import os

import warnings
warnings.filterwarnings('ignore')


class TableManager():
    def __init__(self, db_con, sql_dir_path, nodb_path, add_cols=[], add_init=[]):
        assert len(add_cols) == len(add_init)
        self.add_cols = add_cols
        self.add_init = add_init
        self.db_con = db_con
        self.nodb_path = nodb_path
        
        # sql 가져오기
        with open(os.path.join(sql_dir_path, "data", "select.txt"), 'r') as f:
            self.sql = f.read()
        
        # 테이블 업데이트
        self.df = None
        self.update_order_today()
        
    def update_order_today(self):
        # 이전 df 저장
        old_df = self.df
        
        if self.db_con is None:
            # 로컬에서 읽어 오기
            with open(self.nodb_path, 'r', encoding='utf-8-sig') as f:
                dic = json.load(f)
            temp = list(zip(dic.keys(), dic.values()))
            df = pd.DataFrame(temp, columns=["ITEM_CD", "ITEM_NM"])
        else:
            # DB에서 읽어 오기
            df = pd.read_sql(self.sql, self.db_con)
        
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
                
    