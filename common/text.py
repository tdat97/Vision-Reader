
# window
TITLE = "Machine Vision System"

# resource
OCR_MODEL_PATH = "./resource/date_ocr.h5"
LOGO_PATH = "./resource/smlogo_white.png"
ICON_PATH = "./resource/eye.ico"
FONT_PATH = "./resource/NanumGothicBold.ttf"

# source
IMG_DIR_PATH = "./source/image"
JSON_DIR_PATH = "./source/json"
SETTING_PATH = "./source/setting.json"
DEFAULT_SETTING_PATH = "./source/default_setting.json"

# DB
# DB_INFO_PATH = "../secret/db_info.txt"
# KEY_PATH = "../secret/key.txt"
DB_INFO_FILE = "db_info.txt"
KEY_FILE = "key.txt"
NODB_PATH = "./source/nodb.json"
SQL_DIR_PATH = "./source/sql"

SUB_DB_INFO_PATH = "../secret/dev/db_info.txt"
SUB_KEY_PATH = "../secret/dev/key.txt"
SUB_SQL_DIR_PATH = "./source/sql2"

# recode
SAVE_IMG_DIR = "./recode"
SAVE_RAW_IMG_DIR = "./recode/raw"
SAVE_OK_IMG_DIR = "./recode/OK"
SAVE_NG_IMG_DIR = "./recode/NG"
SAVE_DEBUG_IMG_DIR = "./recode/debug"

# Cam
EXPOSURE_TIME = 2500

# Serial
SERIAL_PORT = "COM6"
BYTES_DIC = {"light_on"   : b'\x0500WSS0106%DW0140001\x04',
             "light_off"  : b'\x0500WSS0106%DW0140000\x04',
             "red_on"     : b'\x0500WSS0106%DW0100001\x04',
             "red_off"    : b'\x0500WSS0106%DW0100000\x04',
             "yellow_on"  : b'\x0500WSS0106%DW0110001\x04',
             "yellow_off" : b'\x0500WSS0106%DW0110000\x04',
             "green_on"   : b'\x0500WSS0106%DW0120001\x04',
             "green_off"  : b'\x0500WSS0106%DW0120000\x04',
             "sound_on"   : b'\x0500WSS0106%DW0130001\x04',
             "sound_off"  : b'\x0500WSS0106%DW0130000\x04',
             "sol_on"     : b'\x0500WSS0106%DW0150001\x04',
             "sol_off"    : b'\x0500WSS0106%DW0150000\x04',
             "get_sensor1": b'\x0500RSS0106%PX000\x04',
             "get_sensor2": b'\x0500RSS0106%PX001\x04',}

DEFAULT_SETTING_DIC = {
    "alram" : False,
    "use_solenoid" : True,
    
    "nodb_mode" : False,
    "hand_mode" : False,
    "debug_mode" : False,

    "thread_cycle" : 0.05,
    "update_cycle" : 60,

    "trigger1_time_gap" : 0.0,
    "trigger2_time_gap" : 3.0,

    "cam_exp_time" : 2500,
    "cut_width" : [300,300],

    "serial_port" : "COM6",
    "on_off_time" : {"red":3, "yellow":2, "green":1, "sol":1, "sound":1},

    "max_recode_num" : 500,
    "font_size_factor" : 1080,


    "n_features" : 2000,
    "brightness" : 60,
    
    "db_info_dir":"../DB_pair/dev",
    "pin_number":"9876",
}
