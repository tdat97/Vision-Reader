
# window
TITLE = "Machine Vision System"

# resource
OCR_MODEL_PATH = "./resource/date_ocr.h5"
LOGO_PATH = "./resource/smlogo_white.png"
ICON_PATH = "./resource/eye.ico"
FONT_PATH = "./resource/NanumGothic.ttf"

# source
IMG_DIR_PATH = "./source/image"
JSON_DIR_PATH = "./source/json"
SETTING_PATH = "./source/setting.json"

# DB
DB_INFO_PATH = "../secret/db_info.txt"
KEY_PATH = "../secret/key.txt"
NODB_PATH = "./source/nodb.json"
SQL_PATH = "./source/sql.txt"

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
    "use_solenoid" : False,
    
    "nodb_mode" : True,
    "hand_mode" : True,
    "debug_mode" : True,

    "thread_cycle" : 0.05,
    "update_cycle" : 10,

    "trigger1_time_gap" : 0.0,
    "trigger2_time_gap" : 3.0,

    "cam_exp_time" : 2500,
    "cut_width" : [300,2300],

    "serial_port" : "COM6",
    "on_off_time" : {"red":3, "yellow":2, "green":1, "sol":1, "sound":3},

    "max_recode_num" : 500,
    "font_size_factor" : 1080,


    "brightness" : 80,
}
