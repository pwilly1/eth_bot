import sys
import uvicorn
from backend.api import app


if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8001)
