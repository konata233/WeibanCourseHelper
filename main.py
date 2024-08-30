# Wei-ban Course Helper NWPU ver. 1.0
# Do not use it for illegal purposes.
# Do not distribute!

import asyncio
import functools
import sys
import time
from datetime import datetime

import json_structs
import ui_helper
import web_utils
from account_manager import AccountManager
from config import *


def dbg_print(msg: str):
    if config_instance.DEBUG:
        now: datetime = datetime.now()
        print(f"[DEBUG] [{now}] {msg}")


async def main():
    print(config_instance.MAX_TASK_NUM)
    session = None
    account_manager: AccountManager = AccountManager().refresh()

    if (opt := input("Use normal login method or use cookie? \n"
                     "Input 1 for cookie, 2 for saved account info, otherwise normal login. >>").strip()) == "1":
        token = input("Token here >>").strip()
        user_id = input("User ID here >>").strip()
        tenant_code = input("Tenant code here (press enter to use school name instead) >>").strip()
        if tenant_code == "":
            school_name = input("School name here >>").strip()
            tenant_code = web_utils.fetch_all_tenants()[school_name]
        session = json_structs.User(
            token=token,
            user_id=user_id,
            tenant=tenant_code
        )
    elif opt == "2":
        uname = ""
        print("Saved accounts:")
        dbg_print(str(len(account_manager.accounts)))
        for i in account_manager.accounts:
            print(i.uname)
        while not account_manager.contain(uname):
            uname = input("User name here >>")
            print("User not found. Try again or use Ctrl-C to quit.") \
                if not account_manager.contain(uname) else print("User found.")

        user = account_manager.fetch(uname)

        while session is None:
            captcha, ts_sec = web_utils.fetch_login_captcha()
            print("After viewing the CAPTCHA, close the window to continue.")
            print("Do not input any text now!")
            ui_helper.display_img(captcha.content)
            captcha_result = input("CAPTCHA here >>")

            session, msg = await web_utils.login(user.tenant, user.uname, user.pwd, captcha_result, ts_sec)
            if session is None:
                print("Error occurred. Please retry or use Ctrl-C to quit.", msg)

    else:
        tenants = web_utils.fetch_all_tenants()
        dbg_print(str(len(tenants)))

        while (inp := input("Your school name here >>").strip()) not in tenants.keys():
            print("School not found:", inp, ". Please try again.")

        my_tenant = tenants[inp]
        dbg_print(my_tenant)

        uname_prompt, pwd_prompt = web_utils.fetch_tenant_conf(my_tenant)
        print("Customized username prompt:", uname_prompt)
        user_name = input("Username here >>").strip()

        pwd = ""
        if account_manager.contain(user_name):
            print("This account has been saved previously.")
            if input("Do you want to input the password automatically? ([Y]es / [N]o) >>")[0].lower() == "y":
                pwd = account_manager.fetch(user_name).pwd
            else:
                if input("Have you altered your account settings"
                         "(e.g. password, school, etc.)? ([Y]es / [N]o) >>")[0].lower() == "y":
                    new_pwd = input("New password here >>")
                    account_manager.delete(user_name).append(user_name, new_pwd, my_tenant)
                    print("Please restart the script.")
                    sys.exit(0)

        if pwd == "":
            print("Customized pwd prompt:", pwd_prompt)
            pwd = input("Password here >>").strip()

        while session is None:
            captcha, ts_sec = web_utils.fetch_login_captcha()
            print("After viewing the CAPTCHA, close the window to continue.")
            print("Do not input any text now!")
            ui_helper.display_img(captcha.content)
            captcha_result = input("CAPTCHA here >>")

            session, msg = await web_utils.login(my_tenant, user_name, pwd, captcha_result, ts_sec)
            if session is None:
                print("Error occurred. Please retry or use Ctrl-C to quit.", msg)

        if session is not None and not account_manager.contain(user_name):
            if input("Do you want to save your account data? ([Y]es / [N]o) >>")[0].lower() == "y":
                account_manager\
                    .append(user_name, pwd, my_tenant)\
                    .save()
            else:
                print("User data not saved.")

    if session is None:
        print("FATAL: login failed with bad return value.")
        sys.exit(0)

    # IMPORTANT!!!
    web_utils.set_token(session.token)

    print("Start fetching all ongoing projects...")
    projects: list[json_structs.Project] = await web_utils.fetch_project_list(session.tenant_code, session.user_id)

    for p in projects:
        start = time.time()

        courses: list[json_structs.Course] = list()
        print("Ongoing project:", p.project_name, "ID:", p.project_id, "User Project ID:", p.user_project_id)
        categories: list[json_structs.Category] = \
            await web_utils.fetch_category_list(session.tenant_code, session.user_id, p.user_project_id)

        task_courses: list = list()
        for c in categories:
            print("Ongoing category:", c.category_name, "ID:", c.category_code)
            if (not c.finished) or (not config_instance.IGNORE_FINISHED_TASKS):
                task_courses.append(
                    asyncio.create_task(
                        web_utils.fetch_course_list(
                            session.tenant_code, session.user_id,
                            p.user_project_id, c.category_code
                        )
                    )
                )
        print("Starting to fetch ongoing courses asynchronously...")
        if not len(task_courses) == 0:
            courses = functools.reduce(lambda x, y: x + y, await asyncio.gather(*task_courses))
            print("Detected", len(courses), "courses to be finished.")
            tasks: list = list()

            cnt = 0
            for c in courses:
                tasks.append(
                    asyncio.create_task(
                        web_utils.learn_course(
                            session.tenant_code, session.user_id,
                            p.user_project_id, c.user_course_id, c.resource_id,
                            c.resource_name, session.user_name
                        )
                    )
                )

                cnt += 1
                if cnt >= config_instance.MAX_TASK_NUM:
                    break

            print("Gathered", total_cnt := len(tasks), "tasks in total. Starting coroutines...")
            result = await asyncio.gather(*tasks)

            end = time.time()

            success_cnt = 0
            for r in result:
                if r:
                    success_cnt += 1

            time_elapsed = end - start
            print("Succeeded tasks:", success_cnt, "of", total_cnt, end=".\n")
        else:
            print("This project has been finished before.")
            time_elapsed = 0
        print("Ongoing task of Project", p.project_name, "successfully terminated in", time_elapsed, "secs.")

    print("All ongoing tasks successfully terminated.")


if __name__ == "__main__":
    asyncio.run(main())
