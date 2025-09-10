"""backend.api package

Create and configure the FastAPI `app` here and include the modular routers
implemented under `backend.api`.

This removes the previous dependency on importing `app` from `web_server.py`.
"""
from typing import List


def create_app():
	try:
		from fastapi import FastAPI
		from fastapi.middleware.cors import CORSMiddleware
		from contextlib import asynccontextmanager
		import threading
	except Exception:
		# fastapi isn't available in this environment; defer creation.
		return None

	# Lifespan manager: start blockchain listener thread on startup and close DB on shutdown.
	@asynccontextmanager
	async def lifespan(app):
		# Delay importing runtime pieces so importing this package stays lightweight.
		try:
			# web_server exposes run_blockchain_listener and client
			from web_server import run_blockchain_listener, client
		except Exception:
			run_blockchain_listener = None
			client = None

		listener_thread = None
		if run_blockchain_listener is not None:
			try:
				listener_thread = threading.Thread(target=run_blockchain_listener, daemon=True)
				listener_thread.start()
			except Exception:
				# If starting the listener fails, continue — status_messages will capture errors.
				pass

		try:
			yield
		finally:
			print("Shutting down...")
			if client is not None:
				try:
					client.close()
					print("MongoDB client closed.")
				except Exception:
					pass

	# Create FastAPI app with lifespan for startup/shutdown
	app = FastAPI(title="eth_bot API", lifespan=lifespan)

	# ---------------------------
	# CORS
	# ---------------------------
	app.add_middleware(
		CORSMiddleware,
		allow_origins=[
			"https://eth-tracker-front.onrender.com",
			"http://localhost:3000",
			"http://127.0.0.1:3000",
		],
		allow_credentials=False,
		allow_methods=["*"],
		allow_headers=["*"],
	)


	try:
		from . import routes as api_routes

		if getattr(api_routes, "router", None) is not None:
			app.include_router(api_routes.router)
	except Exception:
		# If routes can't be imported for any reason, keep app usable; raise later at runtime.
		pass

	return app


# Try to create app if fastapi is installed; otherwise leave as None.
app = create_app()

__all__: List[str] = ["app", "create_app"]
