from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from base64 import b64encode, b64decode

def encrypt(plain_str, key_str): # 문자열 들어옴
    key_str = hash_str(key_str)
    iv_str = hash_str(key_str)
    
    data = pad(plain_str.encode('utf-8'), AES.block_size) # AES.block_size = 16
    key = pad(key_str.encode('utf-8'), AES.block_size)[:AES.key_size[-1]]
    iv = pad(iv_str.encode('utf-8'), AES.block_size)[:AES.block_size]

    cipher = AES.new(key, AES.MODE_CBC, iv=iv, ) # 객체 생성
    enc = cipher.encrypt(data) # 16배수길이의 바이트문자열을 암호화
    enc_str = b64encode(enc).decode('utf-8') # base 64로 인코드 후 바이트-> 문자열
    return enc_str

def decrypt(enc_str, key_str):
    key_str = hash_str(key_str)
    iv_str = hash_str(key_str)
    
    enc = b64decode(enc_str) # base 64로 디코드
    key = pad(key_str.encode('utf-8'), AES.block_size)[:AES.key_size[-1]]
    iv = pad(iv_str.encode('utf-8'), AES.block_size)[:AES.block_size]

    cipher = AES.new(key, AES.MODE_CBC, iv=iv, ) # 객체 생성
    dec = cipher.decrypt(enc) # 복호화
    dec_str = unpad(dec, AES.block_size).decode('utf-8') # 제로패딩 해제하고 바이트->문자열
    return dec_str

def hash_str(plain_str):
    data = plain_str.encode('utf-8')
    sha = SHA256.new(data=data)
    h = sha.digest()
    h_str = b64encode(h[:AES.block_size]).decode('utf-8')
    return h_str

def get_random_str():
    r = get_random_bytes(AES.block_size)
    r_str = b64encode(r).decode('utf-8')
    return r_str
    # r = get_random_bytes(8)
    # r_str = str(int.from_bytes(r, byteorder="big"))
    # return r_str
    
    
import hashlib

def get_hashed_string(input_string):
    # 문자열을 바이트 문자열로 변환
    byte_string = input_string.encode('utf-8')
    
    # SHA256 알고리즘으로 해싱
    hashed_string = hashlib.sha256(byte_string).hexdigest()
    
    return hashed_string

    
import os
REPEAT_NUM = 16

def glance(target_path, key_path=None):
    with open(target_path, 'r') as f:
        enc_target_str = f.read()
        
    if key_path is not None and os.path.isfile(key_path):
        with open(key_path, 'r') as f:
            enc_key_str = f.read()
    
        # 복호화
        for _ in range(REPEAT_NUM):
            enc_key_str = decrypt(enc_key_str, enc_target_str)
            enc_target_str = decrypt(enc_target_str, enc_key_str)
            
    target_str = enc_target_str
    
    if key_path is not None:
        # 랜덤 키 생성
        enc_key_str = get_random_str()

        # 암호화
        for _ in range(REPEAT_NUM):
            enc_target_str = encrypt(enc_target_str, enc_key_str)
            enc_key_str = encrypt(enc_key_str, enc_target_str)

        # 파일 쓰기
        with open(target_path, 'w') as f:
            f.write(enc_target_str)
        with open(key_path, 'w') as f:
            f.write(enc_key_str)
    
    return target_str