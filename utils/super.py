from utils.crypto import encrypt, decrypt
from common.logger import logger

plain_str = "I'm A Developer!"
enc_str = "PmThSEpP8Jc2RJkjwVoWrDrpQVvcwckk2z3m78gEE2c="

def super_certification(key):
    global enc_str, plain_str
    try:
        dec_str = decrypt(enc_str, key)
        logger.info(dec_str)
        return dec_str == plain_str
    except:
        return False
    
# super_certification("DeepAI")