import tkinter as tk
import tkinter.font as font

class PinWindow(tk.Toplevel):
    def __init__(self, *args, pin_len=4, callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("핀번호 입력")
        self.geometry(f"400x600+{self.winfo_screenwidth()//2-200}+{self.winfo_screenheight()//2-300}")
        self.resizable(False, False)
        self.focus() # 창 선택해줌
        self.grab_set() # 다른창 못건드림
        self.protocol("WM_DELETE_WINDOW", lambda:(self.destroy(),self.callback(""),))
        
        self.callback = callback
        self.pin_len = pin_len
        self.pin_str = ""
        
        self.__configure()
        
    def submit(self):
        self.destroy()
        self.callback(self.pin_str)
    
    def input_pin(self, v):
        self.pin_str += f"{v}"
        self.pin_str = self.pin_str[-self.pin_len:]
        self.pin_label['text'] = self.pin_str
    
    def __configure(self):
        bg_color = "#181B34"
        self.configure(bg=bg_color)
        
        def create_input_pin(i):
            def input_pin_():
                return self.input_pin(i)
            return input_pin_
        
        self.pin_btn_list = []
        for i in range(10):
            pin_btn = tk.Button(self, bd=1, text=f"{i}", command=lambda x=i:self.input_pin(x))#create_input_pin(i))
            pin_btn['font'] = font.Font(family='Helvetica', size=45, weight='bold')
            pin_btn.configure(bg="#393945", fg="#A6A6A6", 
                                           activebackground="#0153B0", activeforeground="#FFF")
            self.pin_btn_list.append(pin_btn)
            
        self.pin_btn_list[0].place(relx=0.33, rely=0.75, relwidth=0.33, relheight=0.25)
        self.pin_btn_list[1].place(relx=0.00, rely=0.50, relwidth=0.33, relheight=0.25)
        self.pin_btn_list[2].place(relx=0.33, rely=0.50, relwidth=0.33, relheight=0.25)
        self.pin_btn_list[3].place(relx=0.66, rely=0.50, relwidth=0.34, relheight=0.25)
        self.pin_btn_list[4].place(relx=0.00, rely=0.25, relwidth=0.33, relheight=0.25)
        self.pin_btn_list[5].place(relx=0.33, rely=0.25, relwidth=0.33, relheight=0.25)
        self.pin_btn_list[6].place(relx=0.66, rely=0.25, relwidth=0.34, relheight=0.25)
        self.pin_btn_list[7].place(relx=0.00, rely=0.00, relwidth=0.33, relheight=0.25)
        self.pin_btn_list[8].place(relx=0.33, rely=0.00, relwidth=0.33, relheight=0.25)
        self.pin_btn_list[9].place(relx=0.66, rely=0.00, relwidth=0.34, relheight=0.25)
        
        # self.pin_btn_list[0]["command"] = lambda:self.input_pin(0)
        # self.pin_btn_list[1]["command"] = lambda:self.input_pin(1)
        # self.pin_btn_list[2]["command"] = lambda:self.input_pin(2)
        # self.pin_btn_list[3]["command"] = lambda:self.input_pin(3)
        # self.pin_btn_list[4]["command"] = lambda:self.input_pin(4)
        # self.pin_btn_list[5]["command"] = lambda:self.input_pin(5)
        # self.pin_btn_list[6]["command"] = lambda:self.input_pin(6)
        # self.pin_btn_list[7]["command"] = lambda:self.input_pin(7)
        # self.pin_btn_list[8]["command"] = lambda:self.input_pin(8)
        # self.pin_btn_list[9]["command"] = lambda:self.input_pin(9)
        
        
        self.submit_btn = tk.Button(self, bd=1, text=f"확인", command=self.submit)
        self.submit_btn.place(relx=0.66, rely=0.75, relwidth=0.34, relheight=0.25)
        self.submit_btn['font'] = font.Font(family='Helvetica', size=45, weight='bold')
        self.submit_btn.configure(bg="#393945", fg="#A6A6A6", activebackground="#0153B0", activeforeground="#FFF")
        
        self.pin_label = tk.Label(self, bd=1, text="")
        self.pin_label.place(relx=0.00, rely=0.75, relwidth=0.33, relheight=0.25)
        self.pin_label['font'] = font.Font(family='Helvetica', size=45, weight='bold')
        self.pin_label.configure(bg="#393945", fg="#FFF")
        
        