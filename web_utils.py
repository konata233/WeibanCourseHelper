import asyncio
import json
import random
import time
from copy import deepcopy
from datetime import datetime
from typing import Optional

import requests
import urllib3
from urllib3 import exceptions

import crypto_helper
import json_structs
from config import *
from json_structs import User

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

headers = {
    "X-Token": "",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 "
                  "Safari/537.36 Edg/127.0.0.0 "
}

# To prevent potential errors raised by proxy configuration.
proxies = {
    "http": None,
    "https": None
}


def dbg_print(msg: str):
    if DEBUG:
        now: datetime = datetime.now()
        print(f"[DBG] [{now}] {msg}")


class request_str_arg_builder:
    base_url: str
    first: bool

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.first = True

    def format(self, *args):
        self.base_url = self.base_url.format(args)
        return self

    def replace(self, old, new):
        self.base_url = self.base_url.replace(old, new)
        return self

    def concat(self, arg: str, arg_v: object):
        if self.first:
            self.base_url += ("?" + arg + "=" + str(arg_v))
            self.first = False
        else:
            self.base_url += ("&" + arg + "=" + str(arg_v))
        return self

    def concat_ts(self, offset: float = 0.0):
        ts = round(time.time() * 1000) / 1000 + offset
        if self.first:
            self.base_url += ("?timestamp=" + str(ts))
            self.first = False
        else:
            self.base_url += ("&timestamp=" + str(ts))
        return self

    def fetch(self):
        # dbg_print(self.base_url)
        return self.base_url


class api:
    GET_LOGIN_CAPTCHA = 0x00
    GET_TENANT_LIST = 0x10
    GET_TENANT_CONF = 0x11
    LOGIN = 0x12
    FETCH_PROJECT_LIST = 0x20
    FETCH_CATEGORY_LIST = 0x21
    FETCH_COURSE_LIST = 0x22
    STUDY_START = 0x30,
    STUDY_GET_COURSE_URL = 0x31,
    STUDY_TERMINATE = 0x32
    STUDY_FETCH_CAPTCHA = 0x40
    STUDY_CHECK_CAPTCHA = 0x41


api_mapping: dict = {
    api.GET_LOGIN_CAPTCHA: "https://weiban.mycourse.cn/pharos/login/randLetterImage.do",
    api.GET_TENANT_LIST: "https://weiban.mycourse.cn/pharos/login/getTenantList.do",
    api.GET_TENANT_CONF: "https://weiban.mycourse.cn/pharos/login/getTenantConfig.do",
    api.LOGIN: "https://weiban.mycourse.cn/pharos/login/login.do",
    api.FETCH_PROJECT_LIST: "https://weiban.mycourse.cn/pharos/index/listMyProject.do",
    api.FETCH_CATEGORY_LIST: "https://weiban.mycourse.cn/pharos/usercourse/listCategory.do",
    api.FETCH_COURSE_LIST: "https://weiban.mycourse.cn/pharos/usercourse/listCourse.do",

    api.STUDY_START: "https://weiban.mycourse.cn/pharos/usercourse/study.do",
    api.STUDY_GET_COURSE_URL: "https://weiban.mycourse.cn/pharos/usercourse/getCourseUrl.do",
    api.STUDY_FETCH_CAPTCHA: "https://weiban.mycourse.cn/pharos/usercourse/getCaptcha.do",
    api.STUDY_CHECK_CAPTCHA: "https://weiban.mycourse.cn/pharos/usercourse/checkCaptcha.do",
    api.STUDY_TERMINATE: "https://weiban.mycourse.cn/pharos/usercourse/v2/<replace>.do"
}


def set_token(token):
    """
    Must be executed right after calling login()
    :param token:
    :return:
    """
    headers["X-Token"] = token


def post(url, data: dict, cookies: object = None) -> requests.Response:
    dbg_print("POST " + url)
    dbg_print("Parameters: " + json.dumps(data))
    if cookies is None:
        cookies = {}
    resp: requests.Response = requests.post(url, data=data, headers=headers, cookies=cookies,
                                            timeout=5, verify=False, proxies=proxies)
    if len(t := resp.text) < DEBUG_PRINT_MAX_LEN:
        dbg_print("Response: " + t)
    else:
        dbg_print("Response: " + t[0:65536])
    return resp


