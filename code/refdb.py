"""
refdb.py — extract structured reference data from Wikipedia articles.

Returns a tidy DataFrame: one row per <ref>...</ref> tag (self-closing skipped).
Columns: page_id, page_title, ref_index, template, nested_templates,
         url, url_archivo, raw_string, text, + every non-empty template param.

Usage:
    from refdb import extract, extract_many
    df = extract(pageid=12345)
    df = extract(title="Buenos Aires")

Repository: https://github.com/silviaegt/wiki-latam-refs

Authorship note:
    This module was developed in collaboration with DeepSeek (DeepSeek-V3).
    The design, methodology, and scientific goals are original work by Silvia Gutiérrez. 
    The language model was used as a coding assistant, not as the
    originator of the research logic.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

import mwparserfromhell
import pandas as pd
import requests

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
DEFAULT_DOMAIN = "es.wikipedia.org"

# Generic user agent; replace with a contact URL for your own use.
# Wikimedia's API requires a descriptive User-Agent header:
# https://meta.wikimedia.org/wiki/User-Agent_policy
USER_AGENT = (
    "WikiLatamRefs/1.0 "
    "(https://github.com/silviaegt/wiki-latam-refs; research)"
)

URL_RE = re.compile(r'https?://[^\s\]\|<>"}\\}]+')
URL_LOOSE_RE = re.compile(r'\bwww\.[^\s\]\|<>"}\\}]+')

# Params that hold a URL by convention (highest priority)
URL_PARAM_NAMES = {"url", "enlace"}

# Other params that sometimes contain a URL (lower priority)
URL_LIKE_PARAMS = {
    "sitioweb", "website", "archiveurl", "archive-url",
    "urlarchivo", "urlmuerta", "urlcapítulo", "chapter-url",
}

# Params that carry an archived copy of the URL
ARCHIVE_PARAM_NAMES = {
    "urlarchivo", "archiveurl", "archive-url", "urlarchive",
    "urlarchivada", "urlmuerta", "enlacearchivo",
}

# Heuristic: template name contains one of these → it's an archive template
ARCHIVE_TEMPLATE_HINTS = ("wayback", "webcite", "archive", "enlace roto")

# Generic snapshot detector: <proxy>/.../<timestamp>/<original-url>
SNAPSHOT_RE = re.compile(
    r'^(?P<proxy>https?://[^/]+/)'
    r'(?:[^/]+/)*?'
    r'(?P<ts>\d{8,14}(?:[a-z_]+)?)'
    r'/(?P<original>https?://.+)$',
    re.IGNORECASE,
)

# Heuristic on the hostname: contains "archive" or "webcache"
ARCHIVE_HOST_RE = re.compile(
    r'(?:^|\.)(?:[^.]*archive[^.]*|webcache)\.[a-z]{2,}$',
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# 1. Fetch
# --------------------------------------------------------------------------- #
def fetch_page(title: str | None = None,
               pageid: int | None = None,
               domain: str = DEFAULT_DOMAIN) -> tuple[int, str, str]:
    """Return (page_id, page_title, wikitext). Follows redirects."""
    if title is None and pageid is None:
        raise ValueError("Provide either title or pageid.")

    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
    }
    if title is not None:
        params["titles"] = title
    else:
        params["pageids"] = str(pageid)

    r = requests.get(f"https://{domain}/w/api.php",
                     params=params,
                     headers={"User-Agent": USER_AGENT},
                     timeout=30)
    r.raise_for_status()
    data = r.json()

    pages = data.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        raise LookupError(f"Page not found: title={title!r} pageid={pageid!r}")

    page = pages[0]
    wikitext = page["revisions"][0]["slots"]["main"]["content"]
    return page["pageid"], page["title"], wikitext


# --------------------------------------------------------------------------- #
# 2. Iterate <ref> tags
# --------------------------------------------------------------------------- #
def iter_refs(wikitext: str):
    """Yield non-self-closing <ref> tags that have non-empty contents."""
    code = mwparserfromhell.parse(wikitext)
    for ref in code.filter_tags(matches=lambda n: n.tag == "ref"):
        if ref.self_closing:
            continue
        if not str(ref.contents).strip():
            continue
        yield ref


# --------------------------------------------------------------------------- #
# 3. Template helpers
# --------------------------------------------------------------------------- #
def _name(t) -> str:
    return str(t.name).strip().lower()


def _non_empty_params(t) -> dict[str, str]:
    out = {}
    for p in t.params:
        k = str(p.name).strip()
        v = str(p.value).strip()
        if v and v != "|":
            out[k] = v
    return out


def _has_url_param(t) -> bool:
    return any(k.lower() in URL_PARAM_NAMES for k in _non_empty_params(t))


def _score(t) -> tuple[int, int]:
    return (1 if _has_url_param(t) else 0, len(_non_empty_params(t)))


# --------------------------------------------------------------------------- #
# 4. URL extraction
# --------------------------------------------------------------------------- #
def _extract_url(value: str) -> str | None:
    """
    Find a URL in an arbitrary string.

    Hardened against template-param junk that leaks in:
      - leading/trailing whitespace
      - trailing '}}' from an unbalanced template
      - trailing '|' from a pipe-split
      - embedded newlines
      - trailing punctuation
    """
    if not value:
        return None
    s = str(value).replace("\n", " ").strip()
    # cut anything after the first '}}' or '|' — those aren't part of a URL
    s = s.split("}}")[0].split("|")[0].strip()
    if not s:
        return None
    m = URL_RE.search(s)
    if m:
        return m.group(0).rstrip(".,;:")
    m = URL_LOOSE_RE.search(s)
    if m:
        return "http://" + m.group(0).rstrip(".,;:")
    return None


def _host(url: str) -> str | None:
    if not url:
        return None
    try:
        h = urlparse(str(url).strip()).hostname
        return h.lower() if h else None
    except Exception:
        return None


def _looks_like_archive_host(url: str) -> bool:
    h = _host(url)
    return bool(h and ARCHIVE_HOST_RE.search(h))


def split_archive_url(url: str) -> tuple[str | None, str | None]:
    """(original, snapshot) if url is a snapshot; (url, None) otherwise."""
    if not url:
        return None, None
    m = SNAPSHOT_RE.match(url)
    if m and _looks_like_archive_host(m.group("proxy")):
        return m.group("original"), url
    return url, None


def _resolve_urls(ref, ordered_templates, main_template_name: str, raw: str):
    """Return dict with keys: url, url_archivo."""
    candidates: list[tuple[str, str]] = []
    for t in ordered_templates:
        for k, v in _non_empty_params(t).items():
            candidates.append((k.lower(), v))

    # 1. explicit archive param (urlarchivo=, archiveurl=, ...)
    archive_from_param = None
    for k, v in candidates:
        if k in ARCHIVE_PARAM_NAMES:
            u = _extract_url(v)
            if u:
                archive_from_param = u
                break

    # 2. main url param (or fallback cascade)
    main_url = None
    for k, v in candidates:
        if k in URL_PARAM_NAMES:
            main_url = _extract_url(v)
            if main_url:
                break
    if not main_url:
        for k, v in candidates:
            if k in URL_LIKE_PARAMS or "url" in k:
                main_url = _extract_url(v)
                if main_url:
                    break
    if not main_url:
        for k, v in candidates:
            main_url = _extract_url(v)
            if main_url:
                break
    if not main_url:
        exts = ref.contents.filter_external_links()
        if exts:
            main_url = str(exts[0].url).strip()
    if not main_url:
        main_url = _extract_url(raw)

    # 3. archive template without explicit urlarchivo → build snapshot from date
    tmpl = (main_template_name or "").lower()
    is_archive_template = any(h in tmpl for h in ARCHIVE_TEMPLATE_HINTS)
    if is_archive_template and main_url and not archive_from_param:
        for k, v in candidates:
            if k in {"date", "fecha", "timestamp", "fechaarchivo", "archive-date"}:
                m = re.search(r'\d{8,14}', v)
                if m:
                    archive_from_param = (
                        f"https://web.archive.org/web/{m.group(0)}/{main_url}"
                    )
                    break

    # 4. split if main_url IS a snapshot
    original, snapshot = split_archive_url(main_url) if main_url else (None, None)

    if snapshot:
        return {"url": original, "url_archivo": snapshot}
    return {"url": main_url, "url_archivo": archive_from_param}


# --------------------------------------------------------------------------- #
# 5. Parse a single ref
# --------------------------------------------------------------------------- #
def parse_ref(ref, page_id: int, page_title: str, ref_index: int) -> dict:
    raw = str(ref.contents).strip()
    text = ref.contents.strip_code().strip()

    record: dict = {
        "page_id":          page_id,
        "page_title":       page_title,
        "ref_index":        ref_index,
        "template":         "text",
        "nested_templates": None,
        "url":              None,
        "url_archivo":      None,
        "raw_string":       raw,
        "text":             text,
    }

    templates = ref.contents.filter_templates(recursive=True)

    if templates:
        main = max(templates, key=_score)
        record["template"] = _name(main)

        others = [_name(t) for t in templates if t is not main]
        others = list(dict.fromkeys(others))
        if others:
            record["nested_templates"] = "|".join(others)

        ordered = [t for t in templates if t is not main] + [main]
        for t in ordered:
            for k, v in _non_empty_params(t).items():
                record[k] = v

        record.update(_resolve_urls(ref, ordered, record["template"], raw))
    else:
        record.update(_resolve_urls(ref, [], "text", raw))

    return record


# --------------------------------------------------------------------------- #
# 6. Public API
# --------------------------------------------------------------------------- #
def extract(title: str | None = None,
            pageid: int | None = None,
            domain: str = DEFAULT_DOMAIN) -> pd.DataFrame:
    """Return a DataFrame of all non-empty <ref> tags from a Wikipedia page."""
    FRONT = ["page_id", "page_title", "ref_index",
             "template", "nested_templates",
             "url", "url_archivo",
             "raw_string", "text"]

    fetched = fetch_page(title=title, pageid=pageid, domain=domain)

    if fetched is None:
        return pd.DataFrame(columns=FRONT)

    pid, ptitle, wikitext = fetched

    records = [parse_ref(ref, pid, ptitle, i)
               for i, ref in enumerate(iter_refs(wikitext))]

    df = pd.DataFrame(records, columns=FRONT)

    cols = FRONT + [c for c in df.columns if c not in FRONT]
    return df[cols]


# --------------------------------------------------------------------------- #
# 7. Batch helper
# --------------------------------------------------------------------------- #
def extract_many(titles: list[str],
                 domain: str = DEFAULT_DOMAIN) -> pd.DataFrame:
    """Run extract() over many titles, skip failures, concat the results."""
    frames = []
    for t in titles:
        try:
            df = extract(title=t, domain=domain)
            frames.append(df)
            print(f"  OK  {t:<40} {len(df):>5} refs")
        except Exception as e:
            print(f"  !!  {t:<40} {type(e).__name__}: {e}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
