try:
    from fastapi import APIRouter, Header, HTTPException, Depends
    from fastapi.security import OAuth2PasswordRequestForm
    from pydantic import BaseModel
except Exception:
    APIRouter = None
    Header = HTTPException = Depends = OAuth2PasswordRequestForm = None
    BaseModel = object

import threading
from typing import Optional

# Create router only if FastAPI is available; keep router=None otherwise so imports are safe.
router = APIRouter(prefix="/api") if APIRouter is not None else None

if router is not None:
    # Import runtime state lazily to avoid pulling optional deps (passlib, web3)
    from web_server import auth_manager, wl_manager, web3_instance, tracked_tokens, wallet_tracker_threads, wallet_alerts, WATCHLIST
    from backend.Core.wallet_tracker import WalletTracker

    class UserRegister(BaseModel):
        username: str
        password: str


    @router.post("/register")
    def register(u: UserRegister):
        try:
            auth_manager.register_user(u.username, u.password)
            # return access token so client can use it immediately
            token = auth_manager.create_access_token(u.username)
            return {"access_token": token, "token_type": "bearer"}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


    try:
        from fastapi import Request
    except Exception:
        Request = None

    @router.post("/login")
    async def login(request):
        # Robust parsing: try JSON body first, then form data. Always return JSON or an HTTPException.
        user = None
        pw = None

        # try JSON
        try:
            data = await request.json()
            if isinstance(data, dict):
                user = data.get("username") or data.get("user") or data.get("email")
                pw = data.get("password")
        except Exception:
            # not JSON or empty body
            pass

        # try form data if missing
        if not user or not pw:
            try:
                form = await request.form()
                user = user or form.get("username") or form.get("user")
                pw = pw or form.get("password")
            except Exception:
                pass

        if not user or not pw:
            # explicit JSON error body so client.parse doesn't fail on empty response
            raise HTTPException(status_code=400, detail="No credentials provided")

        token = auth_manager.authenticate(user, pw)
        if not token:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"access_token": token, "token_type": "bearer"}


    @router.get("/watchlist")
    def read_watchlist(authorization: str = Header(None)):
        user = auth_manager.get_username_from_auth_header(authorization)
        if user:
            return {"watchlist": wl_manager.get_user_watchlist(user)}
        return {"watchlist": WATCHLIST}


    @router.get("/me")
    def me(authorization: str = Header(None)):
        user = auth_manager.get_username_from_auth_header(authorization)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            uwl = wl_manager.get_user_watchlist(user)
        except Exception:
            uwl = []
        return {"username": user, "watchlist": uwl}


    @router.post("/watchlist/add")
    def add_watchlist(address: str, authorization: str = Header(None)):
        addr = address.lower()
        user = auth_manager.get_username_from_auth_header(authorization)
        if user:
            wl = wl_manager.add_user_watchlist(user, addr)
            return {"watchlist": wl, "added": True}

        wl = wl_manager.get_global_watchlist()
        if addr in wl:
            return {"watchlist": wl, "added": False}
        wl.append(addr)
        wl_manager.save_global_watchlist(wl)

        try:
            if web3_instance is not None:
                wallet_tracker = WalletTracker(web3_instance, set(tracked_tokens), wl)
                t = threading.Thread(target=wallet_tracker.run, daemon=True)
                t.start()
                wallet_tracker_threads.append(t)
                wallet_alerts.append(f"Started wallet tracker for {addr}")
        except Exception as e:
            wallet_alerts.append(f"Failed to start wallet tracker for {addr}: {e}")

        return {"watchlist": wl, "added": True}


    @router.post("/watchlist/remove")
    def remove_watchlist(address: str, authorization: str = Header(None)):
        addr = address.lower()
        user = auth_manager.get_username_from_auth_header(authorization)
        if user:
            wl = wl_manager.remove_user_watchlist(user, addr)
            return {"watchlist": wl, "removed": True}

        wl = wl_manager.get_global_watchlist()
        if addr not in wl:
            return {"watchlist": wl, "removed": False}
        wl = [a for a in wl if a != addr]
        wl_manager.save_global_watchlist(wl)
        wallet_alerts.append(f"Removed {addr} from watchlist")
        return {"watchlist": wl, "removed": True}


    # include token-related routes implemented in token_routes.py
    try:
        # import token_routes at runtime so it's created when FastAPI is available
        from backend.api import token_routes as token_routes_module
        if getattr(token_routes_module, "router", None) is not None:
            router.include_router(token_routes_module.router)
    except Exception:
        # if token routes cannot be imported, continue without them
        pass
