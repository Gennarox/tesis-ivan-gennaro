import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

# Ciphers que IIS 8.5 soporta sin bug
IIS_CIPHERS = (
    "ECDHE-RSA-AES256-SHA384:"
    "ECDHE-RSA-AES128-SHA256:"
    "AES256-GCM-SHA384:"
    "AES128-GCM-SHA256"
)

class IIS8CompatibleAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(
            ciphers=IIS_CIPHERS,
            ssl_version=2  # TLSv1.2
        )
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)

session = requests.Session()
session.mount("https://www.stock.com.py", IIS8CompatibleAdapter())

resp = session.get("https://www.stock.com.py/default.aspx", timeout=10)
print(resp.status_code)
print(resp.text[:500])
