import requests
import time
import threading

_THREAD_LOCAL = threading.local()


def get_session():
    if not hasattr(_THREAD_LOCAL, "session"):
        _THREAD_LOCAL.session = requests.Session()
    return _THREAD_LOCAL.session

def safe_get(url, params=None, retries=5):
    for i in range(retries):
        try:
            r = get_session().get(url, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(2 ** i)
                continue
            r.raise_for_status()
            return r.json()
        except:
            if i == retries - 1:
                raise
            time.sleep(2 ** i)


def safe_get_text(url, params=None, retries=5):
    for i in range(retries):
        try:
            r = get_session().get(url, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(2 ** i)
                continue
            r.raise_for_status()
            return r.text
        except:
            if i == retries - 1:
                raise
            time.sleep(2 ** i)


def normalize_doi(doi):
    if not doi:
        return None
    return doi.lower().replace("https://doi.org/", "").strip()
