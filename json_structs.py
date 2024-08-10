import json
from urllib.parse import quote


class User:
    real_name: str
    tenant_code: str
    tenant_name: str
    token: str
    unique_value: str
    user_id: str
    user_name: str

    def __init__(self, real_name=None, tenant=None, tenant_name=None, token=None,
                 unique_value=None, user_id=None, user_name=None):
        self.real_name = real_name
        self.tenant_code = str(tenant)
        self.tenant_name = tenant_name
        self.token = token
        self.unique_value = unique_value
        self.user_id = user_id
        self.user_name = user_name


class Project:
    project_id: str
    project_name: str
    user_project_id: str

    def __init__(self, project_id, project_name, user_project_id):
        self.project_id = project_id
        self.project_name = project_name
        self.user_project_id = user_project_id


class Category:
    category_name: str
    category_code: str
    finished: bool

    def __init__(self, name, code, finished_num, total_num):
        self.category_code = code
        self.category_name = name
        self.finished = finished_num == total_num


class Course:
    resource_id: str
    resource_name: str
    user_course_id: str

    def __init__(self, resource_id, resource_name, user_course_id):
        self.resource_id = resource_id
        self.resource_name = resource_name
        self.user_course_id = user_course_id


class Captcha:
    image_url: str
    num: int
    question_id: str

    def __init__(self, image_url, num, question_id):
        self.image_url = image_url
        self.num = num
        self.question_id = question_id


class Position:
    x: int
    y: int

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def to_dict(self) -> dict[str, int]:
        return {
            "x": self.x,
            "y": self.y
        }


class CaptchaAnswer:
    p1: Position
    p2: Position
    p3: Position

    def __init__(self, p1: Position, p2: Position, p3: Position):
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3

    def fetch(self) -> str:
        l: list = list()
        l.append(self.p1.to_dict())
        l.append(self.p2.to_dict())
        l.append(self.p3.to_dict())

        return json.dumps(l).replace(" ", "")

    def fetch_url_encoded(self):
        return quote(self.fetch().encode(encoding="utf-8"))
