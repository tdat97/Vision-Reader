
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
DB_INFO_PATH = "./source/db_info.txt"
KEY_PATH = "./source/key.txt"
NODB_PATH = "./source/nodb.json"
SQL_PATH = "./source/sql.txt"

# recode
SAVE_IMG_DIR = "./recode"
SAVE_RAW_IMG_DIR = "./recode/raw"
SAVE_OK_IMG_DIR = "./recode/OK"
SAVE_NG_IMG_DIR = "./recode/NG"
SAVE_DEBUG_IMG_DIR = "./recode/debug"

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
             "get_sensor1": b'\x0500RSS0106%PX000\x04',
             "get_sensor2": b'\x0500RSS0106%PX001\x04',}

# Cam
EXPOSURE_TIME = 2500

