"""Shared application logic, independent of HTTP and any web framework."""


class InputError(Exception):
    pass


class UserStore:
    def __init__(self):
        self._users = {}
        self._next_id = 1

    def list_users(self):
        return {"users": list(self._users.values())}

    def get_user(self, user_id):
        user = self._users.get(user_id)
        if user is None:
            return None
        return user

    def create_user(self, payload):
        if not isinstance(payload, dict):
            raise InputError("JSON body must be an object")

        name = payload.get("name")
        age = payload.get("age")

        if not isinstance(name, str) or not name.strip():
            raise InputError("name must be a non-empty string")
        if type(age) is not int or age < 0:
            raise InputError("age must be a non-negative integer")

        user = {"id": self._next_id, "name": name.strip(), "age": age}
        self._users[self._next_id] = user
        self._next_id += 1
        return user
