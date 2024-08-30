import base64

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# Consider setting a breakpoint @ webpack:///src/store/index.js line 136 & 152 and run step by step.
from config import *


def encrypt(content: str) -> str:
    aes = AES.new(key=config_instance.KEY, mode=AES.MODE_ECB)
    pad_pkcs7 = pad(content.encode("utf-8"), AES.block_size, style='pkcs7')
    encrypted = aes.encrypt(pad_pkcs7)
    encrypted_text = str(base64.encodebytes(encrypted), encoding='utf-8') \
        .strip() \
        .replace("+", "-") \
        .replace("/", "_") \
        .replace("\n", "")  # encrypted strings sometimes contain weird \n and I have no idea why.
    return encrypted_text


def decrypt(content_b64: str) -> str:
    content = content_b64.strip() \
        .replace("-", "+") \
        .replace("_", "/")
    content_bytes = content.encode("utf-8")
    content_original: bytes = base64.b64decode(content_bytes)

    aes = AES.new(key=config_instance.KEY, mode=AES.MODE_ECB)
    pad_pkcs7 = pad(content_original, AES.block_size, style='pkcs7')
    decrypted = aes.decrypt(pad_pkcs7)
    # print(decrypted)
    return decrypted.decode("utf-8")
