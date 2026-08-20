#!/usr/bin/env python3
import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://paolo-de-marinis.github.io"
SM = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
XHTML = "{http://www.w3.org/1999/xhtml}"


class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical = None
        self.hreflang = {}
        self.robots = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href")
        if tag == "link" and attrs.get("rel") == "alternate" and attrs.get("hreflang"):
            self.hreflang[attrs["hreflang"]] = attrs.get("href")
        if tag == "meta" and attrs.get("name", "").lower() == "robots":
            self.robots = attrs.get("content", "").lower()


def page_path(url):
    assert url.startswith(ORIGIN + "/"), f"foreign URL: {url}"
    return ROOT / url.removeprefix(ORIGIN).lstrip("/") / "index.html"


def parse_html(data):
    parser = HeadParser()
    parser.feed(data.decode("utf-8") if isinstance(data, bytes) else data)
    return parser


def fetch(url):
    request = Request(url, headers={"User-Agent": "paolo-de-marinis-seo-validator/1.0"})
    with urlopen(request, timeout=20) as response:
        assert response.status == 200, f"{url}: HTTP {response.status}"
        assert response.url == url, f"{url}: redirects to {response.url}"
        return response.headers.get_content_type(), response.read()


def validate(live):
    robots_bytes = (ROOT / "robots.txt").read_bytes()
    assert not robots_bytes.startswith(b"\xef\xbb\xbf"), "robots.txt has a BOM"
    assert b"\r" not in robots_bytes, "robots.txt must use LF line endings"
    robots = robots_bytes.decode("utf-8")
    assert f"Sitemap: {ORIGIN}/sitemap.xml" in robots
    for agent in ("Googlebot", "Google-Extended"):
        group = robots.split(f"User-agent: {agent}\n", 1)[1].split("\n\n", 1)[0]
        assert "Allow: /" in group and "Disallow: /" not in group, f"{agent} is not allowed"

    sitemap_bytes = (ROOT / "sitemap.xml").read_bytes()
    assert not sitemap_bytes.startswith(b"\xef\xbb\xbf"), "sitemap.xml has a BOM"
    root = ET.fromstring(sitemap_bytes)
    assert root.tag == SM + "urlset"
    entries = {}
    for item in root.findall(SM + "url"):
        loc = item.findtext(SM + "loc")
        assert loc and loc not in entries, f"duplicate or missing loc: {loc}"
        alternatives = {link.get("hreflang"): link.get("href") for link in item.findall(XHTML + "link")}
        assert alternatives.get("en") and alternatives.get("it-IT") and alternatives.get("x-default")
        assert loc in alternatives.values(), f"{loc}: hreflang does not reference itself"
        entries[loc] = alternatives

    for loc, alternatives in entries.items():
        for alternate in set(alternatives.values()):
            assert alternate in entries, f"{loc}: alternate missing from sitemap: {alternate}"
            assert entries[alternate] == alternatives, f"{loc}: hreflang is not reciprocal"
        path = page_path(loc)
        assert path.is_file(), f"{loc}: missing local page {path.relative_to(ROOT)}"
        head = parse_html(path.read_text(encoding="utf-8"))
        assert head.canonical == loc, f"{loc}: canonical is {head.canonical}"
        assert "noindex" not in head.robots, f"{loc}: page is noindex"
        assert head.hreflang == {key: value for key, value in alternatives.items() if key != "x-default"}, f"{loc}: HTML hreflang differs from sitemap"

    if live:
        for name, expected_type, expected_bytes in (
            ("robots.txt", "text/plain", robots_bytes),
            ("sitemap.xml", "application/xml", sitemap_bytes),
        ):
            content_type, body = fetch(f"{ORIGIN}/{name}")
            assert content_type == expected_type, f"{name}: Content-Type {content_type}"
            assert body == expected_bytes, f"{name}: live content differs from the repository"
        for loc in entries:
            content_type, body = fetch(loc)
            assert content_type == "text/html", f"{loc}: Content-Type {content_type}"
            assert parse_html(body).canonical == loc, f"{loc}: live canonical mismatch"

    print(f"SEO validation passed: {len(entries)} canonical URLs" + (" (live)" if live else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    validate(parser.parse_args().live)
