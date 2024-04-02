import base64
from Crypto.Cipher import AES


class Aes:
    """ AES 加解密
    """

    class DecryptError(Exception):
        """ AES 解密失敗
        """

        def __init__(self, message: str):
            self.message = f"AES 解密失敗: {message}"
            super().__init__(self.message)

    @classmethod
    def encrypt(cls, key: str, iv: str, data: str) -> str:
        """ AES加密

        Ref. https://www.jb51.net/article/196942.htm

        Args:
            key (str): AES 密鑰
            data (str): 加密數據

        Returns:
            str : AES 已加密資料
        """
        def pad(s): return s + (16 - len(s) % 16) * chr(16 - len(s) % 16)
        data = pad(data)
        # 字符串補位
        cipher = AES.new(key.encode('utf8'), AES.MODE_CBC, iv.encode('utf8'))
        encryptedbytes = cipher.encrypt(data.encode('utf8'))
        # 加密後得到的是bytes類型的數據
        encodestrs = base64.b64encode(encryptedbytes)
        # 使用Base64進行編碼,返回byte字符串
        enctext = encodestrs.decode('utf8')
        # 對byte字符串按utf-8進行解碼
        return enctext

    @classmethod
    def decrypt(cls, key: str, iv: str, aes_encrypted_str: str) -> str:
        """ AES 解密

        Ref. https://www.jb51.net/article/196942.htm

        Args:
            key (str): AES 密鑰
            aes_encrypted_str (str): AES 已加密資料

        Raise:
            DecryptError: 解密失敗

        Returns:
            str : 解密資料
        """
        try:
            aes_encrypted_str = aes_encrypted_str.encode('utf8')
            encodebytes = base64.decodebytes(aes_encrypted_str)
            # 將加密數據轉換位bytes類型數據
            cipher = AES.new(key.encode('utf8'),
                             AES.MODE_CBC, iv.encode('utf8'))
            text_decrypted = cipher.decrypt(encodebytes)
            def unpad(s): return s[0:-s[-1]]
            text_decrypted = unpad(text_decrypted)
            # 去補位
            text_decrypted = text_decrypted.decode('utf8')
            return text_decrypted
        except UnicodeDecodeError as e:
            raise cls.DecryptError(e)
