"""Import-tolerant token routes.

This module only creates a FastAPI router when FastAPI is available. All runtime
state (from web_server) and optional third-party exceptions are imported lazily
inside the route handlers so importing the package won't fail in environments
without FastAPI/pymongo/web3.
"""

try:
    from fastapi import APIRouter, Query, HTTPException
    from typing import List, Dict, Any, Optional
    from datetime import datetime, timezone
    import time

    router = APIRouter()

    def _get_pymongo_exceptions():
        try:
            from pymongo.errors import ServerSelectionTimeoutError, PyMongoError
            return ServerSelectionTimeoutError, PyMongoError
        except Exception:
            return Exception, Exception


    @router.get("/status")
    def get_status():
        from web_server import status_messages
        return {"status": status_messages[-1] if status_messages else "No status yet."}


    @router.get("/wallet_alerts")
    def get_wallet_alerts():
        from web_server import wallet_alerts
        return {"wallet_alerts": wallet_alerts}


    @router.get("/token_events")
    def get_token_events(
        q: Optional[str] = Query(None, description="search token address/name/symbol"),
        honeypot: Optional[bool] = Query(None, description="filter honeypot true/false"),
        min_liquidity: Optional[float] = Query(None, description="minimum liquidity in ETH"),
        ownership: Optional[bool] = Query(None, description="ownership renounced true/false"),
        start_ms: Optional[int] = Query(None, description="start time in ms since epoch"),
        end_ms: Optional[int] = Query(None, description="end time in ms since epoch"),
        limit: int = Query(200, description="max results"),
    ):
        PSE, PME = _get_pymongo_exceptions()
        try:
            from web_server import token_collection, token_events

            docs: List[Dict[str, Any]] = []

            # start of today (local timezone -> utc)
            local_now = datetime.now().astimezone()
            start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_day = int(start_local.astimezone(timezone.utc).timestamp())

            if start_ms is not None:
                start_of_day = int(start_ms // 1000)
            end_of_day: Optional[int] = None
            if end_ms is not None:
                end_of_day = int(end_ms // 1000)

            if token_collection is not None:
                query: Dict[str, Any] = {"timestamp": {"$gte": start_of_day}}
                if end_of_day is not None:
                    query["timestamp"]["$lte"] = end_of_day
                if honeypot is not None:
                    query["honeypot"] = bool(honeypot)
                if min_liquidity is not None:
                    query["liquidity_eth"] = {"$gte": float(min_liquidity)}
                if ownership is not None:
                    query["ownership_renounced"] = bool(ownership)
                if q:
                    regex = {"$regex": q, "$options": "i"}
                    query["$or"] = [
                        {"address": regex},
                        {"token0_info.address": regex},
                        {"token1_info.address": regex},
                        {"token0_info.name": regex},
                        {"token1_info.name": regex},
                        {"token0_info.symbol": regex},
                        {"token1_info.symbol": regex},
                    ]

                fields = {
                    "_id": 0,
                    "timestamp": 1,
                    "address": 1,
                    "liquidity_eth": 1,
                    "honeypot": 1,
                    "ownership_renounced": 1,
                    "token0_info": 1,
                    "token1_info": 1,
                }
                docs = list(token_collection.find(query, fields).sort("timestamp", -1).limit(limit))
            else:
                for e in token_events:
                    ts = int(e.get("timestamp", 0))
                    if ts < start_of_day:
                        continue
                    if end_of_day is not None and ts > end_of_day:
                        continue
                    if honeypot is not None and bool(e.get("honeypot", False)) != bool(honeypot):
                        continue
                    if min_liquidity is not None and float(e.get("liquidity_eth", 0.0)) < float(min_liquidity):
                        continue
                    if ownership is not None and bool(e.get("ownership_renounced", False)) != bool(ownership):
                        continue
                    if q:
                        ql = q.lower()
                        found = False
                        for val in [
                            str(e.get("address", "")),
                            str((e.get("token0_info") or {}).get("address", "")),
                            str((e.get("token1_info") or {}).get("address", "")),
                            str((e.get("token0_info") or {}).get("name", "")),
                            str((e.get("token1_info") or {}).get("name", "")),
                            str((e.get("token0_info") or {}).get("symbol", "")),
                            str((e.get("token1_info") or {}).get("symbol", "")),
                        ]:
                            if ql in val.lower():
                                found = True
                                break
                        if not found:
                            continue
                    docs.append(e)
                docs = sorted(docs, key=lambda x: int(x.get("timestamp", 0)), reverse=True)[:limit]

            safe = []
            for d in docs:
                safe.append({
                    "timestamp": int(d.get("timestamp", 0)) * 1000,
                    "address": str(d.get("address", "")),
                    "liquidity_eth": float(d.get("liquidity_eth", 0.0)),
                    "honeypot": bool(d.get("honeypot", False)),
                    "ownership_renounced": bool(d.get("ownership_renounced", False)),
                    "token0": d.get("token0_info") or {},
                    "token1": d.get("token1_info") or {},
                })
            return {"token_events": safe}

        except Exception as e:
            try:
                from web_server import status_messages, token_events as _token_events
                status_messages.append(f"Mongo error or handler failure: {e}")
                safe_mem = [{
                    "timestamp": int(ev.get("timestamp", 0)) * 1000,
                    "address": str(ev.get("address", "")),
                    "liquidity_eth": float(ev.get("liquidity_eth", 0.0)),
                    "honeypot": bool(ev.get("honeypot", False)),
                    "ownership_renounced": bool(ev.get("ownership_renounced", False)),
                    "token0": ev.get("token0_info") or {},
                    "token1": ev.get("token1_info") or {},
                } for ev in _token_events]
                return {"token_events": safe_mem}
            except Exception:
                raise HTTPException(status_code=500, detail=f"/api/token_events failed: {e}")


    @router.get("/historical_data")
    def get_historical_data(
        q: Optional[str] = Query(None, description="search token address/name/symbol"),
        honeypot: Optional[bool] = Query(None, description="filter honeypot true/false"),
        min_liquidity: Optional[float] = Query(None, description="minimum liquidity in ETH"),
        ownership: Optional[bool] = Query(None, description="ownership renounced true/false"),
        start_ms: Optional[int] = Query(None, description="start time in ms since epoch"),
        end_ms: Optional[int] = Query(None, description="end time in ms since epoch"),
        limit: int = Query(500, description="max results"),
    ):
        try:
            from web_server import token_collection, token_events
            docs: List[Dict[str, Any]] = []
            if token_collection is not None:
                query: Dict[str, Any] = {}
                if honeypot is not None:
                    query["honeypot"] = bool(honeypot)
                if min_liquidity is not None:
                    query["liquidity_eth"] = {"$gte": float(min_liquidity)}
                if ownership is not None:
                    query["ownership_renounced"] = bool(ownership)
                if start_ms is not None or end_ms is not None:
                    query["timestamp"] = {}
                    if start_ms is not None:
                        query["timestamp"]["$gte"] = int(start_ms // 1000)
                    if end_ms is not None:
                        query["timestamp"]["$lte"] = int(end_ms // 1000)
                if q:
                    regex = {"$regex": q, "$options": "i"}
                    query["$or"] = [
                        {"address": regex},
                        {"token0_info.address": regex},
                        {"token1_info.address": regex},
                        {"token0_info.name": regex},
                        {"token1_info.name": regex},
                        {"token0_info.symbol": regex},
                        {"token1_info.symbol": regex},
                    ]

                fields = {
                    "_id": 0,
                    "timestamp": 1,
                    "liquidity_eth": 1,
                    "honeypot": 1,
                    "ownership_renounced": 1,
                    "token0_info": 1,
                    "token1_info": 1,
                    "address": 1,
                }
                docs = list(token_collection.find(query, fields).sort("timestamp", -1).limit(limit))
            else:
                for e in token_events:
                    if honeypot is not None and bool(e.get("honeypot", False)) != bool(honeypot):
                        continue
                    if min_liquidity is not None and float(e.get("liquidity_eth", 0.0)) < float(min_liquidity):
                        continue
                    if ownership is not None and bool(e.get("ownership_renounced", False)) != bool(ownership):
                        continue
                    if start_ms is not None and int(e.get("timestamp", 0)) * 1000 < start_ms:
                        continue
                    if end_ms is not None and int(e.get("timestamp", 0)) * 1000 > end_ms:
                        continue
                    if q:
                        ql = q.lower()
                        found = False
                        for val in [
                            str(e.get("address", "")),
                            str((e.get("token0_info") or {}).get("address", "")),
                            str((e.get("token1_info") or {}).get("address", "")),
                            str((e.get("token0_info") or {}).get("name", "")),
                            str((e.get("token1_info") or {}).get("name", "")),
                            str((e.get("token0_info") or {}).get("symbol", "")),
                            str((e.get("token1_info") or {}).get("symbol", "")),
                        ]:
                            if ql in val.lower():
                                found = True
                                break
                            if not found:
                                continue
                    docs.append(e)
                docs = sorted(docs, key=lambda x: int(x.get("timestamp", 0)), reverse=True)[:limit]

            out = []
            for e in docs:
                t0 = e.get("token0_info") or e.get("token0") or {}
                t1 = e.get("token1_info") or e.get("token1") or {}
                out.append({
                    "timestamp": int(e.get("timestamp", 0)) * 1000,
                    "liquidity_eth": float(e.get("liquidity_eth", 0.0)),
                    "honeypot": bool(e.get("honeypot", False)),
                    "ownership_renounced": bool(e.get("ownership_renounced", False)),
                    "token0": {
                        "name": str(t0.get("name", "")),
                        "symbol": str(t0.get("symbol", "")),
                        "address": str(t0.get("address", "")),
                    },
                    "token1": {
                        "name": str(t1.get("name", "")),
                        "symbol": str(t1.get("symbol", "")),
                        "address": str(t1.get("address", "")),
                    },
                    "address": str(e.get("address", "")),
                })
            return out
        except Exception as ex:
            try:
                from web_server import status_messages
                status_messages.append(f"historical_data failure: {ex}")
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"/api/historical_data failed: {ex}")


    @router.get("/token/{address}")
    def get_token_detail(address: str):
        try:
            addr = address.lower()
            from web_server import token_collection, token_events
            if token_collection is not None:
                doc = token_collection.find_one({"address": {"$regex": f"^{addr}$", "$options": "i"}}, {"_id": 0})
            else:
                doc = next((e for e in token_events if str(e.get("address", "")).lower() == addr), None)

            if not doc:
                raise HTTPException(status_code=404, detail="Token not found")

            t0 = doc.get("token0_info") or doc.get("token0") or {}
            t1 = doc.get("token1_info") or doc.get("token1") or {}

            return {
                "timestamp": int(doc.get("timestamp", 0)) * 1000,
                "address": str(doc.get("address", "")),
                "pair_address": str(doc.get("pair_address", "")),
                "liquidity_eth": float(doc.get("liquidity_eth", 0.0)),
                "honeypot": bool(doc.get("honeypot", False)),
                "ownership_renounced": bool(doc.get("ownership_renounced", False)),
                "token0": {"name": str(t0.get("name", "")), "symbol": str(t0.get("symbol", "")), "address": str(t0.get("address", ""))},
                "token1": {"name": str(t1.get("name", "")), "symbol": str(t1.get("symbol", "")), "address": str(t1.get("address", ""))},
                "raw": doc,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"/api/token/{address} failed: {e}")

except Exception:
    # FastAPI or other imports failed; export router=None so package import is safe.
    router = None

