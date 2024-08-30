import asyncio
import functools
import json
import time
from copy import deepcopy
from typing import Optional

import requests
import urllib3
from urllib3 import exceptions

import crypto_helper
import json_structs
from config import *
from web_utils import api, api_mapping, dbg_print, request_str_arg_builder, jquery_style_callback_parser

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main_print(*msg, end="\n"):
    print("[Main]", *msg, end=end)


class AccountEntity:
    """
    This is a variant of web_utils for multi-account purposes.
    """
    headers = {
        "X-Token": "",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/127.0.0.0 "
                      "Safari/537.36 Edg/127.0.0.0 "
    }

    proxies = {
        "http": None,
        "https": None
    }

    user: json_structs.User
    id_: int

    def __init__(self, user: json_structs.User, id_: int):
        self.user = user
        self.set_token(user.token)
        self.id_ = id_

    def entity_print(self, *args, end="\n"):
        print(f"[Coroutine Entity {0}]".format(self.id_), *args, "of user", self.user.user_name, end=end)

    def set_token(self, token):
        """
        Must be executed right after calling login()
        :param token:
        :return:
        """
        self.headers["X-Token"] = token

    def post(self, url, data: dict, cookies: object = None) -> requests.Response:
        dbg_print("POST " + url)
        dbg_print("Parameters: " + json.dumps(data))
        if cookies is None:
            cookies = {}
        resp: requests.Response = requests.post(url, data=data, headers=self.headers, cookies=cookies,
                                                timeout=5, verify=False, proxies=self.proxies)
        if len(t := resp.text) < config_instance.DEBUG_PRINT_MAX_LEN:
            dbg_print("Response: " + t)
        else:
            dbg_print("Response: " + t[0:65536])
        return resp

    def get(self, url, cookies=None) -> requests.Response:
        dbg_print("GET " + url)
        if cookies is None:
            cookies = {}
        resp: requests.Response = requests.get(url, headers=self.headers, cookies=cookies,
                                               timeout=5, verify=False, proxies=self.proxies)
        if len(t := resp.text) < config_instance.DEBUG_PRINT_MAX_LEN:
            dbg_print("Response: " + t)
        else:
            dbg_print("Response: " + t[0:65536])
        return resp

    def fetch_login_captcha(self) -> (requests.Response, int):
        current_time = time.time()
        return self.get(
            request_str_arg_builder(api_mapping[api.GET_LOGIN_CAPTCHA])
            .concat("time", str(round(current_time * 1000)))
            .fetch(),
        ), current_time

    def fetch_all_tenants(self) -> dict[str, str]:
        resp = self.post(
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

    def fetch_tenant_conf(self, tenant_code: str):
        resp = self.post(
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

    async def login(self, tenant: str, uname: str, pwd: str, captcha: str, captcha_ts: float)\
            -> (Optional[json_structs.User], str):
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
        resp = self.post(
            request_str_arg_builder(api_mapping[api.LOGIN])
            .concat_ts()
            .fetch(),
            data={
                "data": crypto_helper.encrypt(
                    json.dumps(
                        {
                            "keyNumber": uname,
                            "password": pwd,
                            "tenantCode": tenant,
                            "time": captcha_ts,
                            "verifyCode": captcha
                        }
                    ).replace(" ", "")
                )
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

    async def fetch_project_list(self, tenant: str, user_id: str, ended=2):
        """
        Fetches designated project list according to argument ended.
        :param tenant:
        :param user_id:
        :param ended: when ended==2, function fetches ongoing projects;
        when ended==1, fetches finished projects instead.
        :return:
        """
        resp = self.post(
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
            ret.append(
                deepcopy(
                    json_structs.Project(
                        project_id=d["projectId"],
                        project_name=d["projectName"],
                        user_project_id=d["userProjectId"]
                    )
                )
            )
        return deepcopy(ret)

    async def fetch_category_list(self, tenant, user_id, user_project_id, choose_type=3):
        resp = self.post(
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
            ret.append(
                deepcopy(
                    json_structs.Category(
                        d["categoryName"],
                        d["categoryCode"],
                        d["finishedNum"],
                        d["totalNum"]
                    )
                )
            )
        return deepcopy(ret)

    async def fetch_course_list(self, tenant, user_id, user_project_id, category_code, choose_type=3):
        resp = self.post(
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
            ret.append(
                deepcopy(
                    json_structs.Course(
                        resource_id=d["resourceId"],
                        resource_name=d["resourceName"],
                        user_course_id=d["userCourseId"]
                    )
                )
            )

        return deepcopy(ret)

    """
    Flow:
    STUDY_START -> STUDY_GET_COURSE_URL -> 
    STUDY_FETCH_CAPTCHA -> STUDY_CHECK_CAPTCHA ->
    STUDY_TERMINATE
    """

    async def study_start(self, tenant, user_id, user_project_id, course_id) -> bool:
        """

        :param tenant:
        :param user_id:
        :param user_project_id:
        :param course_id: resource_id of Course
        :return:
        """
        resp = self.post(
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

    async def study_get_course_url(self, tenant, user_id, user_project_id, course_id) -> bool:
        """

        :param tenant:
        :param user_id:
        :param user_project_id:
        :param course_id: resource_id of Course
        :return:
        """
        resp = self.post(
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

    async def study_fetch_captcha(self, tenant, user_id, user_project_id, user_course_id) -> json_structs.Captcha:
        """

        :param tenant:
        :param user_id:
        :param user_project_id:
        :param user_course_id: Note that this time must use user_course_id rather than resource_id!!!
        :return:
        """
        resp = self.post(
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

    async def study_verify_captcha(self, tenant, user_id, user_project_id,
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
        resp = self.post(
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

    async def study_terminate(self, user_course_id, tenant, captcha_token) -> bool:
        jq, ts = jquery_style_callback_parser()
        resp = self.post(
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
            dbg_print("Finished!")
            return True
        else:
            dbg_print("Failed!")
            return False

    async def captcha_crack(self, tenant, user_id, user_project_id, user_course_id,
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
            captcha = await self.study_fetch_captcha(tenant, user_id, user_project_id, user_course_id)
            captcha_id = captcha.question_id
            count += 1
            if count > config_instance.CAPTCHA_CRACK_MAX_ITER:
                dbg_print("Maximum CAPTCHA crack iteration limit exceeded!")
                return ""
        success, captcha_token = await self.study_verify_captcha(
            tenant, user_id, user_project_id,
            user_course_id, captcha_id, answer
        )
        return captcha_token

    async def learn_course(self, tenant, user_id, user_project_id, user_course_id, course_id,
                           course_name, user_name) -> bool:
        await self.study_start(tenant, user_id, user_project_id, course_id)
        await self.study_get_course_url(tenant, user_id, user_project_id, course_id)

        self.entity_print("Start learning course", course_name, "with id", course_id,
                          ". Please stand by...")
        await asyncio.sleep(config_instance.LEARN_TIMEOUT)
        self.entity_print("Fetching CAPTCHA of course", course_name, "with id", course_id, ". Starting coroutine...")
        captcha: json_structs.Captcha = await self.study_fetch_captcha(tenant, user_id, user_project_id, user_course_id)
        self.entity_print("Verifying CAPTCHA of course", course_name, "with id", course_id, ". Starting coroutine...")
        success, captcha_token = await self.study_verify_captcha(
            tenant, user_id, user_project_id, user_course_id,
            captcha.question_id,
            answer=json_structs.CaptchaAnswer(
                json_structs.Position(192, 420),
                json_structs.Position(61, 416),
                json_structs.Position(120, 425)
            )
        )

        success = await self.study_terminate(user_course_id, tenant, captcha_token)
        if success:
            self.entity_print("Task", course_name, "of user", user_name, "with id", course_id,
                              "terminated successfully.")
        else:
            self.entity_print("Task", course_name, "of user", user_name, "with id", course_id,
                              "terminated due to failure!")
        return success

    async def main(self):
        self.entity_print("Start fetching all ongoing projects...")
        projects: list[json_structs.Project] = await self.fetch_project_list(self.user.tenant_code, self.user.user_id)

        for p in projects:
            start = time.time()

            courses: list[json_structs.Course] = list()
            self.entity_print("Ongoing project:", p.project_name, "ID:", p.project_id, "User Project ID:",
                              p.user_project_id)
            categories: list[json_structs.Category] = \
                await self.fetch_category_list(self.user.tenant_code, self.user.user_id, p.user_project_id)

            task_courses: list = list()
            for c in categories:
                self.entity_print("Ongoing category:", c.category_name, "ID:", c.category_code)
                if (not c.finished) or (not config_instance.IGNORE_FINISHED_TASKS):
                    task_courses.append(
                        asyncio.create_task(
                            self.fetch_course_list(
                                self.user.tenant_code, self.user.user_id,
                                p.user_project_id, c.category_code
                            )
                        )
                    )
            self.entity_print("Starting to fetch ongoing courses asynchronously...")
            if not len(task_courses) == 0:
                courses = functools.reduce(lambda x, y: x + y, await asyncio.gather(*task_courses))
                self.entity_print("Detected", len(courses), "courses to be finished.")
                tasks: list = list()

                cnt = 0
                for c in courses:
                    tasks.append(
                        asyncio.create_task(
                            self.learn_course(
                                self.user.tenant_code, self.user.user_id,
                                p.user_project_id, c.user_course_id, c.resource_id,
                                c.resource_name, self.user.user_name
                            )
                        )
                    )

                    cnt += 1
                    if cnt >= config_instance.MAX_TASK_NUM:
                        break

                self.entity_print("Gathered", total_cnt := len(tasks), "tasks in total. Starting coroutines...")
                result = await asyncio.gather(*tasks)

                end = time.time()

                success_cnt = 0
                for r in result:
                    if r:
                        success_cnt += 1

                time_elapsed = end - start
                self.entity_print("Succeeded tasks:", success_cnt, "of", total_cnt, end=".\n")
            else:
                self.entity_print("This project has been finished before.")
                time_elapsed = 0
            self.entity_print("Ongoing task of Project", p.project_name, "successfully terminated in", time_elapsed,
                              "secs.")

        self.entity_print("All ongoing tasks successfully terminated.")

    async def run(self) -> bool:
        try:
            await self.main()
        except:
            return False
        finally:
            return True


class AccountEntityManager:
    account_entities: list[AccountEntity]
    entity_id: int

    def __init__(self):
        self.account_entities = list()
        self.entity_id = 0

    def add_entity(self, entity: AccountEntity):
        entity.id_ = self.entity_id
        self.account_entities.append(entity)
        self.entity_id += 1

        return self

    def remove_entity(self, entity_id: int):
        for i in self.account_entities:
            if i.id_ == entity_id:
                self.account_entities.remove(i)
                return self

    def fetch_entity(self, entity_id: int) -> AccountEntity:
        for i in self.account_entities:
            if i.id_ == entity_id:
                return i

    async def start_all_instances(self):
        tasks = list()
        cnt_all = len(self.account_entities)
        cnt = 1
        for entity in self.account_entities:
            main_print("Generating task", cnt, "of", cnt_all, "tasks...")
            tasks.append(
                asyncio.create_task(
                    entity.run()
                )
            )

        main_print("Starting all instances...")

        success_cnt = 0
        result = await asyncio.gather(*tasks)
        for r in result:
            if r:
                success_cnt += 1

        main_print("All", cnt_all, "running instances have quited with", success_cnt, "succeeded instances.")


class AccountEntityFactory:
    def make_entity(self, session: json_structs.User) -> AccountEntity:
        return AccountEntity(session, 0)

    def make_entity_from_sessions(self, sessions: list[json_structs.User]) -> list[AccountEntity]:
        ret = list()
        for sess in sessions:
            ret.append(
                AccountEntity(
                    sess, 0
                )
            )
        return ret

    def make_entity_from_account_data(self, json_filename: str):
        # TODO
        pass


class SingletonHolder:
    factory: AccountEntityFactory
    manager: AccountEntityManager

    def __init__(self):
        self.manager = AccountEntityManager()
        self.factory = AccountEntityFactory()


web_utils2: SingletonHolder = SingletonHolder()