def get(url, cookies=None) -> requests.Response:
    dbg_print("GET " + url)
    if cookies is None:
        cookies = {}
    resp: requests.Response = requests.get(url, headers=headers, cookies=cookies,
                                           timeout=5, verify=False, proxies=proxies)
    if len(t := resp.text) < DEBUG_PRINT_MAX_LEN:
        dbg_print("Response: " + t)
    else:
        dbg_print("Response: " + t[0:65536])
    return resp


def fetch_login_captcha() -> (requests.Response, int):
    current_time = time.time()
    return get(
        request_str_arg_builder(api_mapping[api.GET_LOGIN_CAPTCHA])
        .concat("time", str(round(current_time * 1000)))
        .fetch(),
    ), current_time


def fetch_all_tenants() -> dict[str, str]:
    resp = post(
        request_str_arg_builder(api_mapping[api.GET_TENANT_LIST])
        .concat_ts()
        .fetch(),
        data={}
    )

    ret = dict()

    data: list[dict] = json.loads(resp.text)["data"]
    for d in data:
        dbg_print(str({d["name"]: d["code"]}))
        ret.update({d["name"]: d["code"]})

    return ret


def fetch_tenant_conf(tenant_code: str):
    resp = post(
        request_str_arg_builder(api_mapping[api.GET_TENANT_CONF])
        .concat_ts()
        .fetch(),
        data={
            "tenantCode": tenant_code
        }
    )

    data = json.loads(resp.text)["data"]
    pwd_prompt = data["passwordPrompt"]
    uname_prompt = data["userNamePrompt"]

    return uname_prompt, pwd_prompt


async def login(tenant: str, uname: str, pwd: str, captcha: str, captcha_ts: float) -> (Optional[User], str):
    captcha_ts = round(captcha_ts * 1000)
    dbg_print(json.dumps(
        {
            "keyNumber": uname,
            "password": pwd,
            "tenantCode": tenant,
            "time": captcha_ts,
            "verifyCode": captcha
        })
    )
    resp = post(
        request_str_arg_builder(api_mapping[api.LOGIN])
        .concat_ts()
        .fetch(),
        data={
            "data": crypto_helper.encrypt(json.dumps(
                {
                    "keyNumber": uname,
                    "password": pwd,
                    "tenantCode": tenant,
                    "time": captcha_ts,
                    "verifyCode": captcha
                }).replace(" ", ""))
        }
    )

    j = json.loads(resp.text)
    if j["code"] == "0":
        data = j["data"]
        return json_structs.User(
            data["realName"],
            data["tenantCode"],
            data["tenantName"],
            data["token"],
            data["uniqueValue"],
            data["userId"],
            data["userName"]
        ), resp.text
    else:
        return None, resp.text


async def fetch_project_list(tenant: str, user_id: str, ended=2):
    """
    Fetches designated project list according to argument ended.
    :param tenant:
    :param user_id:
    :param ended: when ended==2, function fetches ongoing projects; when ended==1, fetches finished projects instead.
    :return:
    """
    resp = post(
        request_str_arg_builder(api_mapping[api.FETCH_PROJECT_LIST])
        .concat_ts()
        .fetch(),
        data={
            "tenantCode": tenant,
            "userId": user_id,
            "ended": str(ended)
        }
    )

    data = json.loads(resp.text)["data"]
    ret: list = list()
    for d in data:
        ret.append(deepcopy(json_structs.Project(
            project_id=d["projectId"],
            project_name=d["projectName"],
            user_project_id=d["userProjectId"]
        )))
    return deepcopy(ret)


async def fetch_category_list(tenant, user_id, user_project_id, choose_type=3):
    resp = post(
        request_str_arg_builder(api_mapping[api.FETCH_CATEGORY_LIST])
        .concat_ts()
        .fetch(),
        data={
            "tenantCode": tenant,
            "userId": user_id,
            "userProjectId": user_project_id,
            "chooseType": str(choose_type)
        }
    )

    data = json.loads(resp.text)["data"]

    ret: list = list()
    for d in data:
        ret.append(deepcopy(json_structs.Category(
            d["categoryName"],
            d["categoryCode"],
            d["finishedNum"],
            d["totalNum"]
        )))
    return deepcopy(ret)


