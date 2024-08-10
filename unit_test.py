import crypto_helper
import web_utils


def test():
    assert web_utils.request_str_arg_builder("aaa<bbb>ccc") \
        .replace("<bbb>", "ddd") \
        .fetch() == "aaadddccc"

    raw = '''{"keyNumber":"2024303504","password":"2024303504","tenantCode":"71000012","time":1723272942989,"verifyCode":"x2bb"}'''
    sample = "YBVqh7s9jlcEyFQp0ykbgH8392I5enPRYLhxa0DuW1ar02ku9M-aId8TSVvS0mpBugyf2mRaZFnTbfiEPJog3pE8ciSiz7WlVVgIKaOxmVZEBoTIBYgSxoj-PXANZxuxJHnhv71z-ibHF-_GTyKgTQ8maJsiZ1NeXalVoRok7Ds="

    assert crypto_helper.encrypt(raw) == sample
