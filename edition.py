#!/usr/bin/env python3
"""
edition.py: The Edition, the composed front page (owner spec 2026-08-03; reconciled
against the approved edition-demo.html per the owner's reconciliation order).

THE CHASSIS RENDERER. Crypto first per the build order; News and Sports extend by
SKINNING (the DESK dict is the whole per-desk surface; anything crypto-specific outside
it is a bug). The desk already exercises judgment (rank, the Brief, the verifier); this
layer RENDERS that judgment. It re-ranks nothing, fetches nothing, and adds no
commercial element (tier doctrine).

DEMO RECONCILIATION (demo wins on composition and proportions; inference only where the
demo is silent): two-font system (serif body/display, Inter furniture), in-flow topbar
with Vol/No and the mode toggles, masthead weight 600 with motto, dateline rules 2px
over 1px, uniform rail sizing, brief band as kicker+stamp head with three columns and
no display headline, down-page left-rule cards, demo color tokens in all three themes,
data-theme semantics on the document element. Every resolved difference is listed in
the build report, not resolved silently.

FIELD-GAP RULINGS (owner, 2026-08-03): sections ship as routes ONLY when real per-story
tags exist; the corpus is uniformly category="news", so v1 renders the sections nav
with only its REAL destinations (Front Page, Back Issues) and no dead links. Kickers
render only real data: the house desk label plus "Updated" when update_of is set.
Reading-mode preference persists via the site's established guarded-localStorage
pattern (ruling accepted).

The demo names 'Newsreader' first in the serif stack without loading it, so Georgia
renders in practice; the stack is kept verbatim so a later self-hosted Newsreader
lights up without a template change.
"""
import datetime
import html as _html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

DESK = {
    "name": "GoCheckMyCrypto",
    "motto": "Independent · No Hype · Every Source Linked",
    "folio": ("GoCheckMyCrypto is a site of Go Check My Brands LLC · "
              "Every source linked · Never financial advice"),
    "place": "Charleston, S.C.",
    "origin": "https://gocheckmycrypto.com",
    "desk_label": "The Desk",
    "volume": "Vol. I",
    # the demo's crypto section list, held as chassis data until real per-story tags
    # exist to scope routes (owner ruling: no dead links, no keyword-faked sections)
    "sections_when_tagged": ["Regulation", "Markets", "Security", "Mining"],
}


def esc(s):
    return _html.escape(str(s or ""), quote=True)


def _when(d):
    return str(d.get("published_utc") or d.get("date") or "")


def _is_edition(d):
    return (d.get("category") or "").lower() == "daily edition"


def _day_of(d):
    return _when(d)[:10]


CYCLE_HOURS = 30      # the front carries the news CYCLE, not midnight-to-midnight
FRONT_SLOTS = 10      # lead + three rail + six down-page
MAX_BACKFILL_H = 72   # the density floor's reach: a quiet cycle widens its window in
                      # steps until the front fills or the cap is hit (owner direction
                      # 2026-08-03: readers get a full paper, never a scarce one; only
                      # real desk reporting, never padding)


