import os
import json
from typing import List, Optional


class WatchlistManager:
    def __init__(self, watchlist_collection=None, users_collection=None, resources_dir: str = "resources"):
        self.watchlist_collection = watchlist_collection
        self.users_collection = users_collection
        self.resources_dir = resources_dir
        os.makedirs(self.resources_dir, exist_ok=True)

    def get_global_watchlist(self) -> List[str]:
        # Use DB-backed global watchlist when a collection is available.
        if self.watchlist_collection is not None:
            docs = list(self.watchlist_collection.find({}, {"_id": 0, "address": 1}))
            return [d.get("address", "").lower() for d in docs]
        # file-backed
        try:
            with open(os.path.join(self.resources_dir, "watchlist.json"), "r") as f:
                return [a.lower() for a in json.load(f)]
        except Exception:
            return []

    def save_global_watchlist(self, wl: List[str]):
        if self.watchlist_collection is not None:
            # rewrite collection with idempotent upserts
            for a in wl:
                try:
                    self.watchlist_collection.update_one({"address": a}, {"$set": {"address": a}}, upsert=True)
                except Exception:
                    pass
        else:
            with open(os.path.join(self.resources_dir, "watchlist.json"), "w") as f:
                json.dump(wl, f, indent=2)

    def get_user_watchlist(self, username: str) -> List[str]:
        if self.users_collection is not None:
            doc = self.users_collection.find_one({"username": username}, {"_id": 0, "watchlist": 1}) or {}
            return doc.get("watchlist", [])
        # file fallback
        path = os.path.join(self.resources_dir, f"watchlist_{username}.json")
        try:
            with open(path, "r") as f:
                return [a.lower() for a in json.load(f)]
        except Exception:
            return []

    def add_user_watchlist(self, username: str, addr: str) -> List[str]:
        addr = addr.lower()
        if self.users_collection is not None:
            self.users_collection.update_one({"username": username}, {"$addToSet": {"watchlist": addr}})
            return self.get_user_watchlist(username)
        path = os.path.join(self.resources_dir, f"watchlist_{username}.json")
        wl = self.get_user_watchlist(username)
        if addr not in wl:
            wl.append(addr)
            with open(path, "w") as f:
                json.dump(wl, f, indent=2)
        return wl

    def remove_user_watchlist(self, username: str, addr: str) -> List[str]:
        addr = addr.lower()
        if self.users_collection is not None:
            self.users_collection.update_one({"username": username}, {"$pull": {"watchlist": addr}})
            return self.get_user_watchlist(username)
        path = os.path.join(self.resources_dir, f"watchlist_{username}.json")
        wl = self.get_user_watchlist(username)
        if addr in wl:
            wl = [a for a in wl if a != addr]
            with open(path, "w") as f:
                json.dump(wl, f, indent=2)
        return wl
