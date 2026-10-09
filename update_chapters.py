#!/usr/bin/env python3
"""Generate spoiler-free RSS announcements from VIZ's Kagurabachi chapter list.

No credentials or external dependencies. The first run only establishes a baseline.
"""
from __future__ import annotations

import datetime as dt
import email.utils
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

VIZ_URL = "https://www.viz.com/shonenjump/chapters/kagurabachi"
READ_URL = "https://mangaplus.shueisha.co.jp/titles/700020"
STATE_FILE = Path("state.json")
FEED_FILE = Path("chapters.xml")
UTC = dt.timezone.utc
MONTHS = "January February March April May June July August September October November December".split()
DATE_PATTERN = r"(?:" + "|".join(MONTHS) + r")\s+\d{1,2},\s+20\d{2}"
CHAPTER_RE = re.compile(
    r"(?P<date>" + DATE_PATTERN + r")\s+Ch\.\s*(?P<chapter>\d+(?:\.\d+)?)\b",
    flags=re.I,
)


class StripHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip:
            self.skip -= 1

    def handle_data(self, text):
        if not self.skip:
            self.parts.append(text)


def read_chapters(html: str, now: dt.datetime) -> list[tuple[tuple[int, ...], str, dt.datetime]]:
    parser = StripHTML()
    parser.feed(html)
    text = re.sub(r"\s+", " ", " ".join(parser.parts))
    seen = {}
    for match in CHAPTER_RE.finditer(text):
        date = dt.datetime.strptime(match.group("date"), "%B %d, %Y").date()
        # Date in the public list plus the usual 15:00 UTC publication hour.
        # Not an authoritative API; live validation is required before role pings.
        released_at = dt.datetime.combine(date, dt.time(15, 0), UTC)
        if released_at > now:
            continue
        number = match.group("chapter")
        version = tuple(int(part) for part in number.split("."))
        seen[number] = version, number, released_at
    return sorted(seen.values(), key=lambda x: x[0])


def get_source() -> str:
    request = Request(
        VIZ_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; KagurabachiChapterFeed/1.0)",
                 "Accept": "text/html"},
    )
    with urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError(f"VIZ returned HTTP {response.status}")
        return response.read().decode("utf-8", errors="replace")


def xml_feed() -> tuple[ET.Element, ET.Element]:
    if FEED_FILE.exists():
        rss = ET.parse(FEED_FILE).getroot()
        channel = rss.find("channel")
        if rss.tag == "rss" and channel is not None:
            return rss, channel
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Kagurabachi - Official Chapter Releases"
    ET.SubElement(channel, "link").text = READ_URL
    ET.SubElement(channel, "description").text = "Spoiler-free chapter alerts using VIZ's published chapter list."
    ET.SubElement(channel, "language").text = "en-us"
    return rss, channel


def write_feed(rss: ET.Element) -> None:
    ET.indent(rss, space="  ")
    ET.ElementTree(rss).write(FEED_FILE, encoding="utf-8", xml_declaration=True)


def chapter_sort(raw: str) -> tuple[int, ...]:
    return tuple(int(x) for x in raw.split("."))


def run(html: str | None = None, now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(UTC)
    source = html if html is not None else get_source()
    chapters = read_chapters(source, now)
    if len(chapters) < 3:
        raise RuntimeError("VIZ chapter list could not be parsed; refusing to change state.")
    latest = chapters[-1]
    rss, channel = xml_feed()

    if not STATE_FILE.exists():
        STATE_FILE.write_text(json.dumps({"last_chapter": latest[1]}, indent=2) + "\n")
        write_feed(rss)
        return f"Initialized at existing chapter {latest[1]}; no old chapters announced."

    state = json.loads(STATE_FILE.read_text())
    previous = state["last_chapter"]
    if chapter_sort(latest[1]) <= chapter_sort(previous):
        return f"No new chapter; last baseline is {previous}."

    new_items = [c for c in chapters if c[0] > chapter_sort(previous)][-10:]
    known_guids = {item.findtext("guid") for item in channel.findall("item")}
    count = 0
    for _, number, released_at in new_items:
        guid = f"kagurabachi-chapter-{number}"
        if guid in known_guids:
            continue
        item = ET.Element("item")
        ET.SubElement(item, "title").text = f"Kagurabachi Chapter {number} is out!"
        ET.SubElement(item, "link").text = READ_URL
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = guid
        ET.SubElement(item, "pubDate").text = email.utils.format_datetime(released_at)
        ET.SubElement(item, "description").text = (
            f"Chapter {number} is listed as released. Read on MANGA Plus. No story spoilers."
        )
        channel.insert(list(channel).index(channel.find("language")) + 1, item)
        count += 1

    for old in channel.findall("item")[10:]:
        channel.remove(old)
    write_feed(rss)
    STATE_FILE.write_text(json.dumps({"last_chapter": latest[1]}, indent=2) + "\n")
    return f"Added {count} new chapters through {latest[1]}."


if __name__ == "__main__":
    try:
        print(run())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