def select(items, day):
    """One edition's inputs: the day's edition item (the Brief) and the ranked stories
    of its news cycle. The window is CYCLE_HOURS back from the edition's own timestamp
    (owner review note, 2026-08-03: a calendar-day window starved a light day to three
    stories while the composition holds ten; an afternoon edition legitimately carries
    the prior evening's reporting). Ranking is the desk's own `rank`; the composition
    renders it, never re-ranks, and never reaches past its own edition's press time."""
    eds = sorted((d for d in items if _is_edition(d) and _day_of(d) == day),
                 key=_when, reverse=True)
    ed = eds[0] if eds else None
    press = _when(ed) if ed else f"{day}T23:59:59Z"
    p = datetime.datetime.fromisoformat(press.replace("Z", "+00:00"))
    hi = press
    hours = CYCLE_HOURS
    while True:
        lo = (p - datetime.timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
        stories = [d for d in items if not _is_edition(d) and not d.get("example")
                   and lo <= _when(d) <= hi]
        if len(stories) >= FRONT_SLOTS or hours >= MAX_BACKFILL_H:
            break
        hours += 12
    stories.sort(key=lambda d: (_day_of(d) != day,
                                d.get("rank") if isinstance(d.get("rank"), (int, float))
                                else 999, _when(d)))
    return ed, stories


def edition_days(items):
    return sorted({_day_of(d) for d in items if _is_edition(d)}, reverse=True)


def _clip(text, n):
    """Cut at a word boundary and never on a dangling function word."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(t) <= n:
        return t
    cut = t[:n].rsplit(" ", 1)[0].rstrip(",;:")
    words = cut.split(" ")
    STOP = {"and", "or", "but", "the", "a", "an", "as", "with", "of", "to", "in",
            "on", "at", "for", "its", "his", "her", "their", "even", "while",
            "across", "that"}
    while words and words[-1].lower().rstrip(".,") in STOP:
        words.pop()
    cut = " ".join(words).rstrip(",;:")
    return cut + ("." if not cut.endswith(".") else "")


# ONE LOOK (Program 6, Sprint 6.1, 11 October 2026). The Edition page used to carry its own
# newspaper design: its own paper and ink, a masthead with the old desk name, Print/Night/E-ink
# toggles, justified columns and a drop cap. It now draws from the site's tokens (system.css),
# so it is a page of the same publication, and dark mode is the site's own.
CSS = """
.ed-sheet{max-width:1080px;margin:0 auto;padding:34px 22px 56px;font-family:var(--sans)}
@media(min-width:1280px){.ed-sheet{max-width:1400px}}  /* Sprint 9.5b: the same width as the page wrapper */
.ed-head{border-bottom:1px solid var(--line);padding-bottom:14px;margin-bottom:22px}
.ed-head h1{font-family:var(--serif);font-weight:600;font-size:clamp(28px,4.4vw,42px);
  line-height:1.1;letter-spacing:-.01em;margin:.2em 0 .3em;color:var(--ink)}
.ed-dateline{font-family:var(--mono);font-size:12px;color:var(--muted);margin:0}
.ed-kicker{font-family:var(--sans);font-size:11px;font-weight:600;letter-spacing:.1em;
  text-transform:uppercase;color:var(--rule)}
.ed-front{display:grid;gap:0 2.2rem;grid-template-columns:1fr}
@media(min-width:900px){
  .ed-front{grid-template-columns:1.9fr 1fr}
  .ed-lead{border-right:1px solid var(--line);padding-right:2.2rem}
}
.ed-lead h2{font-family:var(--serif);font-weight:600;font-size:clamp(24px,3.2vw,34px);
  line-height:1.15;margin:.35rem 0 .5rem;letter-spacing:-.005em}
.ed-lead h2 a,.ed-rail h3 a,.ed-downpage h3 a{color:var(--ink)}
.ed-dek{font-size:1.02rem;color:var(--muted);margin:0 0 .9rem;line-height:1.5}
.ed-byline{font-family:var(--mono);font-size:12px;color:var(--muted);margin:0 0 .9rem}
.ed-copy p{margin:0 0 .85rem;font-size:1rem;line-height:1.65;color:var(--ink)}
.ed-continued{font-family:var(--sans);font-size:.85rem;font-weight:600;margin:0}
.ed-rail article{padding:0 0 1.1rem;margin-bottom:1.1rem;border-bottom:1px solid var(--line)}
.ed-rail article:last-child{border-bottom:none}
.ed-rail h3{font-family:var(--serif);font-weight:600;font-size:1.2rem;line-height:1.2;margin:.3rem 0 .35rem}
.ed-rail p,.ed-downpage p{font-size:.95rem;line-height:1.5;color:var(--muted);margin:0}
.ed-brief{margin-top:2.2rem;border-top:2px solid var(--ink);padding-top:1.1rem}
.ed-brief-head{display:flex;align-items:baseline;gap:1rem;flex-wrap:wrap;margin-bottom:.8rem}
.ed-brief-head .ed-kicker{color:var(--ink)}
.ed-stamp{font-family:var(--mono);font-size:12px;color:var(--muted)}
.ed-brief-cols p{margin:0 0 .85rem;font-size:1rem;line-height:1.65;max-width:42rem;color:var(--ink)}
.ed-brief-cites{margin-top:.9rem;padding-top:.6rem;border-top:1px solid var(--line);
  font-size:.85rem;color:var(--muted)}
.ed-brief-cites a{margin-right:1.2rem}
.ed-downpage{margin-top:2rem;border-top:1px solid var(--line);padding-top:1.2rem;display:grid;
  gap:1.4rem 2.2rem;grid-template-columns:1fr}
@media(min-width:760px){.ed-downpage{grid-template-columns:repeat(3,1fr)}}
.ed-downpage article{border-left:2px solid var(--line);padding-left:.9rem}
.ed-downpage h3{font-family:var(--serif);font-weight:600;font-size:1.05rem;line-height:1.25;margin:.25rem 0 .3rem}
.ed-backrow{margin-top:2rem;font-family:var(--mono);font-size:12px;color:var(--muted)}
.ed-folio{margin-top:2.2rem;border-top:1px solid var(--line);padding-top:.7rem;display:flex;
  justify-content:space-between;flex-wrap:wrap;gap:.6rem;font-size:.8rem;color:var(--muted)}
@media print{
  @page{margin:14mm 12mm}
  .ed-backrow{display:none}
  body{background:#fff;color:#000}
  a{color:#000}
  .ed-rail article,.ed-downpage article{break-inside:avoid}
}
"""


def _edition_slot(ed):
    t = str(ed.get("title") or "") if ed else ""
    m = re.search(r"(Morning|Afternoon|Midday|Evening)", t, re.I)
    return (m.group(1).title() + " Brief") if m else "The Brief"


def _brief_name(ed):
    t = str(ed.get("title") or "") if ed else ""
    m = re.search(r"The\s+\w+\s+(?:Brief|Wrap|Update)", t, re.I)
    return m.group(0) if m else "The Brief"


def _human_date(day):
    return datetime.date.fromisoformat(day).strftime("%A, %B %-d, %Y")


def _utc_stamp(d):
    m = re.search(r"T(\d{2}):(\d{2})", _when(d))
    if not m:
        return ""
    hh, mm = int(m.group(1)), m.group(2)
    ampm = "AM" if hh < 12 else "PM"
    return f"{(hh % 12) or 12}:{mm} {ampm} UTC"


def _story_url(d):
    return f"/articles/{esc(d.get('slug'))}.html"


def _byline(d, desk):
    """The one name: a story stored under the retired desk name prints under the desk's."""
    a = str(d.get("author") or "")
    return desk["name"] if (not a or "Cronkite" in a) else a


def _kicker(desk, d):
    """Real data only (owner ruling): the house desk label, plus Updated when the
    story really is an update. No invented sections, no keyword matching."""
    k = desk["desk_label"]
    if d.get("update_of"):
        k += " · Updated"
    return esc(k)



def _latest_edition_path(all_days):
    """The newest dated edition; nav points here now that /news is the news hub."""
    return f"/edition/{all_days[0]}.html" if all_days else "/news.html"

def _cites(ed, html_text):
    """Sprint 9.4 (AUDIT.md 3.2, "Linked"): the Brief cites the Big movers it mentions (movers.cite, no model call)."""
    try:
        import movers
        return movers.cite(html_text, str((ed or {}).get("date") or "")[:10])
    except Exception:                                             # noqa: BLE001 fail open
        return html_text


def render_front(desk, items, day, all_days, canonical_path="/news.html"):
    ed, stories = select(items, day)
    lead = stories[0] if stories else None
    rail = stories[1:4]
    down = stories[4:10]
    slot = _edition_slot(ed)
    issue_no = len(all_days) - all_days.index(day)

    head = f"""<header class="ed-head">
  <span class="ed-kicker">The Brief</span>
  <h1>{esc(slot)}, {esc(_human_date(day))}</h1>
  <p class="ed-dateline">Issue No. {issue_no} &middot; {esc(desk["place"])}</p>
</header>"""

    lead_html = ""
    if lead:
        opening = "".join(f"<p>{p}</p>" for p in (lead.get("body") or [])[:3])
        lead_html = f"""<article class="ed-lead">
  <span class="ed-kicker">{_kicker(desk, lead)}</span>
  <h2><a href="{_story_url(lead)}">{esc(lead.get("title"))}</a></h2>
  <p class="ed-dek">{esc(lead.get("dek"))}</p>
  <p class="ed-byline">By {esc(_byline(lead, desk))} &middot; {esc(_utc_stamp(lead))}</p>
  <div class="ed-copy">{opening}</div>
  <p class="ed-continued"><a href="{_story_url(lead)}">Continued &#8594;</a></p>
</article>"""

    rail_html = "".join(f"""<article>
  <span class="ed-kicker">{_kicker(desk, d)}</span>
  <h3><a href="{_story_url(d)}">{esc(d.get("title"))}</a></h3>
  <p>{esc(_clip(d.get("dek"), 220))}</p>
</article>""" for d in rail)

    brief_html = ""
    if ed:
        cites = "".join(
            f'<a href="{esc(s.get("url") or "#")}">{esc(_clip(s.get("title") or s.get("url") or "", 60))}</a>'
            for s in (ed.get("sources") or [])[:8])
        brief_html = f"""<section class="ed-brief" aria-label="{esc(_brief_name(ed))}">
  <div class="ed-brief-head">
    <span class="ed-kicker">{esc(_brief_name(ed))}</span>
    <span class="ed-stamp">{esc(_utc_stamp(ed))}</span>
  </div>
  <div class="ed-brief-cols">{_cites(ed, "".join(f"<p>{p}</p>" for p in (ed.get("body") or [])))}</div>
  <div class="ed-brief-cites">In this brief: {cites}</div>
</section>"""

    down_html = "".join(f"""<article>
  <h3><a href="{_story_url(d)}">{esc(d.get("title"))}</a></h3>
  <p>{esc(_clip(d.get("dek"), 140))}</p>
</article>""" for d in down)
    down_html = (f'<section class="ed-downpage" aria-label="More from the desk">'
                 f'{down_html}</section>') if down_html else ""

    prev_links = " &middot; ".join(
        f'<a href="/edition/{d}.html">{d}</a>' for d in all_days[:14] if d != day)

    return f"""<style>{CSS}</style>
<main class="ed-sheet">
{head}
<div class="ed-front">
{lead_html}
<aside class="ed-rail" aria-label="Top stories">{rail_html}</aside>
</div>
{brief_html}
{down_html}
<div class="ed-backrow">Back issues: {prev_links}</div>
<div class="ed-folio">
  <span>{esc(desk["folio"])}</span>
  <span><a href="/standards.html">Standards &amp; Corrections</a> &middot; <a href="/archive.html">Archive</a></span>
</div>
</main>"""


def build(items, w, desk=DESK, shell=None):
    """Render the edition at the Latest route plus every back issue. `shell` is the
    site's own page wrapper, so the Edition carries the site masthead, nav and footer
    like every other page (owner correction 2026-08-04: it is a page OF the site).
    `desk` remains the entire per-desk skinning surface."""
    days = edition_days(items)
    if not days:
        return 0

    def page(day, path):
        ed, _ = select(items, day)
        body = render_front(desk, items, day, days, canonical_path=path)
        title = f"{_edition_slot(ed)} - {desk['name']}"
        if shell is None:
            return ("<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
                    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
                    f"<title>{esc(title)}</title></head><body>{body}</body></html>")
        # THE EDITION'S UNIQUE CONTENT IS THE BRIEF, AND THE BRIEF HAS ITS OWN URL
        # (owner SEO audit 2026-08-25). 82% of edition body text is verbatim paragraphs
        # from the article pages, and the one original part, the brief, is published at
        # /articles/<brief-slug> and sits in the sitemap. So the composite page names the
        # brief as canonical instead of competing with it: 31 orphaned near-duplicates
        # stop asking to be indexed on their own.
        canon = f"/articles/{ed['slug']}.html" if ed and ed.get("slug") else path
        return shell(title,
                     f"The composed daily Brief of {desk['name']} for "
                     f"{_human_date(day)}: the desk's ranked reporting and its brief, "
                     f"as one front page.",
                     "The Brief", body, _human_date(day).upper(),
                     path=path, brand="cronkite", og_type="website",
                     canonical_path=canon)

    # /news IS NOT THE EDITION (owner SEO audit 2026-08-25). This used to overwrite
    # news.html with the newest edition, AFTER site_build had already written the real
    # news hub there, which made render_news dead code and left /news byte-identical to
    # /edition/<today> apart from one aria-current attribute: a page that changes every
    # day, duplicating a stable dated twin, is the exact shape Google reports as
    # "crawled, currently not indexed". The hub keeps /news; the editions keep their
    # dated URLs; nav points at the newest one.
    for d in days:
        w(f"edition/{d}.html", page(d, f"/edition/{d}.html"))
    return len(days)
