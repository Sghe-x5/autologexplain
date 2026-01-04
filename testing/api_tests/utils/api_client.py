import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")

class APIClient:
    def get(self, path, **kwargs):
        return requests.get(f"{BASE_URL}{path}", **kwargs)

    def post(self, path, **kwargs):
        return requests.post(f"{BASE_URL}{path}", **kwargs)
