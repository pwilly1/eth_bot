import os
import time
import json
from typing import Optional
from passlib.context import CryptContext
from jose import jwt, JWTError


class AuthManager:
    def __init__(self, users_collection=None, users_dir: str = "resources/users", jwt_secret: str = None):
        self.users_collection = users_collection
        self.users_dir = users_dir
        os.makedirs(self.users_dir, exist_ok=True)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret = jwt_secret or os.getenv("JWT_SECRET", "dev-secret")
        self.alg = "HS256"

    def hash_password(self, pw: str) -> str:
        return self.pwd_context.hash(pw)

    def verify_password(self, plain: str, hashed: str) -> bool:
        try:
            return self.pwd_context.verify(plain, hashed)
        except Exception:
            return False

    def create_access_token(self, username: str, expires: int = 3600) -> str:
        payload = {"sub": username, "exp": int(time.time()) + int(expires)}
        return jwt.encode(payload, self.secret, algorithm=self.alg)

    def decode_token(self, token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.alg])
            return payload.get("sub")
        except JWTError:
            return None

    # persistence helpers
    def _read_user_file(self, username: str):
        path = os.path.join(self.users_dir, f"{username}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)

    def register_user(self, username: str, password: str):
        if self.users_collection is not None:
            if self.users_collection.find_one({"username": username}):
                raise ValueError("User exists")
            self.users_collection.insert_one({"username": username, "password": self.hash_password(password), "watchlist": []})
            return True

        # file fallback
        if self._read_user_file(username):
            raise ValueError("User exists")
        path = os.path.join(self.users_dir, f"{username}.json")
        with open(path, "w") as f:
            json.dump({"username": username, "password": self.hash_password(password), "watchlist": []}, f)
        return True

    def authenticate(self, username: str, password: str) -> Optional[str]:
        record = None
        if self.users_collection is not None:
            record = self.users_collection.find_one({"username": username})
        else:
            record = self._read_user_file(username)

        if not record:
            return None
        if not self.verify_password(password, record.get("password", "")):
            return None
        return self.create_access_token(username)

    def get_username_from_auth_header(self, auth_header: Optional[str]) -> Optional[str]:
        if not auth_header:
            return None
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
        else:
            token = auth_header
        return self.decode_token(token)