async def fetch_course_list(tenant, user_id, user_project_id, category_code, choose_type=3):
    resp = post(
        request_str_arg_builder(api_mapping[api.FETCH_COURSE_LIST])
        .concat_ts()
        .fetch(),
        data={
            "tenantCode": tenant,
            "userId": user_id,
            "userProjectId": user_project_id,
            "chooseType": str(choose_type),
            "categoryCode": category_code
        }
    )

    ret: list = list()
    data = json.loads(resp.text)["data"]
    for d in data:
        ret.append(deepcopy(json_structs.Course(
            resource_id=d["resourceId"],
            resource_name=d["resourceName"],
            user_course_id=d["userCourseId"]
        )))

    return deepcopy(ret)


"""
Flow:
STUDY_START -> STUDY_GET_COURSE_URL -> 
STUDY_FETCH_CAPTCHA -> STUDY_CHECK_CAPTCHA ->
STUDY_TERMINATE
"""


async def study_start(tenant, user_id, user_project_id, course_id) -> bool:
    """

    :param tenant:
    :param user_id:
    :param user_project_id:
    :param course_id: resource_id of Course
    :return:
    """
    resp = post(
        request_str_arg_builder(api_mapping[api.STUDY_START])
        .concat_ts()
        .fetch(),
        data={
            "tenantCode": tenant,
            "userId": user_id,
            "courseId": course_id,
            "userProjectId": user_project_id
        }
    )

    if json.loads(resp.text)["code"] == "0":
        dbg_print("Starting " + course_id)
        return True
    else:
        dbg_print("Fail to start " + course_id)
        return False


async def study_get_course_url(tenant, user_id, user_project_id, course_id) -> bool:
    """

    :param tenant:
    :param user_id:
    :param user_project_id:
    :param course_id: resource_id of Course
    :return:
    """
    resp = post(
        request_str_arg_builder(api_mapping[api.STUDY_GET_COURSE_URL])
        .concat_ts()
        .fetch(),
        data={
            "tenantCode": tenant,
            "userId": user_id,
            "courseId": course_id,
            "userProjectId": user_project_id
        }
    )

    if json.loads(resp.text)["code"] == "0":
        dbg_print("Fetching " + course_id)
        return True
    else:
        dbg_print("Fail to fetch " + course_id)
        return False


async def study_fetch_captcha(tenant, user_id, user_project_id, user_course_id) -> json_structs.Captcha:
    """

    :param tenant:
    :param user_id:
    :param user_project_id:
    :param user_course_id: Note that this time must use user_course_id rather than resource_id!!!
    :return:
    """
    resp = post(
        request_str_arg_builder(api_mapping[api.STUDY_FETCH_CAPTCHA])
        .concat("userCourseId", user_course_id)
        .concat("userProjectId", user_project_id)
        .concat("userId", user_id, )
        .concat("tenantCode", tenant)
        .fetch(),
        data={}
    )

    captcha = json.loads(resp.text)["captcha"]
    return json_structs.Captcha(
        image_url=captcha["imageUrl"],
        num=captcha["num"],
        question_id=captcha["questionId"]
    )


async def study_verify_captcha(tenant, user_id, user_project_id,
                               user_course_id, question_id, answer: json_structs.CaptchaAnswer) -> (bool, str):
    """

    :param tenant:
    :param user_id:
    :param user_project_id:
    :param user_course_id:
    :param question_id:
    :param answer:
    :return: A bool, indicating whether the operation has succeeded;
            a string, which is the token for terminating study progress.
    """
    resp = post(
        request_str_arg_builder(api_mapping[api.STUDY_CHECK_CAPTCHA])
        .concat("userCourseId", user_course_id)
        .concat("userProjectId", user_project_id)
        .concat("userId", user_id)
        .concat("tenantCode", tenant)
        .concat("questionId", question_id)
        .fetch(),
        data={
            "coordinateXYs": answer.fetch()
        }
    )

    result = json.loads(resp.text)
    if error_code := result["code"] == "0":
        if (ck := result["data"]["checkResult"]) == 1:
            return True, result["data"]["methodToken"]
        else:
            dbg_print("Failed CAPTCHA with bad answer. CheckResult = " + str(ck))
            return True, result["data"]["methodToken"]
    else:
        dbg_print("Failed CAPTCHA with error code = " + error_code)
    return False, None


