#!/usr/bin/env python3
"""
indexnow.py: tell the search engines which pages changed (Program 8, Sprint 8.2, item 5).

IndexNow needs no account. The site serves a key file at its root whose name and text are the key
(this key is public by design: it only proves the host's owner placed the file), and after a
production build the changed URLs are POSTed to the shared endpoint. Bing, Yandex and the other
participants pass them on.

  python3 indexnow.py --prepare   at the end of the build: compare the sitemaps this build wrote
                                  with the LIVE ones (the previous deploy) and keep the changed
                                  URLs in out/indexnow-changed.json (never published)
  python3 indexnow.py --send      after the deploy is live (the Netlify plugin's onSuccess): POST them

CHANGED means a URL that is new in the sitemaps or whose <lastmod> moved. A URL with no lastmod
cannot be shown to have changed and is sent only when new. A failed fetch, a failed send or a
refusal is logged and never fails a build: the next build sends again.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = "gocheckmycrypto.com"
ORIGIN = "https://" + HOST
KEY = "a44f710d9349e5f84a1c0bbae18b03c5"
ENDPOINT = "https://api.indexnow.org/indexnow"
CHANGED = os.path.join(HERE, "out", "indexnow-changed.json")
SITEMAPS = ("sitemap-priority.xml", "sitemap-archive.xml")
CAP = 200               # URLs per submission; the endpoint takes 10,000, a news desk needs few


def key_file():
    return KEY + ".txt"


def _entries(xml):
    """{loc: lastmod or ''} from one urlset."""
    out = {}
    for m in re.finditer(r"<url>(.*?)</url>", xml or "", re.S):
        loc = re.search(r"<loc>(.*?)</loc>", m.group(1))
        lm = re.search(r"<lastmod>(.*?)</lastmod>", m.group(1))
        if loc:
            out[loc.group(1).strip()] = lm.group(1).strip() if lm else ""
    return out


def changed_urls(old_xmls, new_xmls):
    """URLs new in `new_xmls`, or whose lastmod differs from `old_xmls`', in the new order."""
    old, new = {}, {}
    for x in old_xmls:
        old.update(_entries(x))
    ordered = []
    for x in new_xmls:
        for loc, lm in _entries(x).items():
            new[loc] = lm
            ordered.append(loc)
    return [u for u in ordered if u not in old or (new[u] and new[u] != old[u])]


def payload(urls):
    return {"host": HOST, "key": KEY, "keyLocation": f"{ORIGIN}/{key_file()}", "urlList": list(urls)}


def send(urls, opener=None, endpoint=ENDPOINT):
    """POST the URLs; returns the one log line (also printed). Never raises."""
    urls = list(urls)[:CAP]
    if not urls:
        line = "indexnow: nothing changed, nothing sent"
        print(line)
        return line
    opener = opener or urllib.request.urlopen
    req = urllib.request.Request(endpoint, data=json.dumps(payload(urls)).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        r = opener(req, timeout=20)
        line = f"indexnow: sent {len(urls)} URL(s) to {endpoint}, response {getattr(r, 'status', '?')}"
    except urllib.error.HTTPError as e:                     # 4xx and 5xx carry a code worth logging
        line = f"indexnow: send failed, response {e.code} for {len(urls)} URL(s); the next build sends again"
    except Exception as e:                                  # noqa: BLE001
        line = f"indexnow: send failed ({type(e).__name__}: {str(e)[:80]}); the next build sends again"
    print(line)
    return line


def _live(name, opener=None):
    try:
        r = (opener or urllib.request.urlopen)(urllib.request.Request(f"{ORIGIN}/{name}",
                                               headers={"User-Agent": "gocheckmycrypto-indexnow"}), timeout=15)
        return r.read().decode("utf-8", "replace")
    except Exception:                                       # noqa: BLE001
        return None


def prepare(publish, opener=None):
    """Write the key file into the published tree and the changed list to out/. Called by the build."""
    with open(os.path.join(publish, key_file()), "w", encoding="utf-8") as fh:
        fh.write(KEY)
    if os.environ.get("CONTEXT", "") != "production":
        # a local build, a canary build or a preview never reaches for the network or tells an engine
        os.makedirs(os.path.dirname(CHANGED), exist_ok=True)
        json.dump({"urls": []}, open(CHANGED, "w", encoding="utf-8"))
        print(f"indexnow: not a production build; key file {key_file()} written, nothing kept to send")
        return []
    new = []
    for n in SITEMAPS:
        try:
            new.append(open(os.path.join(publish, n), encoding="utf-8").read())
        except OSError:
            pass
    old = [x for x in (_live(n, opener) for n in SITEMAPS) if x is not None]
    if len(old) < len(SITEMAPS):
        print("indexnow: the live sitemaps could not be read; sending nothing this build rather than everything")
        urls = []
    else:
        urls = changed_urls(old, new)
    os.makedirs(os.path.dirname(CHANGED), exist_ok=True)
    json.dump({"urls": urls}, open(CHANGED, "w", encoding="utf-8"))
    print(f"indexnow: key file {key_file()} written; {len(urls)} changed URL(s) kept for the post-deploy send")
    return urls


def main(argv):
    if "--send" in argv:
        # only a production deploy tells the engines; a branch or preview never does
        if os.environ.get("CONTEXT", "production") != "production":
            print("indexnow: not a production deploy, nothing sent")
            return 0
        try:
            urls = json.load(open(CHANGED, encoding="utf-8")).get("urls", [])
        except (OSError, ValueError):
            urls = []
        send(urls)
        return 0
    if "--prepare" in argv:
        prepare(os.path.join(HERE, "site", "publish"))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
