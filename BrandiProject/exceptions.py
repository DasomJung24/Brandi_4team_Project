class NoAffectedRowException(Exception):
    """
    update, delete 같은 sql 문을 실행하였을 때 영향을 받는 row 가 없는 경우
    """
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message


class NoDataException(Exception):
    """
    select 구문을 사용하였을 때 필수로 받아와야 하는 데이터가 있는 경우에 아무 데이터도 받지 못했을 때
    """
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message


class InvalidUsage(Exception):
    """
    Exception 을 잡아서 함수 밖의 validate params 데코레이터 에러가 발생했을 때도 에러를 잡아줌
    app.py 에 정의된 error handler 로 전달
    """
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv
