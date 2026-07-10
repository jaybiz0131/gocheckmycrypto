#!/usr/bin/env python3
"""
site_build.py: build the public Crypto Cronkite site from committed content.

Reproducible + lossless (the GoCheckMyPet lesson D2: everything the page needs is emitted
here from the templates, so rebuilding never strips the footer, disclaimer, or schema). Reads
site/content/*.json (one file per published item; _-prefixed files are ignored) and renders a
static deploy folder site/publish/: home, archive, one page per article, plus the static
editorial pages (about / how we work / standards) and a 404. No third-party dependency; no em
dashes; not-financial-advice baked into every article and the footer.

CONTENT FLOW
  A story is published only after a human approves it (publish.py, Stage 6). Promote approved
  payloads into committed site content with --ingest, then rebuild:

    python3 site_build.py --ingest      # out/published/*.json -> site/content/*.json, then build
    python3 site_build.py               # build site/publish/ from committed content

USAGE
  python3 site_build.py [--ingest]
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "site")
CONTENT = os.path.join(SITE, "content")
ASSETS = os.path.join(SITE, "assets")
PUBLISH = os.path.join(SITE, "publish")
PUBLISHED = os.path.join(HERE, "out", "published")

# Brand: Crypto Cronkite is the focal brand (the news desk, the masthead, the audience). This site
# stands on its own; the only thing it shares with the GoCheckMy family is the name/domain
# (gocheckmycrypto.com) plus the "A GoCheckMy site" footer tie. No family visual reskin, by design
# (see DEVIATIONS D-CRYPTO-2). Whale Watch is the on-chain tools sub-brand.
NAME = "Crypto Cronkite"
SLOGAN = "And that's the way it is."          # Walter Cronkite's sign-off; the brand tagline
DESK_LINE = "The honest voice in a shill-filled space."   # secondary descriptor
FAMILY = "GoCheckMyCrypto"                     # family/domain tie: gocheckmycrypto.com
FAMILY_HUB = "https://gocheckmy.com/"          # the GoCheckMy family hub (canonical footer link)
ORIGIN = "https://gocheckmycrypto.com"         # canonical origin for canonical/og:url/sitemap
OG_IMAGE = ORIGIN + "/og-image.png"            # 1200x630 social card, committed at site/assets/og-image.png
CF_ANALYTICS_TOKEN = "ee5216c8411a41d78c7c4f679406ef4b"  # Cloudflare Web Analytics site token; empty renders no beacon
DESC = ("Crypto Cronkite is an honest crypto news desk: AI does the reading, triage, and fact-checking; "
        "a human editor signs off on every story. Plus Whale Watch on-chain analytics. We report "
        "events, we never advise trades.")
NFA = ("Not financial advice. Crypto Cronkite reports events and explains what they may mean. "
       "It never tells you to buy or sell anything. Do your own research.")
YEAR = "2026"
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]

NAV = [("Home", "/index.html"), ("Whale Watch", "/flows.html"),
       ("Market Pulse", "/pulse.html"), ("Archive", "/archive.html"),
       ("How we work", "/method.html"), ("About", "/about.html"),
       ("Standards", "/standards.html")]


# ---- helpers -----------------------------------------------------------------

def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s or "story"


def fmt_date(iso):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(iso or ""))
    if not m:
        return str(iso or "")
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{MONTHS[mo]} {d}, {y}"


def fmt_usd(n):
    n = float(n or 0)
    sign = "-" if n < 0 else ""
    a = abs(n)
    if a >= 1e12:
        return f"{sign}${a/1e12:.2f}T"
    if a >= 1e9:
        return f"{sign}${a/1e9:.2f}B"
    if a >= 1e6:
        return f"{sign}${a/1e6:.1f}M"
    if a >= 1e3:
        return f"{sign}${a/1e3:.0f}K"
    return f"{sign}${a:.0f}"


def load_flows():
    path = os.path.join(SITE, "data", "flows.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return None


def load_pulse():
    path = os.path.join(SITE, "data", "pulse.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return None


def load_content():
    items = []
    if os.path.isdir(CONTENT):
        for fn in sorted(os.listdir(CONTENT)):
            if fn.startswith("_") or not fn.endswith(".json"):
                continue
            c = json.load(open(os.path.join(CONTENT, fn), encoding="utf-8"))
            c.setdefault("slug", slugify(c.get("title", "")))
            items.append(c)
    # newest first by date then id
    items.sort(key=lambda c: (c.get("date", ""), c.get("id", "")), reverse=True)
    return items


# ---- shared chrome -----------------------------------------------------------

def masthead(active, dateline):
    nav = "".join(
        f'<a href="{esc(href)}"{" class=active" if label == active else ""}>{esc(label)}</a>'
        for label, href in NAV)
    return f"""<div class="top-rule"></div>
<header class="masthead"><div class="wrap">
  <div class="mh-top">
    <span class="mh-family">{esc(FAMILY)}.com</span>
    <span class="mh-dateline">{esc(dateline)} &middot; Independent &middot; Human-approved</span>
  </div>
  <a class="mh-brand" href="/index.html" style="margin-top:8px">
    <img class="mh-mark" src="/assets/logo.svg" alt="">
    <span class="mh-word">{esc(NAME)}</span>
    <span class="mh-slogan">{esc(SLOGAN)}</span>
  </a>
</div></header>
<nav class="mh-nav"><div class="wrap">{nav}</div></nav>"""


def market_strip():
    """A live markets ticker. Client-side (the reader's browser fetches CoinGecko), so the build
    stays offline and reproducible. Clearly labelled and separate from the verified news: a price
    is live factual data, not a story that went through the human gate. Fails quietly if the API
    is unreachable (leaves the neutral placeholder)."""
    return """<section class="markets" id="markets" aria-label="Live crypto markets"><div class="wrap">
  <span class="lab">Markets &middot; live</span>
  <span class="tick" data-id="bitcoin"><span class="sym">BTC</span><span class="px">--</span><span class="chg"></span></span>
  <span class="tick" data-id="ethereum"><span class="sym">ETH</span><span class="px">--</span><span class="chg"></span></span>
  <span class="tick" data-id="solana"><span class="sym">SOL</span><span class="px">--</span><span class="chg"></span></span>
  <span class="tick" id="mcap"><span class="sym">Total cap</span><span class="px">--</span><span class="chg"></span></span>
  <span class="note">Market data, not news. Not financial advice.</span>
</div>
<script>
(function(){
  var CG="https://api.coingecko.com/api/v3";
  function money(n){ if(n>=1e12)return "$"+(n/1e12).toFixed(2)+"T"; if(n>=1e9)return "$"+(n/1e9).toFixed(1)+"B";
    if(n>=1000)return "$"+Math.round(n).toLocaleString(); return "$"+n.toFixed(2); }
  function chg(el,p){ if(p==null){return;} var s=(p>=0?"+":"")+p.toFixed(1)+"%";
    el.textContent=s; el.className="chg "+(p>=0?"up":"down"); }
  fetch(CG+"/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true")
    .then(function(r){return r.json();}).then(function(d){
      document.querySelectorAll(".markets .tick[data-id]").forEach(function(t){
        var k=t.getAttribute("data-id"), v=d[k]; if(!v)return;
        t.querySelector(".px").textContent=money(v.usd);
        chg(t.querySelector(".chg"), v.usd_24h_change);
      });
    }).catch(function(){});
  fetch(CG+"/global").then(function(r){return r.json();}).then(function(d){
      var g=d.data||{}, m=document.getElementById("mcap"); if(!m)return;
      if(g.total_market_cap&&g.total_market_cap.usd) m.querySelector(".px").textContent=money(g.total_market_cap.usd);
      chg(m.querySelector(".chg"), g.market_cap_change_percentage_24h_usd);
    }).catch(function(){});
})();
</script>
</section>"""


def newsletter():
    return f"""<section class="news"><div class="wrap">
  <h2>Get the brief</h2>
  <p>The day's real crypto news, de-shilled and fact-checked, with the honest take. No hype,
     no moon calls. One email, on a cadence we can actually keep.</p>
  <form name="newsletter" method="POST" data-netlify="true" netlify-honeypot="company" action="/thanks.html">
    <input type="hidden" name="form-name" value="newsletter">
    <input class="hp" type="text" name="company" tabindex="-1" autocomplete="off" aria-hidden="true">
    <input type="email" name="email" placeholder="you@email.com" required aria-label="Email address">
    <button type="submit">Subscribe</button>
  </form>
  <p class="fine">We do not sell your email. Unsubscribe anytime. Not financial advice.</p>
</div></section>"""


def trust_block():
    steps = [
        ("01", "Aggregate", "We pull the day's stories from many sources, weighting official and primary sources highest, and collapse the same event across outlets into one story."),
        ("02", "Editor AI ranks and de-shills", "An AI managing editor ranks the real news by genuine significance and strips paid promotion, price-hype, and affiliate bait, showing its work."),
        ("03", "A separate AI verifies", "An independent, adversarial AI fetches each cited source and checks the claim against it. VERIFIED, needs-review, or rejected. It never grades its own work."),
        ("04", "A human signs off", "The editor-in-chief reviews, overrides where judgment differs, adds the honest take, and approves. Nothing publishes without that sign-off."),
    ]
    cells = "".join(
        f'<div class="step"><span class="n">{n}</span><h4>{esc(t)}</h4><p>{esc(p)}</p></div>'
        for n, t, p in steps)
    return f"""<section class="trust"><div class="wrap">
  <div class="sec-head"><h2>How a story gets here</h2><span class="bar"></span>
    <a href="/method.html" style="font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase">Full method &rarr;</a></div>
  <div class="trust-grid">{cells}</div>
</div></section>"""


def footer():
    links = "".join(f'<a href="{esc(h)}">{esc(l)}</a>' for l, h in
                    [("About", "/about.html"), ("How we work", "/method.html"),
                     ("Standards & corrections", "/standards.html"), ("Archive", "/archive.html")])
    return f"""<footer class="site"><div class="wrap">
  <div class="frow">
    <div class="fbrand">{esc(NAME)}</div>
    <div class="flinks">{links}</div>
  </div>
  <p class="fnote"><b>{esc(NFA)}</b> Crypto Cronkite is an independent crypto news desk. Stories are
    machine-assembled and machine-verified, then reviewed and approved by a human editor before
    publication. Whale Watch shows on-chain market data, not news. Sources are linked on every story.
    &copy; {YEAR} {esc(NAME)} &middot; <a href="{FAMILY_HUB}">A GoCheckMy site</a>.</p>
</div></footer>"""


def shell(title, desc, active, body, dateline, body_class="", path="/", noindex=False):
    fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
             '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
             '<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">')
    url = ORIGIN + path
    robots = '<meta name="robots" content="noindex">\n' if noindex else f'<link rel="canonical" href="{esc(url)}">\n'
    beacon = ""
    if CF_ANALYTICS_TOKEN:
        beacon = ('\n<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
                  f'data-cf-beacon=\'{{"token": "{CF_ANALYTICS_TOKEN}"}}\'></script>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{esc(url)}">
<meta property="og:site_name" content="{esc(NAME)}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{OG_IMAGE}">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
{fonts}
<link rel="stylesheet" href="/assets/site.css">
</head>
<body class="{esc(body_class)}">
{masthead(active, dateline)}
{body}
{footer()}{beacon}
</body>
</html>"""


# ---- article ----------------------------------------------------------------

def render_body(body):
    out = []
    for b in body or []:
        if isinstance(b, dict) and "h2" in b:
            out.append(f"<h2>{esc(b['h2'])}</h2>")
        else:
            out.append(f"<p>{esc(b)}</p>")
    return "\n".join(out)


def verdict_badge(verdict):
    if verdict == "VERIFIED":
        return '<span class="badge verified">Verified</span>'
    if verdict in ("NEEDS-HUMAN-REVIEW", "REVIEW"):
        return '<span class="badge review">Editor reviewed</span>'
    return ""


def render_article(item):
    dateline = fmt_date(item.get("date"))
    badge = verdict_badge(item.get("verdict"))
    tag = f'<span class="tag">{esc(item.get("category","news"))}</span>' if item.get("category") else ""
    ribbon = ""
    if item.get("example"):
        ribbon = ('<div class="callout"><b>Example, not a real story.</b> This page shows the '
                  'format Crypto Cronkite publishes in. The content is illustrative only.</div>')
    key = ""
    if item.get("key_fact"):
        key = (f'<div class="keyfact"><span class="lab">The key fact</span>'
               f'<p>{esc(item["key_fact"])}</p></div>')
    take = ""
    if (item.get("human_take") or "").strip():
        take = (f'<div class="take"><span class="lab">The take</span>'
                f'<p>{esc(item["human_take"])}</p></div>')
    srcs = item.get("sources") or []
    src_html = ""
    if srcs:
        lis = "".join(
            f'<li><a href="{esc(s.get("url",""))}" rel="nofollow">{esc(s.get("title") or s.get("url"))}</a></li>'
            for s in srcs)
        src_html = f'<div class="sources"><h4>Sources</h4><ol>{lis}</ol></div>'
    author = esc(item.get("author", "The Crypto Cronkite desk"))
    body = f"""<main class="wrap narrow">
  <article class="article">
    <div class="ey">{badge}{tag}<span class="dateline">{esc(dateline)}</span></div>
    <h1>{esc(item.get("title"))}</h1>
    {f'<p class="dek">{esc(item["dek"])}</p>' if item.get("dek") else ""}
    <div class="byline">By {author} &nbsp;&middot;&nbsp; Reviewed and approved by a human editor</div>
    {ribbon}
    <div class="prose">{render_body(item.get("body"))}</div>
    {key}
    {take}
    {src_html}
    <p class="nfa">{esc(NFA)}</p>
  </article>
</main>"""
    title = f'{item.get("title")} - {NAME}'
    desc = item.get("dek") or (item.get("body", [""])[0] if item.get("body") else DESC)
    return shell(title, desc if isinstance(desc, str) else DESC, None, body, dateline.upper(),
                 path=f"/articles/{item['slug']}.html", noindex=bool(item.get("example")))


# ---- cards / index / archive -------------------------------------------------

def card(item):
    badge = verdict_badge(item.get("verdict"))
    tag = f'<span class="tag">{esc(item.get("category","news"))}</span>' if item.get("category") else ""
    href = f'/articles/{esc(item["slug"])}.html'
    summ = item.get("dek") or (item.get("body", [""])[0] if item.get("body") else "")
    if isinstance(summ, dict):
        summ = summ.get("h2", "")
    nsrc = len(item.get("sources") or [])
    return f"""<article class="card">
  <div class="row">{badge}{tag}</div>
  <h3><a href="{href}">{esc(item.get("title"))}</a></h3>
  <p class="summary">{esc(summ[:180])}</p>
  <div class="foot"><span class="dateline">{esc(fmt_date(item.get("date")))}</span>
    <span class="src">{nsrc} source{"s" if nsrc != 1 else ""}</span></div>
</article>"""


def desk_strip():
    # Home-only anchor-desk strip: the Crypto Cronkite portrait coin (the YouTube channel
    # face) beside the desk line. The masthead checkmark badge stays the site mark; this is
    # the anchor's face at the top of the front page. No link yet (channel tie post-launch).
    return f"""<section class="desk"><div class="wrap">
  <img class="desk-coin" src="/assets/cronkite-coin.png" alt="Crypto Cronkite" width="132" height="132">
  <div class="desk-copy">
    <span class="kicker">From the desk</span>
    <p>{esc(DESK_LINE)}</p>
  </div>
</div></section>"""


def render_index(items, dateline):
    live = [i for i in items if not i.get("example")]
    if live:
        lead = live[0]
        rest = live[1:]
        badge = verdict_badge(lead.get("verdict"))
        tag = f'<span class="tag">{esc(lead.get("category","news"))}</span>' if lead.get("category") else ""
        lead_html = f"""<section class="lead"><div class="wrap">
    <span class="kicker">Lead story</span>
    <h1><a href="/articles/{esc(lead["slug"])}.html" style="color:inherit">{esc(lead.get("title"))}</a></h1>
    {f'<p class="dek">{esc(lead["dek"])}</p>' if lead.get("dek") else ""}
    <div class="meta">{badge}{tag}<span class="dateline">{esc(fmt_date(lead.get("date")))}</span>
      <a href="/articles/{esc(lead["slug"])}.html">Read the story &rarr;</a></div>
  </div></section>"""
        grid = ""
        if rest:
            grid = (f'<section class="sec"><div class="wrap"><div class="sec-head" id="latest">'
                    f'<h2>More from the desk</h2><span class="bar"></span></div>'
                    f'<div class="grid">{"".join(card(i) for i in rest)}</div></div></section>')
    else:
        lead_html = f"""<section class="lead"><div class="wrap">
    <span class="kicker">The desk is live</span>
    <h1>Honest crypto news, on a cadence we can keep.</h1>
    <p class="dek">{esc(DESK_LINE)} The first published brief lands here. In the meantime, read how
       the desk works and why you can trust the byline.</p>
    <div class="meta"><a href="/method.html">How we work &rarr;</a>
      <a href="/about.html">Why this exists &rarr;</a></div>
  </div></section>"""
        grid = ('<section class="sec"><div class="wrap"><div class="empty">'
                '<span class="k">No brief published yet</span>'
                '<p style="margin:.6em 0 0">Every story here will have been ranked by an AI editor, '
                'checked against its sources by an independent AI verifier, and approved by a human. '
                'That gate is the whole point, so we would rather publish nothing than publish junk.</p>'
                '</div></div></section>')
    body = market_strip() + desk_strip() + lead_html + trust_block() + flow_teaser() + grid + newsletter()
    return shell(f"{NAME} - {SLOGAN}", DESC, "Home", body, dateline, path="/")


def flow_teaser():
    flows = load_flows()
    if not flows or not flows.get("by_asset"):
        summ = "Track where whales are moving large amounts on net: onto exchanges or off into self-custody."
    else:
        v = flows.get("volatile", {})
        s = flows.get("stablecoins", {})
        pre = "Example: " if flows.get("example") else ""
        summ = (f"{pre}Volatile whales net {fmt_usd(v.get('net_usd',0))} {v.get('direction','')} in "
                f"{flows.get('window_hours',24)}h; {fmt_usd(s.get('net_buying_power_usd',0))} "
                f"stablecoin buying power arriving.")
    return (f'<section class="sec"><div class="wrap">'
            f'<a class="flow-teaser" href="/flows.html">'
            f'<div><div class="t">Whale Watch &middot; follow the money</div>'
            f'<div class="d">{esc(summ)}</div></div>'
            f'<span style="font-family:var(--mono);font-size:11px;letter-spacing:.06em;'
            f'text-transform:uppercase;white-space:nowrap">Open the board &rarr;</span></a>'
            f'</div></section>')


def render_archive(items, dateline):
    live = [i for i in items if not i.get("example")]
    if live:
        rows = "".join(card(i) for i in live)
        inner = f'<div class="grid">{rows}</div>'
    else:
        inner = ('<div class="empty"><span class="k">Archive is empty</span>'
                 '<p style="margin:.6em 0 0">No stories have been approved and published yet.</p></div>')
    body = f"""<main class="wrap"><section class="sec">
    <div class="sec-head"><h2>Archive</h2><span class="bar"></span></div>
    {inner}
  </section></main>"""
    return shell(f"Archive - {NAME}", "Every published Crypto Cronkite story.", "Archive", body, dateline,
                 path="/archive.html")


# ---- static editorial pages --------------------------------------------------

def render_method(items, dateline):
    example = next((i for i in items if i.get("example")), None)
    ex_html = ""
    if example:
        ex_html = (f'<h2>What a finished story looks like</h2>'
                   f'<p>Here is the format, using an illustrative example (not a real story):</p>'
                   f'<div style="margin:18px 0">{card(example)}</div>'
                   f'<p><a href="/articles/{esc(example["slug"])}.html">Open the example story &rarr;</a></p>')
    body = f"""<main class="wrap narrow"><section class="page">
  <span class="kicker">Method</span>
  <h1>How a story gets to you</h1>
  <p class="lede">Automation removes the grind. It does not remove the judgment. Here is exactly
     what happens between a raw feed and a published story, and where the human sits.</p>

  <h2>1. Aggregate the day</h2>
  <p>On a schedule, the desk pulls crypto news from many sources at once: official and primary
     sources first (regulators, exchange and protocol notices), then established outlets. The same
     event reported by ten outlets is collapsed into one story so nothing is double-counted, and a
     deterministic first pass flags the obvious paid-promotion tells before any AI sees it.</p>

  <h2>2. An AI managing editor ranks and de-shills</h2>
  <p>An AI editor ranks the real news by genuine market and ecosystem significance, and strips the
     shill: price-prediction hype, affiliate listicles, self-issued press releases dressed as news,
     and moon-and-pump language. It shows its work, listing why each story made the cut and why
     others were cut, so the human can audit the call.</p>

  <h2>3. A separate AI verifies the editor</h2>
  <p>A second, independent AI, with an adversarial prompt, audits those picks before anything is
     drafted. It fetches each cited source and checks whether the source actually says what the
     story claims. It flags anything single-source, unconfirmed, or implausible, and stamps each
     story VERIFIED, needs-human-review, or rejected. The builder never verifies its own work, so
     the editor and the verifier are deliberately two different passes. When they disagree, that
     disagreement is surfaced to the human as a signal.</p>

  <h2>4. A human editor-in-chief signs off</h2>
  <p>Everything lands in a review queue. A human reads it, overrides the machine where judgment
     differs, kills stories, promotes ones it missed, and adds the honest take, the thing only a
     person can provide. Only what the human approves is published. That gate is not optional, and
     it is never removed to publish faster.</p>

  <div class="callout"><b>Why two AIs, not one.</b> A single model asked to both rank and
    self-check tends to rubber-stamp its own work. An independent pass, told to find what is wrong,
    catches what the first pass missed. It is the same discipline a real newsroom uses: the reporter
    does not fact-check their own copy.</div>

  {ex_html}

  <h2>What we will not do</h2>
  <ul>
    <li>We will not publish anything unverified or unapproved. If a stage fails, we publish nothing.</li>
    <li>We will not tell you to buy or sell. We report events and explain what they may mean.</li>
    <li>We will not run paid coverage as news. Sponsored items are the thing we are built to strip out.</li>
  </ul>
  <p class="nfa">{esc(NFA)}</p>
</section></main>"""
    return shell(f"How we work - {NAME}", "How Crypto Cronkite ranks, verifies, and approves every story.",
                 "How we work", body, dateline, path="/method.html")


def render_about(dateline):
    body = f"""<main class="wrap narrow"><section class="page">
  <span class="kicker">About</span>
  <h1>Why Crypto Cronkite exists</h1>
  <p class="lede">Crypto media is drowning in shilling. The scarce thing is an honest voice. That
     is the entire product.</p>

  <p>Most crypto "news" is paid promotion wearing a press badge: price predictions with nothing
     behind them, "partnerships" that are really self-issued press releases, and listicles of coins
     to buy that are affiliate bait. It is exhausting, and it is how people get hurt.</p>

  <p>Crypto Cronkite is built on one idea: report the real news, strip the shill, and never tell you
     what to do with your money. The name is a promise. Walter Cronkite was trusted because he was
     straight with people. That is the register we hold ourselves to, right down to the sign-off:
     and that's the way it is.</p>

  <p>Alongside the news, <b>Whale Watch</b> follows the money on-chain, the large exchange flows most
     coverage ignores. It is market data, clearly labelled, never dressed up as news.</p>

  <h2>The machine does the grind. A human owns the judgment.</h2>
  <p>An AI newsroom does the reading, the triage, the fact-checking, and the first draft, every day,
     without getting tired. But the machine is the staff, not the editor. A human editor-in-chief
     reviews every story, overrides the machine where judgment differs, adds the honest take, and
     approves what publishes. Nothing goes out as reporting or as a take without that sign-off. If
     even that sustainable human step ever slips, we drop the cadence before we drop the standard.</p>

  <h2>Our bias</h2>
  <p>We are biased toward the reader and against the shill. We weight official and primary sources
     most, we link every source, and we would rather publish nothing on a given day than publish
     something we cannot stand behind.</p>

  <h2>What we are not</h2>
  <p>We are not your financial advisor, and this is not investment advice. We report what happened
     and, carefully, what it may mean. What you do with that is yours.</p>

  <div class="callout"><b>Read next:</b> <a href="/method.html">How a story gets to you</a>, the
    step-by-step of how we rank, verify, and approve. Or <a href="/standards.html">our standards and
    corrections policy</a>.</div>
  <p class="nfa">{esc(NFA)}</p>
</section></main>"""
    return shell(f"About - {NAME}", "Why Crypto Cronkite exists: an honest crypto news desk plus on-chain analytics.",
                 "About", body, dateline, path="/about.html")


def render_standards(dateline):
    body = f"""<main class="wrap narrow"><section class="page">
  <span class="kicker">Standards</span>
  <h1>Standards and corrections</h1>
  <p class="lede">What you can hold us to.</p>

  <h2>Sourcing</h2>
  <p>Every story links its sources. We weight official and primary sources (regulators, exchange and
     protocol notices) most heavily. A claim carried by a single low-credibility source is marked as
     unverified or is not published.</p>

  <h2>Verification</h2>
  <p>Before a story is drafted, an independent verification pass checks each claim against its cited
     source. Stories that cannot be verified are either marked clearly for the reader or held back.
     We would rather be slow than wrong.</p>

  <h2>The human gate</h2>
  <p>No story is published automatically. A human editor approves every story, and adds any opinion
     or analysis in the byline. The AI never writes a "take" in a human's voice.</p>

  <h2>Not financial advice</h2>
  <p>We report events and explain what they may mean. We never advise buying or selling any asset.
     Nothing on this site is financial, investment, legal, or tax advice.</p>

  <h2>Corrections</h2>
  <p>When we get something wrong, we fix it and say so on the story. If you spot an error, tell us and
     we will check it against the source. A correction is a feature of an honest desk, not a failure.</p>

  <h2>AI disclosure</h2>
  <p>Stories on this site are assembled and fact-checked with AI assistance and then reviewed and
     approved by a human editor before publication. We think transparency about that process is part
     of being trustworthy, which is why this page exists.</p>
  <p class="nfa">{esc(NFA)}</p>
</section></main>"""
    return shell(f"Standards - {NAME}", "Crypto Cronkite standards, verification, and corrections policy.",
                 "Standards", body, dateline, path="/standards.html")


def flows_chart_svg(by_asset):
    """Diverging horizontal bar chart of net whale exchange flow per volatile asset. Inline SVG,
    offline, theme-aware (fills use the site's CSS variables). Polarity is encoded three ways so
    it never relies on red/green alone: side of the zero line, the sign in the label, and color.
    Left/red = net onto exchanges (sell pressure); right/green = net off exchanges (accumulation)."""
    if not by_asset:
        return '<div class="empty"><span class="k">No exchange-relevant whale moves in window</span></div>'
    W, cx, half = 720, 360, 250
    row_h, bar_h = 46, 20
    top = 44
    H = top + len(by_asset) * row_h + 16
    max_abs = max((abs(a.get("net_usd", 0)) for a in by_asset), default=1) or 1
    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
             f'aria-label="Net whale exchange flow by asset" style="max-width:100%;height:auto">']
    # axis labels + zero line
    parts.append(f'<text x="{cx-12}" y="20" text-anchor="end" class="ax">&#8592; onto exchanges (sell pressure)</text>')
    parts.append(f'<text x="{cx+12}" y="20" text-anchor="start" class="ax">off exchanges (accumulation) &#8594;</text>')
    parts.append(f'<line x1="{cx}" y1="30" x2="{cx}" y2="{H-8}" class="zero"/>')
    for i, a in enumerate(by_asset):
        y = top + i * row_h
        net = a.get("net_usd", 0)
        length = (abs(net) / max_abs) * half
        cy = y + row_h / 2
        by = cy - bar_h / 2
        parts.append(f'<text x="8" y="{cy+5:.0f}" class="sym">{esc(a.get("symbol",""))}</text>')
        if net < 0:  # onto exchanges, extend left, red
            parts.append(f'<rect x="{cx-length:.1f}" y="{by:.0f}" width="{length:.1f}" height="{bar_h}" '
                         f'rx="4" fill="var(--rule)"/>')
            parts.append(f'<text x="{cx-length-8:.1f}" y="{cy+5:.0f}" text-anchor="end" class="val">'
                         f'{esc(fmt_usd(net))}</text>')
        else:  # off exchanges, extend right, green
            parts.append(f'<rect x="{cx:.1f}" y="{by:.0f}" width="{length:.1f}" height="{bar_h}" '
                         f'rx="4" fill="var(--verified-fg)"/>')
            parts.append(f'<text x="{cx+length+8:.1f}" y="{cy+5:.0f}" text-anchor="start" class="val">'
                         f'+{esc(fmt_usd(net))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def ww_hero():
    return ('<section class="ww-hero"><div class="ww-heroinner">'
            '<img src="/assets/whale-watch-logo.jpg" alt="GoCheckMyCrypto Whale Watch: market pulse, on-chain insights">'
            '</div></section>')


def render_flows(flows, dateline):
    if not flows or not flows.get("by_asset") and not (flows or {}).get("top_inflows"):
        body = ww_hero() + """<main class="wrap"><section class="page">
  <span class="kicker">Follow the money</span>
  <h1>Where the whales are moving</h1>
  <p class="lede">This board tracks where whales are moving large amounts of crypto: onto
     exchanges (which can precede selling) or off exchanges into self-custody (accumulation).</p>
  <div class="empty"><span class="k">No board yet</span>
    <p style="margin:.6em 0 0">The board refreshes from Whale Alert's public data at each site
    build. Preview it locally with <code>python3 whale_flows.py --fixture
    fixtures/whale_sample.json</code>.</p></div>
</section></main>"""
        return shell(f"Whale Watch - {NAME}", "Follow the money: whale exchange flows.",
                     "Whale Watch", body, dateline, body_class="ww-dark", path="/flows.html")

    v = flows.get("volatile", {})
    s = flows.get("stablecoins", {})
    net = v.get("net_usd", 0)
    dir_word = v.get("direction", "")
    dir_cls = "up" if net >= 0 else "down"
    ribbon = ""
    if flows.get("example"):
        ribbon = ('<div class="callout"><b>Example board.</b> These are illustrative figures from '
                  'sample data, shown so you can see the format. Live flows arrive with the next site build.</div>')
    moves = flows.get("top_inflows", [])
    move_rows = "".join(
        f'<tr><td class="sym2">{esc(m.get("symbol",""))}{" &middot; stable" if m.get("stable") else ""}</td>'
        f'<td class="num">{esc(fmt_usd(m.get("usd",0)))}</td>'
        f'<td>&rarr; {esc(m.get("to","unknown exchange"))}</td>'
        f'<td class="mut">from {esc(m.get("from","unknown wallet"))}</td></tr>'
        for m in moves)
    win = flows.get("window_hours", 24)
    body = ww_hero() + f"""<main class="wrap"><section class="page">
  <span class="kicker">Follow the money</span>
  <h1>Where the whales are moving</h1>
  <p class="lede">Not a scrolling feed of every transfer, the aggregate. Where are whales moving
     large amounts on net over the last {win} hours: onto exchanges (which can precede selling)
     or off into self-custody (accumulation)?</p>
  {ribbon}

  <div class="stats">
    <div class="stat">
      <span class="lab">Volatile assets, net</span>
      <span class="big {dir_cls}">{esc(fmt_usd(net))}</span>
      <span class="sub">net {esc(dir_word)} ({win}h)</span>
    </div>
    <div class="stat">
      <span class="lab">Stablecoin buying power arriving</span>
      <span class="big">{esc(fmt_usd(s.get("net_buying_power_usd",0)))}</span>
      <span class="sub">net stablecoins onto exchanges ({win}h)</span>
    </div>
  </div>

  <div class="sec-head" style="margin-top:26px"><h2>Net exchange flow by asset</h2><span class="bar"></span></div>
  <div class="chartcard">{flows_chart_svg(flows.get("by_asset", []))}</div>

  {f'''<div class="sec-head" style="margin-top:26px"><h2>The 13-week trend</h2><span class="bar"></span></div>
  <div class="chartcard">{history_bars_svg(flows.get("history"))}</div>
  <p class="pc-note" style="margin-top:8px">Weekly net exchange flow for volatile assets.
  Bars above the line are net withdrawals (accumulation); bars below are net deposits
  (potential sell pressure). Hover a bar for the week's numbers.</p>''' if flows.get("history") else ""}

  <div class="sec-head" style="margin-top:26px"><h2>Biggest moves onto exchanges</h2><span class="bar"></span></div>
  <div class="movetable"><table><tbody>{move_rows or '<tr><td class=mut>None in window.</td></tr>'}</tbody></table></div>

  <div class="sec-head" style="margin-top:30px"><h2>Whale watching 101</h2><span class="bar"></span></div>
  <div class="learn-grid">
    <div class="learn"><span class="lab sell">Onto exchanges</span>
      <p>To sell a large amount of crypto, a whale usually has to move it onto an exchange first.
      So when BTC or ETH flows heavily <b>onto</b> exchanges on net, it can mean big holders are
      getting into position to sell. That is the sell-pressure side of the chart.</p></div>
    <div class="learn"><span class="lab buy">Off exchanges</span>
      <p>Coins withdrawn from an exchange usually head to self-custody: wallets the holder
      controls directly, often cold storage. Money tends to go there to sit, so net
      <b>outflow</b> historically reads as accumulation. That is the other side.</p></div>
    <div class="learn"><span class="lab">Stablecoins flip the logic</span>
      <p>Stablecoins like USDT and USDC are crypto's dry powder. When they flood <b>onto</b>
      exchanges, buyers may be staging money for purchases; when they leave, that buying power
      is stepping out of the arena. That is why we score them separately from volatile assets.</p></div>
    <div class="learn"><span class="lab">What it cannot tell you</span>
      <p>Whales move money for many reasons: custody rotations, transfers between their own
      wallets, over-the-counter deals. Only moves large enough for
      <a href="https://whale-alert.io/" rel="nofollow">Whale Alert</a> to post publicly (roughly
      $50M and up) appear here, and exchanges are identified by name. Treat this board as
      context for the news above it, never as a trade signal on its own.</p></div>
  </div>
  <p class="nfa">{esc(flows.get("note",""))} {esc(NFA)}</p>
</section></main>"""
    return shell(f"Whale Watch - {NAME}", "Follow the money: net whale exchange flows by asset.",
                 "Whale Watch", body, dateline, body_class="ww-dark", path="/flows.html")


# ---- market pulse -------------------------------------------------------------

def spark_svg(values, w=230, h=44, cls="spark"):
    """Tiny inline sparkline; server-rendered, no JS."""
    vals = [float(v) for v in (values or []) if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    pts = []
    for i, v in enumerate(vals):
        x = 3 + i * (w - 6) / (len(vals) - 1)
        y = 3 + (h - 6) * (1 - (v - lo) / rng)
        pts.append(f"{x:.1f},{y:.1f}")
    last = pts[-1].split(",")
    return (f'<svg class="{cls}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
            f'preserveAspectRatio="none" role="img" aria-hidden="true">'
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linejoin="round"/>'
            f'<circle cx="{last[0]}" cy="{last[1]}" r="2.6" fill="currentColor"/></svg>')


FNG_BANDS = [(0, 25, "#C0392B", "Extreme fear"), (25, 45, "#D9822B", "Fear"),
             (45, 55, "#9AA0A6", "Neutral"), (55, 75, "#6FA26B", "Greed"),
             (75, 100, "#2E7D4F", "Extreme greed")]


def fng_gauge_svg(value):
    """Semicircular sentiment gauge, 0 (extreme fear) to 100 (extreme greed)."""
    import math
    cx, cy, r = 130, 122, 96

    def pt(v, radius):
        theta = math.pi * (1 - v / 100.0)
        return cx + radius * math.cos(theta), cy - radius * math.sin(theta)

    parts = [f'<svg class="gauge" viewBox="0 0 260 150" xmlns="http://www.w3.org/2000/svg" '
             f'role="img" aria-label="Fear and greed gauge reading {value}">']
    for a, b, color, _ in FNG_BANDS:
        x0, y0 = pt(a + 0.6, r)
        x1, y1 = pt(b - 0.6, r)
        parts.append(f'<path d="M {x0:.1f} {y0:.1f} A {r} {r} 0 0 1 {x1:.1f} {y1:.1f}" '
                     f'fill="none" stroke="{color}" stroke-width="15" stroke-linecap="butt"/>')
    nx, ny = pt(max(2, min(98, value)), r - 22)
    parts.append(f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" '
                 f'stroke="currentColor" stroke-width="3" stroke-linecap="round"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="5.5" fill="currentColor"/>')
    parts.append(f'<text x="{cx}" y="{cy - 26}" text-anchor="middle" class="gauge-num">{value}</text>')
    parts.append("</svg>")
    return "".join(parts)


def history_bars_svg(history):
    """13-week net-flow bar chart for the Whale Watch page. Green up = net off exchanges."""
    if not history:
        return ""
    w, h = 660, 190
    mid = h / 2 - 8
    max_abs = max((abs(x.get("net_usd", 0)) for x in history), default=0) or 1
    n = len(history)
    slot = (w - 30) / n
    bw = min(34, slot * 0.62)
    parts = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" '
             f'aria-label="Weekly net exchange flow, last {n} weeks">']
    parts.append(f'<line x1="16" y1="{mid}" x2="{w-14}" y2="{mid}" stroke="var(--line)" stroke-width="1"/>')
    for i, wk in enumerate(history):
        net = wk.get("net_usd", 0)
        x = 22 + i * slot + (slot - bw) / 2
        bar = (abs(net) / max_abs) * (mid - 26)
        color = "var(--verified-fg)" if net >= 0 else "var(--rule)"
        y = mid - bar if net >= 0 else mid
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(bar, 1):.1f}" '
                     f'rx="3" fill="{color}"><title>week ending {esc(wk.get("week_ending",""))}: '
                     f'{esc(fmt_usd(net))} net, {wk.get("moves", 0)} moves</title></rect>')
        if i % 2 == 0:
            parts.append(f'<text x="{x + bw/2:.1f}" y="{h - 6}" text-anchor="middle" '
                         f'class="axis">{esc(wk.get("week_ending", ""))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _chip(text, cls=""):
    return f'<span class="chip {cls}">{esc(text)}</span>'


def _posture_card(a):
    rsi = a.get("rsi14")
    if rsi is None:
        rsi_chip = ""
    elif rsi >= 70:
        rsi_chip = _chip(f"RSI {rsi:.0f} hot", "chip-down")
    elif rsi <= 30:
        rsi_chip = _chip(f"RSI {rsi:.0f} cold", "chip-cool")
    else:
        rsi_chip = _chip(f"RSI {rsi:.0f} neutral")
    mom = (_chip("Momentum building", "chip-up") if a.get("macd_above_signal")
           else _chip("Momentum fading", "chip-down"))
    trend = (_chip("Above 200-day", "chip-up") if a.get("above_sma200")
             else _chip("Below 200-day", "chip-down"))
    cross = (_chip("Golden cross", "chip-up") if a.get("golden_cross")
             else _chip("Death cross", "chip-down"))
    return f"""<div class="pulse-card">
  <div class="pc-head"><span class="pc-sym">{esc(a.get("symbol",""))}</span>
    <span class="pc-price">${a.get("price", 0):,.0f}</span></div>
  <div class="pc-spark">{spark_svg(a.get("spark"))}</div>
  <div class="pc-chips">{rsi_chip}{mom}{trend}{cross}
    {_chip(f'{a.get("pct_from_high_12m", 0):+.0f}% vs 12-mo high')}
    {_chip(f'volatility {a.get("vol30_pct", 0):.0f}%/yr')}</div>
</div>"""


def render_pulse(pulse, dateline):
    desc = ("Market Pulse: crowd sentiment, price posture (RSI, MACD, moving averages), "
            "stablecoin dry powder, and Bitcoin network vitals, with plain-language "
            "explanations. Market data, not advice.")
    if not pulse:
        body = """<main class="wrap narrow"><section class="page">
  <span class="kicker">Market data desk</span>
  <h1>Market Pulse</h1>
  <p class="lede">Sentiment, price posture, and dry powder, explained honestly.</p>
  <div class="empty"><span class="k">No data yet</span>
    <p style="margin:.6em 0 0">The pulse refreshes from free public data at each site build.
    Generate it locally with <code>python3 market_pulse.py</code>.</p></div>
</section></main>"""
        return shell(f"Market Pulse - {NAME}", desc, "Market Pulse", body, dateline, path="/pulse.html")

    fng = pulse.get("fng") or {}
    assets = pulse.get("assets") or []
    stables = pulse.get("stables") or {}
    network = pulse.get("network") or {}

    fng_html = ""
    if fng:
        label = fng.get("label", "")
        band_color = next((c for a, b, c, _ in FNG_BANDS if a <= fng.get("value", 50) < b or
                           (b == 100 and fng.get("value") == 100)), "#9AA0A6")
        fng_html = f"""<div class="sec-head" style="margin-top:8px"><h2>Crowd sentiment</h2><span class="bar"></span></div>
  <div class="pulse-grid2">
    <div class="pulse-card center">{fng_gauge_svg(fng.get("value", 50))}
      <div class="gauge-label" style="color:{band_color}">{esc(label)}</div>
      <p class="pc-note">Fear &amp; Greed Index, 0 to 100</p></div>
    <div class="pulse-card"><span class="lab">Last 90 days</span>
      <div class="pc-spark tall">{spark_svg(fng.get("history"), w=300, h=84)}</div>
      <p class="pc-note">The index blends volatility, volume, social chatter, and Bitcoin
      dominance into one crowd-mood number. It measures emotion, not value.</p></div>
  </div>"""

    assets_html = ""
    if assets:
        cards = "".join(_posture_card(a) for a in assets)
        assets_html = f"""<div class="sec-head" style="margin-top:26px"><h2>Price posture</h2><span class="bar"></span></div>
  <div class="pulse-grid3">{cards}</div>
  <p class="pc-note" style="margin-top:8px">Standard formulas on daily closes (RSI-14,
  MACD 12/26/9, 50- and 200-day averages, 30-day realized volatility). The 90-day price line
  is drawn behind each reading. What these mean is explained below.</p>"""

    stables_html = ""
    if stables:
        chg = stables.get("change_30d_pct", 0)
        chg_chip = _chip(f"{chg:+.1f}% in 30 days", "chip-up" if chg >= 0 else "chip-down")
        stables_html = f"""<div class="sec-head" style="margin-top:26px"><h2>Stablecoin dry powder</h2><span class="bar"></span></div>
  <div class="pulse-grid2">
    <div class="pulse-card"><span class="lab">Total USD-pegged float</span>
      <span class="pc-big">{esc(fmt_usd(stables.get("total_usd", 0)))}</span>
      <div class="pc-chips">{chg_chip}</div>
      <p class="pc-note">All dollars parked in stablecoins across chains, per DefiLlama.</p></div>
    <div class="pulse-card"><span class="lab">One-year trend</span>
      <div class="pc-spark tall">{spark_svg(stables.get("spark"), w=300, h=84)}</div>
      <p class="pc-note">A growing float is money staying in crypto, staged to buy. A
      shrinking float is money leaving the arena entirely.</p></div>
  </div>"""

    network_html = ""
    if network:
        diff = network.get("difficulty_change_pct", 0)
        network_html = f"""<div class="sec-head" style="margin-top:26px"><h2>Bitcoin network</h2><span class="bar"></span></div>
  <div class="pulse-card"><div class="pc-chips" style="margin-top:2px">
    {_chip(f'next-block fee {network.get("fastest_fee", "?")} sat/vB')}
    {_chip(f'1-hour fee {network.get("hour_fee", "?")} sat/vB')}
    {_chip(f'difficulty est. {diff:+.1f}%', "chip-up" if diff >= 0 else "chip-down")}
    {_chip(f'{network.get("retarget_blocks", "?")} blocks to retarget')}</div>
  <p class="pc-note">Low fees mean a quiet chain; rising difficulty means miners are adding
  machines (long-term confidence), falling difficulty means some are switching off.</p></div>"""

    body = f"""<main class="wrap"><section class="page">
  <span class="kicker">Market data desk</span>
  <h1>Market Pulse</h1>
  <p class="lede">The market's vital signs: crowd sentiment, price posture, and dry powder,
     computed with standard formulas from free public data and explained in plain language.</p>
  {fng_html}
  {assets_html}
  {stables_html}
  {network_html}

  <div class="sec-head" style="margin-top:30px"><h2>Pulse 101</h2><span class="bar"></span></div>
  <div class="learn-grid">
    <div class="learn"><span class="lab">Fear &amp; Greed</span>
      <p>A 0-100 crowd sentiment score. Extreme fear has historically shown up near local
      bottoms and extreme greed near local tops, because crowds overreact in both directions.
      It tells you the mood, never the value.</p></div>
    <div class="learn"><span class="lab">RSI</span>
      <p>The Relative Strength Index compares recent gains to recent losses on a 0-100 scale.
      Above 70 reads as <b>hot</b> (overbought), below 30 as <b>cold</b> (oversold). Extremes
      often cool off, but a strong trend can stay hot for weeks.</p></div>
    <div class="learn"><span class="lab">Momentum (MACD)</span>
      <p>MACD compares a fast moving average to a slow one. When the fast line sits above its
      signal line, momentum is <b>building</b>; below it, momentum is <b>fading</b>. It shows
      which way the wind is blowing, not how long it will blow.</p></div>
    <div class="learn"><span class="lab">Trend (moving averages)</span>
      <p>The 200-day average is the classic bull/bear line: price above it reads as an uptrend.
      When the 50-day crosses above the 200-day, that is a <b>golden cross</b> and trend
      followers take notice. Crossing below is the bearish twin, the <b>death cross</b>.</p></div>
    <div class="learn"><span class="lab">Stablecoin float</span>
      <p>Stablecoins are dollars that already made the jump into crypto. When the total float
      grows, money is staging to buy. When it shrinks, money is going back to the exit. It is
      the market's fuel gauge.</p></div>
    <div class="learn"><span class="lab">What this page is not</span>
      <p>Indicators describe the recent past; none of them predict. We publish them with fixed,
      standard formulas so you can learn to read them yourself, and we will never turn them
      into a buy or sell call. That is the deal.</p></div>
  </div>
  <p class="nfa">{esc(pulse.get("note", ""))} {esc(NFA)}</p>
</section></main>"""
    return shell(f"Market Pulse - {NAME}", desc, "Market Pulse", body, dateline, path="/pulse.html")


def render_404(dateline):
    body = """<main class="wrap narrow"><section class="page" style="text-align:center;padding-top:60px">
  <span class="kicker">404</span>
  <h1>That page moved on.</h1>
  <p class="lede" style="margin-left:auto;margin-right:auto">The story you were looking for is not
     here. Try the <a href="/index.html">front page</a> or the <a href="/archive.html">archive</a>.</p>
</section></main>"""
    return shell(f"Not found - {NAME}", "Page not found.", None, body, dateline,
                 path="/404.html", noindex=True)


def render_thanks(dateline):
    body = """<main class="wrap narrow"><section class="page" style="text-align:center;padding-top:60px">
  <span class="kicker">Subscribed</span>
  <h1>You are on the list.</h1>
  <p class="lede" style="margin-left:auto;margin-right:auto">Thanks for subscribing to the brief.
     We will not sell your email, and you can unsubscribe anytime. Back to the
     <a href="/index.html">front page</a>.</p>
</section></main>"""
    return shell(f"Subscribed - {NAME}", "Thanks for subscribing.", None, body, dateline,
                 path="/thanks.html", noindex=True)


# ---- ingest approved payloads -----------------------------------------------

def ingest():
    """Promote approved payloads (out/published/*.json from publish.py) into committed content."""
    if not os.path.isdir(PUBLISHED):
        print("ingest: no out/published/ (nothing approved yet); building from committed content only.")
        return 0
    # date from the run, not a wall clock, so builds stay reproducible
    date = "undated"
    try:
        date = json.load(open(os.path.join(HERE, "out", "items.json"), encoding="utf-8"))["_meta"]["generated"][:10]
    except Exception:
        pass
    os.makedirs(CONTENT, exist_ok=True)
    n = 0
    for fn in sorted(os.listdir(PUBLISHED)):
        if not fn.endswith(".json"):
            continue
        rec = json.load(open(os.path.join(PUBLISHED, fn), encoding="utf-8"))
        payload = rec.get("payload", {})
        art = payload.get("article", {})
        title = art.get("title") or "Untitled"
        slug = slugify(title)
        body = art.get("body", "")
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()] or [body]
        srcs = [{"title": u, "url": u} for u in art.get("sources", [])]
        item = {
            "id": rec.get("id"), "slug": slug, "kind": "brief",
            "title": title, "dek": (payload.get("script", {}) or {}).get("summary", ""),
            "date": date, "category": "news", "verdict": rec.get("verdict"),
            "author": "The Crypto Cronkite desk",
            "key_fact": (payload.get("script", {}) or {}).get("key_fact", ""),
            "human_take": art.get("human_take", ""), "body": paras, "sources": srcs,
        }
        out = os.path.join(CONTENT, f"{date}-{slug}.json")
        json.dump(item, open(out, "w", encoding="utf-8"), indent=2)
        print(f"  ingested {rec.get('id')} -> {os.path.relpath(out)}")
        n += 1
    print(f"ingest: promoted {n} approved item(s) into site content.")
    return n


