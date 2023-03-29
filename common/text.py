
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
SERIAL_PORT = "COM7"
BYTES_DIC = {"light_on"   : bytes([0xA0, 0x00, 0x01, 0xA0 ^ 0x00 ^ 0x01]),
             "light_off"  : bytes([0xA0, 0x00, 0x00, 0xA0 ^ 0x00 ^ 0x00]),
             "green_on"   : bytes([0xA0, 0x01, 0x01, 0xA0 ^ 0x01 ^ 0x01]),
             "green_off"  : bytes([0xA0, 0x01, 0x00, 0xA0 ^ 0x01 ^ 0x00]),
             "yellow_on"  : bytes([0xA0, 0x02, 0x01, 0xA0 ^ 0x02 ^ 0x01]),
             "yellow_off" : bytes([0xA0, 0x02, 0x00, 0xA0 ^ 0x02 ^ 0x00]),
             "red_on"     : bytes([0xA0, 0x01, 0x01, 0xA0 ^ 0x01 ^ 0x01]),
             "red_off"    : bytes([0xA0, 0x01, 0x00, 0xA0 ^ 0x01 ^ 0x00]),
             "get_sensor1": bytes([0xB0, 0x00, 0x00, 0xB0 ^ 0x00 ^ 0x00]),
             "get_sensor2": bytes([0xB0, 0x01, 0x00, 0xB0 ^ 0x01 ^ 0x00]),}
# ex) 0xB0 0x01 0x00 0xB1 -> get input-pin-1 sensor value
# ex) 0xC0 0x01 0x01 0xC0 -> reply (input-pin-1 is HIGH)
# ex) 0xA0 0x02 0x01 0xA3 -> turn on output-pin-2 
# ex) 0xFF 0x00 0x00 0xFF -> Incorrect validation.

# Cam
EXPOSURE_TIME = 2500

