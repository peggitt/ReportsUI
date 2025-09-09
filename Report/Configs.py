ENDPOINTEnvironment =  "_Development"

from cryptography.fernet import Fernet
key = b'_3ZQXo8476twsZ4-XPi6ANcbGGMUQbs8Qe5eAZS6Fqc='

def EncryptData(PassVar: str):
    fernet = Fernet(key)
    encMessage = fernet.encrypt(PassVar.encode())
    return encMessage

def DecryptData(PassVar: str):
    fernet = Fernet(key)
    decMessage = fernet.decrypt(PassVar).decode()
    return decMessage

def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'