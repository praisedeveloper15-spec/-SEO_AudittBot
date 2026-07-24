import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import urllib.robotparser as robotparser

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SEOAudittBot/1.0; +https://t.me/SEO_AudittBot)"}


def audit_url(url: str) -> dict:
    issues = []
    metrics = {}

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException as e:
        return {"issues": [{"severity": "critical", "message": f"Could not fetch URL: {e}"}], "metrics": {}}

    metrics["status_code"] = resp.status_code
    if resp.status_code >= 400:
        issues.append({"severity": "critical", "message": f"Page returned HTTP {resp.status_code}"})

    soup = BeautifulSoup(resp.text, "lxml")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    metrics["title"] = title
    metrics["title_length"] = len(title)
    if not title:
        issues.append({"severity": "high", "message": "Missing <title> tag"})
    elif len(title) > 60:
        issues.append({"severity": "low", "message": f"Title is {len(title)} chars (recommended <= 60)"})

    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_desc_tag["content"].strip() if meta_desc_tag and meta_desc_tag.get("content") else ""
    metrics["meta_description"] = meta_desc
    metrics["meta_description_length"] = len(meta_desc)
    if not meta_desc:
        issues.append({"severity": "high", "message": "Missing meta description"})
    elif len(meta_desc) > 160:
        issues.append({"severity": "low", "message": f"Meta description is {len(meta_desc)} chars (recommended <= 160)"})

    h1_tags = soup.find_all("h1")
    metrics["h1_count"] = len(h1_tags)
    if len(h1_tags) == 0:
        issues.append({"severity": "high", "message": "No <h1> tag found"})
    elif len(h1_tags) > 1:
        issues.append({"severity": "medium", "message": f"Multiple <h1> tags found ({len(h1_tags)})"})

    canonical = soup.find("link", attrs={"rel": "canonical"})
    metrics["canonical"] = canonical["href"] if canonical and canonical.get("href") else None
    if not canonical:
        issues.append({"severity": "low", "message": "Missing canonical link tag"})

    images = soup.find_all("img")
    missing_alt = [img for img in images if not img.get("alt", "").strip()]
    metrics["image_count"] = len(images)
    metrics["images_missing_alt"] = len(missing_alt)
    if missing_alt:
        issues.append({"severity": "medium", "message": f"{len(missing_alt)} of {len(images)} images missing alt text"})

    body_text = soup.get_text(separator=" ", strip=True)
    word_count = len(body_text.split())
    metrics["word_count"] = word_count
    if word_count < 300:
        issues.append({"severity": "medium", "message": f"Thin content: only {word_count} words"})

    meta_robots = soup.find("meta", attrs={"name": "robots"})
    if meta_robots and "noindex" in meta_robots.get("content", "").lower():
        issues.append({"severity": "critical", "message": "Page has a noindex directive"})

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        if not rp.can_fetch("*", url):
            issues.append({"severity": "high", "message": "URL is disallowed by robots.txt"})
    except Exception:
        pass

    return {"issues": issues, "metrics": metrics}
