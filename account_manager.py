import json
import os.path
import functools


class Account:
    uname: str
    pwd: str
    tenant: str

    def __init__(self, uname, pwd, tenant):
        self.uname = uname
        self.pwd = pwd
        self.tenant = tenant


class AccountManager:
    __accounts: list[Account]

    @property
    def accounts(self) -> list[Account]:
        return self.__accounts

    def __init__(self):
        if not os.path.exists("./accounts.json"):
            with open("./accounts.json", "w", encoding="utf-8") as f:
                struct = {
                    "accounts": [
                        {
                            "uname": "placeholder",
                            "pwd": "pwd",
                            "tenant": "114514"
                        }
                    ]
                }

                t = json.dumps(struct)
                f.write(t)
                f.close()

        self.__accounts = list()
        self.refresh()

    def refresh(self):
        self.__accounts.clear()
        with open("./accounts.json", "r", encoding="utf-8") as f:
            data = json.loads(functools.reduce(lambda x, y: x + y, f.readlines()))
            for acc in data["accounts"]:
                self.__accounts.append(
                    Account(
                        acc["uname"],
                        acc["pwd"],
                        acc["tenant"]
                    )
                )
            f.close()

        return self

    def fetch(self, uname) -> Account:
        for i in self.__accounts:
            if i.uname == uname:
                return i

    def append(self, uname, pwd, tenant):
        self.__accounts.append(
            Account(
                uname,
                pwd,
                tenant
            )
        )
        return self

    def contain(self, uname) -> bool:
        for i in self.__accounts:
            if i.uname == uname:
                return True
        return False

    def delete(self, uname):
        for i in self.__accounts:
            if i.uname == uname:
                self.__accounts.remove(i)
                return self

    def save(self):
        with open("./accounts.json", "w", encoding="utf-8") as f:
            struct = {
                "accounts": []
            }

            for i in self.__accounts:
                struct["accounts"].append(
                    {
                        "uname": i.uname,
                        "pwd": i.pwd,
                        "tenant": i.tenant
                    }
                )

            j = json.dumps(struct)
            f.write(j)
            f.close()

        return self
