from utils.check import MacChecker
from common.text import *
# from gui import MainWindow

if __name__ == "__main__":
    check_window = MacChecker(SUB_DB_INFO_PATH, SUB_SQL_DIR_PATH, key_path=SUB_KEY_PATH)
    check_window.mainloop()
    exit()
    # main_window = MainWindow()
    # main_window.mainloop()