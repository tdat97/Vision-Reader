import pandas as pd

class TableManager():
    def __init__(self, key_column, columns, lb_list, rows):
        assert len(columns) == len(lb_list) == len(rows[0])
        self.stop_signal = False
        self.key_column = key_column
        self.columns = columns
        self.key_idx = columns.index(key_column)
        self.lb_list = lb_list
        
        self.table_df = None
        self.update_all(rows)
    
    def update_table(self):
        for j, lb in enumerate(self.lb_list):
            lb.delete(0, 'end')
            for i in range(len(self.table_df)):
                lb.insert(self.table_df.iloc[i,j])
        
    def update_all(self, rows):
        self.table_df = pd.DataFrame(rows, columns=self.columns)
        self.update_table()
        
    def update_row(self, row):
        # df 업데이트
        key = row[self.key_idx]
        self.table_df[self.table_df[self.key_column] == key] = row
        
        # list_box 변경
        self.update_table()
        
    def get_row(self, key):
        row = self.table_df[self.table_df[self.key_column] == key].iloc[0,:]
        return row
        
        
        

        # self.table_mng = TableManager(key_column="code", columns=["code","name","ALL","OK","NG","exist"], 
        #                               lb_list=[self.listbox1, self.listbox2, self.listbox3, 
        #                                        self.listbox4, self.listbox5, self.listbox6, ], 
        #                               rows=[])