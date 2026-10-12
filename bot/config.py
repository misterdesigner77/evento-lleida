import os
import re
import config as c

BOT_TOKEN = os.environ["BOT_TOKEN"]  # sem token o bot não tem como rodar
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
API_TOKEN = os.getenv("API_TOKEN")

ADMINS = {int(a) for a in os.getenv("ADMIN_ID", "").split(",") if a.strip()}

TG_LIMIT = 4000
CODE_RE = re.compile(rf"^[{c.ALFABETO}]{{{c.TAMANHO}}}$", re.IGNORECASE)