def ts_mill() -> int:
    return round(time.time() * 1000)


def jquery_style_callback_parser():
    """
    Parses the given random number and timestamp to jQuery style string
    to be provided to study_terminate() func.

    For instance, it parses:
    Randint,
    Timestamp(ms)
    to:
    jQuery  341             02569642488978181 _ 1723205201708
            version 3.4.1   randint             timestamp(ms)
    :return:
    """
    ts = ts_mill()
    return ("jQuery" + JQUERY_VER + str(random.random()) + "_" + str(ts)).replace(".", ""), ts


async def study_terminate(user_course_id, tenant, captcha_token) -> bool:
    jq, ts = jquery_style_callback_parser()
    resp = post(
        request_str_arg_builder(api_mapping[api.STUDY_TERMINATE])
        .replace("<replace>", captcha_token)
        .concat("callback", jq)
        .concat("userCourseId", user_course_id)
        .concat("tenantCode", tenant)
        .concat("_", ts + 1 / 1000)  # MAGIC Number
        .fetch(),
        data={}
    )

    if "ok" in resp.text:
        # screw it 操了，他真返回一个 jQuery callback and I don't want to make any comment
        # json serializer 直接干开线了
        dbg_print("Finished!")
        return True
    else:
        dbg_print("Failed!")
        return False


async def captcha_crack(tenant, user_id, user_project_id, user_course_id,
                        designated_captcha_id, answer: json_structs.CaptchaAnswer) -> str:
    """

    :param tenant:
    :param user_id:
    :param user_project_id:
    :param user_course_id:
    :param designated_captcha_id:
    :param answer:
    :return: Token of CAPTCHA
    """
    captcha_id = ""
    captcha: json_structs.Captcha
    count = 0
    while captcha_id != designated_captcha_id:
        captcha = await study_fetch_captcha(tenant, user_id, user_project_id, user_course_id)
        captcha_id = captcha.question_id
        count += 1
        if count > CAPTCHA_CRACK_MAX_ITER:
            dbg_print("Maximum CAPTCHA crack iteration limit exceeded!")
            return ""
    success, captcha_token = await study_verify_captcha(tenant, user_id, user_project_id,
                                                        user_course_id, captcha_id, answer)
    return captcha_token


async def learn_course(tenant, user_id, user_project_id, user_course_id, course_id,
                       course_name, user_name) -> bool:
    await study_start(tenant, user_id, user_project_id, course_id)
    await study_get_course_url(tenant, user_id, user_project_id, course_id)

    print("Start learning course", course_name, "with id", course_id,
          ". Please stand by...")
    # PS: this timeout is necessary. Otherwise, the request would be rejected.
    # Do not remove it in further updates.
    # Try to minimize the waiting time by sending requests continuously until no request would be rejected.
    await asyncio.sleep(LEARN_TIMEOUT)  # what can I say
    print("Fetching CAPTCHA of course", course_name, "with id", course_id, ". Starting coroutine...")
    captcha: json_structs.Captcha = await study_fetch_captcha(tenant, user_id, user_project_id, user_course_id)
    print("Verifying CAPTCHA of course", course_name, "with id", course_id, ". Starting coroutine...")
    success, captcha_token = await study_verify_captcha(tenant, user_id, user_project_id, user_course_id,
                                                        captcha.question_id,
                                                        answer=json_structs.CaptchaAnswer(
                                                            json_structs.Position(192, 420),
                                                            json_structs.Position(61, 416),
                                                            json_structs.Position(120, 425)
                                                        ))
    # Interestingly there's no need to "crack" the captcha,
    # for that submitting any answer can bypass the CAPTCHA.

    success = await study_terminate(user_course_id, tenant, captcha_token)
    if success:
        print("Task", course_name, "of user", user_name, "with id", course_id, "terminated successfully.")
    else:
        print("Task", course_name, "of user", user_name, "with id", course_id, "terminated due to failure!")
    return success
