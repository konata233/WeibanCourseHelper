# Common
DEBUG = True
IGNORE_FINISHED_TASKS = False
MAX_TASK_NUM = 11451
DEBUG_PRINT_MAX_LEN = 65535

# Network Service
JQUERY_VER = "3.4.1"
MY_CAPTCHA = "ba95ef14-d7dd-4d7b-8ec5-189d33b3a6d8"
CAPTCHA_CRACK_MAX_ITER = 256

# Cryptography
KEY_SZ = 128
KEY: bytes = "xie2gg".encode("utf-8").ljust(KEY_SZ // 8, b"\x00")
IV = b""
