import uvicorn
import os
from src import app

if __name__ == "__main__":
    env = os.environ
    uvicorn.run("src:app", host="0.0.0.0", port=80, reload=True)
