class ServerError(Exception):
    """ 伺服器連線或請求處理異常
    """

    def __init__(self, message: str):
        self.message = f"伺服器連線或請求處理異常: {message}"
        super().__init__(self.message)


class IDCardValidationNotPassError(Exception):
    """ 身分證驗證未通過
    """

    def __init__(self, message: str):
        self.message = f"IDCard not valid: {message}"
        super().__init__(self.message)


class PersonalInfoNotConsistencyError(Exception):
    """ 個人資料不一致
    """

    def __init__(self, message: str):
        self.message = f"PersonalInfo not consistence: {message}"
        super().__init__(self.message)