# ---- build -------------------------------------------------------------------

def _copytree(src, dst):
    os.makedirs(dst, exist_ok=True)
    for root, _dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(target, exist_ok=True)
        for f in files:
            data = open(os.path.join(root, f), "rb").read()
            open(os.path.join(target, f), "wb").write(data)


def build():
    items = load_content()
    # dateline reflects the newest content (or a neutral standing line), never a wall clock
    newest = next((i.get("date") for i in items if not i.get("example") and i.get("date")), None)
    dateline = fmt_date(newest).upper() if newest else "AN HONEST CRYPTO NEWS DESK"

    import shutil
    if os.path.isdir(PUBLISH):
        shutil.rmtree(PUBLISH)
    os.makedirs(os.path.join(PUBLISH, "articles"), exist_ok=True)
    _copytree(ASSETS, os.path.join(PUBLISH, "assets"))

    def w(rel, html):
        path = os.path.join(PUBLISH, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(html)

    w("index.html", render_index(items, dateline))
    w("flows.html", render_flows(load_flows(), dateline))
    w("pulse.html", render_pulse(load_pulse(), dateline))
    w("archive.html", render_archive(items, dateline))
    w("method.html", render_method(items, dateline))
    w("about.html", render_about(dateline))
    w("standards.html", render_standards(dateline))
    w("404.html", render_404(dateline))
    w("thanks.html", render_thanks(dateline))
    for it in items:
        w(os.path.join("articles", f"{it['slug']}.html"), render_article(it))

    # the social card lives at the site root (family convention: /og-image.png)
    og_src = os.path.join(ASSETS, "og-image.png")
    if os.path.exists(og_src):
        open(os.path.join(PUBLISH, "og-image.png"), "wb").write(open(og_src, "rb").read())

    # sitemap (indexable pages only; 404/thanks are noindex), robots, netlify 404 redirect
    locs = ["/", "/flows.html", "/pulse.html", "/archive.html", "/method.html", "/about.html",
            "/standards.html"]
    locs += [f"/articles/{it['slug']}.html" for it in items if not it.get("example")]
    urls = "\n".join(f"  <url><loc>{ORIGIN}{esc(p)}</loc></url>" for p in locs)
    w("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "\n</urlset>\n")
    w("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {ORIGIN}/sitemap.xml\n")
    w("_redirects", "/*  /404.html  404\n")
    n_live = sum(1 for i in items if not i.get("example"))
    print(f"site: built {PUBLISH} - {n_live} published stor{'y' if n_live == 1 else 'ies'} "
          f"+ {len(items) - n_live} example, plus home/archive/method/about/standards/404.")
    return 0


def main():
    if "--ingest" in sys.argv:
        ingest()
    build()


if __name__ == "__main__":
    main()
