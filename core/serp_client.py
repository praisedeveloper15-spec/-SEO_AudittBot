"""
Thin wrapper around the SerpApi.com search API.
Docs: https://serpapi.com/search-api

Free tier: 250 searches/month, no credit card required (serpapi.com/users/sign_up).
Supports google / bing / yahoo organic search.
Auth: single API key passed as a query param.
"""
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from config import SERPAPI_KEY

BASE_URL = "https://serpapi.com/search.json"

# maps our internal engine name -> SerpApi "engine" param
ENGINE_MAP = {
    "google": "google",
    "bing": "bing",
    "yahoo": "yahoo",
}


class SerpClientError(Exception):
    pass


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _get(params: dict):
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise SerpClientError(data["error"])
    return data


def check_rank(term: str, domain: str, engine: str = "google",
                device: str = "desktop", location_code: int = 2840,
                language_code: str = "en", depth: int = 100):
    """
    Returns (position, url) for the first organic result whose URL contains `domain`,
    or (None, None) if the domain isn't found in the results SerpApi returns.
    """
    if engine not in ENGINE_MAP:
        raise ValueError(f"Unsupported engine: {engine}")

    params = {
        "engine": ENGINE_MAP[engine],
        "q": term,
        "device": device,
        "hl": language_code,
        "api_key": SERPAPI_KEY,
    }

    data = _get(params)
    organic_results = data.get("organic_results", [])

    for item in organic_results:
        item_url = item.get("link", "") or ""
        if domain.lower().lstrip("www.") in item_url.lower():
            return item.get("position"), item_url

    return None, None
