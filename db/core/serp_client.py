import requests
from requests.auth import HTTPBasicAuth
from tenacity import retry, stop_after_attempt, wait_exponential

from config import DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD

BASE_URL = "https://api.dataforseo.com/v3"

ENGINE_PATHS = {
    "google": "google/organic",
    "bing": "bing/organic",
    "yahoo": "yahoo/organic",
    "youtube": "youtube/organic",
}


class SerpClientError(Exception):
    pass


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _post(path: str, payload: list[dict]):
    resp = requests.post(
        f"{BASE_URL}/{path}/live/advanced",
        auth=HTTPBasicAuth(DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status_code") != 20000:
        raise SerpClientError(data.get("status_message", "Unknown DataForSEO error"))
    return data


def check_rank(term: str, domain: str, engine: str = "google",
                device: str = "desktop", location_code: int = 2840,
                language_code: str = "en", depth: int = 100):
    if engine not in ENGINE_PATHS:
        raise ValueError(f"Unsupported engine: {engine}")

    payload = [{
        "keyword": term,
        "location_code": location_code,
        "language_code": language_code,
        "device": device,
        "depth": depth,
    }]

    data = _post(ENGINE_PATHS[engine], payload)
    task = data["tasks"][0]
    result = task.get("result")
    if not result:
        return None, None

    items = result[0].get("items", [])
    for item in items:
        if item.get("type") != "organic":
            continue
        item_url = item.get("url", "") or ""
        if domain.lower().lstrip("www.") in item_url.lower():
            return item.get("rank_absolute"), item_url

    return None, None
