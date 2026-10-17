/* coinchart.js: THE COIN CHART (Program 7, Sprint 6.4, 13 October 2026).
   One file for every coin page, cached by its content hash, so the chart code is not in
   a hundred pages. It reads CoinGecko's market_chart for the coin's id and draws:

     1D  days=1    5-minute points   (~289)   the finest the source gives
     7D  days=7    hourly points     (~169)
     1M  days=365  daily points, the last 30 days
     1Y  days=365  daily points      (~366)   one request serves 1M and 1Y

   The 50-day and 200-day lines are averages of DAILY closes, so they come from the 366-day
   series and are drawn on 1M and 1Y only, where they mean something. CoinGecko's free tier gives
   365 days and no more, and that is enough: each line begins on the first day it has a full
   window of real history (day 50, day 200), one point a day, never bridged and never drawn from
   invented history, and a muted line under the 1Y chart says where each one starts. They are drawn as one
   smooth curve through the daily averages and named in the right gutter beside the price
   axis, never on the line. Volume bars are drawn on 1M and 1Y only, where each bar is a
   day's volume; on 1D and 7D the source gives a trailing 24-hour figure at every point, so
   every bar would be the same height and the window shows none.

   The line is Program 7's one style (glow.py): 3 px, a glow, an area fill, the high and low
   as white dots with mono labels, a halo on the last point. It is colored by the chosen
   window's own change, first point to last, and recolored when the tab changes, and the
   change printed beside it is that same number. The chosen window lives in this closure for
   the visit and nowhere else: no storage, no cookie. The line draws once and never loops;
   with reduced motion it is whole at once.

   The build's seven-day line is the fallback, stamped as such. A blocked or rate-limited
   fetch leaves it standing and says so. */
(function () {
  'use strict';
  var wrap = document.querySelector('[data-coin-chart]');
  if (!wrap) return;
  var id = wrap.getAttribute('data-coin-id') || '';
  var stage = wrap.querySelector('.cc-stage');
  var box = wrap.querySelector('.cc-box');
  var readout = wrap.querySelector('.cc-readout');
  var cap = wrap.querySelector('[data-coin-cap]');
  var maNote = wrap.querySelector('[data-coin-ma-start]');
  var chgEl = wrap.querySelector('.cc-chg');
  var tabs = Array.prototype.slice.call(wrap.querySelectorAll('[role=tab]'));
  var tablist = wrap.querySelector('[role=tablist]');
  if (!id || !stage || !box || !readout || !tabs.length) return;

  /* ONE FIGURE, ONE SOURCE (13 October 2026). On 1D and 7D the high and low printed here are the
     snapshot's own pair, read off the page the build wrote (the tape prints the same two); the
     chart never prints a high or low computed from its own live series on those windows, and
     prints none when the snapshot has none. 1M and 1Y have no snapshot figure, so they print
     their own series' extremes, each worded with its window ("1M high") so it never reads as
     the 24-hour figure. */
  function snapNum(a) { var v = parseFloat(wrap.getAttribute(a)); return isFinite(v) ? v : null; }
  var SNAPF = { '1d': { lo: snapNum('data-lo24'), hi: snapNum('data-hi24'), w: '24h' },
                '7d': { lo: snapNum('data-lo7'), hi: snapNum('data-hi7'), w: '7D closing' } };
  function figs(s) {
    var f = SNAPF[s.r];
    if (f) return (f.lo !== null && f.hi !== null) ? f : null;
    return { lo: Math.min.apply(null, s.y), hi: Math.max.apply(null, s.y), w: s.r === '1m' ? '1M' : '1Y' };
  }

  var DAY = 86400000;
  var DAILY = { '1m': true, '1y': true };                 /* the windows whose volume is a day's volume */
  var RANGES = {
    '1d': { fetch: 1, label: '24 hours', spacing: '5-minute' },
    '7d': { fetch: 7, label: '7 days', spacing: 'hourly' },
    '1m': { fetch: 365, label: '1 month', spacing: 'daily', span: 30 * DAY },
    '1y': { fetch: 365, label: '1 year', spacing: 'daily', span: 365 * DAY }
  };
  var reduce = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var cur = wrap.getAttribute('data-range') || '7d';     /* this visit only; nothing is stored */
  var fetched = {};                                       /* days -> Promise of {p, v} */
  var shown = null;                                       /* what is on screen */
  var drawn = false;                                      /* the one-time draw has run */
  var idx = -1;                                           /* the crosshair's point */
  var seq = 0;

  /* ---- formats ---- */
  function money(v, dec) {
    if (dec === undefined) dec = v >= 1 ? 2 : v >= 0.01 ? 4 : 6;
    return '$' + Number(v).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }
  function compact(v) {
    var a = Math.abs(v);
    if (a >= 1e9) return '$' + (v / 1e9).toFixed(1) + 'B';
    if (a >= 1e6) return '$' + (v / 1e6).toFixed(1) + 'M';
    if (a >= 1e3) return '$' + (v / 1e3).toFixed(0) + 'K';
    return '$' + v.toFixed(0);
  }
  function pct(v) {
    if (Math.abs(v) < 0.005) return '0.00%';
    return (v > 0 ? '+' : '-') + Math.abs(v).toFixed(2) + '%';
  }
  function fmtDate(ms, o, utc) {
    o.timeZone = utc ? 'UTC' : 'America/New_York';
    return new Date(ms).toLocaleString('en-US', o);
  }
  function tickLabel(ms, r) {
    if (r === '1d') return fmtDate(ms, { hour: 'numeric' });
    if (r === '1y') return fmtDate(ms, { month: 'short', year: '2-digit' }, true).replace(/ (\d\d)$/, " '$1");
    return fmtDate(ms, { month: 'short', day: 'numeric' }, r !== '7d');
  }
  function readDate(ms, r) {
    if (r === '1d') return fmtDate(ms, { hour: 'numeric', minute: '2-digit' }) + ' ET';
    if (r === '7d') return fmtDate(ms, { month: 'short', day: 'numeric', hour: 'numeric' }) + ' ET';
    return fmtDate(ms, { month: 'short', day: 'numeric', year: 'numeric' }, true);
  }
  /* a smooth path through points, monotone in y (Fritsch-Carlson), so it never overshoots a turn */
  function smooth(q) {
    var n = q.length, h = [], m = [], t = [], i, f = function (v) { return v.toFixed(1); }, d = 'M' + f(q[0][0]) + ',' + f(q[0][1]);
    for (i = 0; i < n - 1; i++) { h.push(q[i + 1][0] - q[i][0] || 1e-6); m.push((q[i + 1][1] - q[i][1]) / h[i]); }
    t[0] = m[0]; t[n - 1] = m[n - 2];
    for (i = 1; i < n - 1; i++) t[i] = m[i - 1] * m[i] <= 0 ? 0 : (m[i - 1] + m[i]) / 2;
    for (i = 0; i < n - 1; i++) {
      var a = t[i] / m[i], b = t[i + 1] / m[i], s = a * a + b * b, k = s > 9 ? 3 / Math.sqrt(s) : 1, w = h[i] / 3;
      d += 'C' + f(q[i][0] + w) + ',' + f(q[i][1] + k * a * m[i] * w) + ' ' + f(q[i + 1][0] - w) + ',' +
        f(q[i + 1][1] - k * b * m[i] * w) + ' ' + f(q[i + 1][0]) + ',' + f(q[i + 1][1]);
    }
    return d;
  }
  function dir(a, b) { return b > a ? 'up' : b < a ? 'down' : 'flat'; }

  /* ---- data ---- */
  function load(days) {
    if (fetched[days]) return fetched[days];
    var url = 'https://api.coingecko.com/api/v3/coins/' + encodeURIComponent(id) +
      '/market_chart?vs_currency=usd&days=' + days;
    function once(n) {
      return fetch(url).then(function (r) {
        if ((r.status === 429 || r.status >= 500) && n < 1) {
          return new Promise(function (ok) { setTimeout(ok, 1600); }).then(function () { return once(n + 1); });
        }
        if (!r.ok) throw new Error('http ' + r.status);
        return r.json();
      });
    }
    var pr = once(0).then(function (d) {
      if (d && d.p) return d;
      var p = d && d.prices, v = (d && d.total_volumes) || [];
      if (!p || p.length < 3) throw new Error('short');
      return { p: p, v: v.length === p.length ? v : null };
    });
    fetched[days] = pr;
    pr['catch'](function () { delete fetched[days]; });
    return pr;
  }
  function sma(vals, n) {
    var out = [], run = 0;
    for (var i = 0; i < vals.length; i++) {
      run += vals[i];
      if (i >= n) run -= vals[i - n];
      out.push(i >= n - 1 ? run / n : null);
    }
    return out;
  }
  /* the points a window shows, with its averages (1M and 1Y only) */
  function build(r, raw) {
    var p = raw.p, v = raw.v, start = 0;
    if (RANGES[r].span) {
      var cut = p[p.length - 1][0] - RANGES[r].span;
      while (start < p.length - 3 && p[start][0] < cut) start++;
    }
    var pts = p.slice(start), vols = v ? v.slice(start) : null;
    var s = { r: r, t: [], y: [], v: [], n: 0 };
    for (var i = 0; i < pts.length; i++) {
      s.t.push(pts[i][0]); s.y.push(pts[i][1]); s.v.push(vols ? vols[i][1] : null);
    }
    s.n = s.y.length;
    s.up = [];
    for (var j = 0; j < s.n; j++) s.up.push(j === 0 ? null : s.y[j] >= s.y[j - 1]);
    if (r === '1m' || r === '1y') {
      var all = p.map(function (q) { return q[1]; });
      s.ma50 = sma(all, 50).slice(start);
      s.ma200 = sma(all, 200).slice(start);
    }
    s.dir = dir(s.y[0], s.y[s.n - 1]);
    s.chg = (s.y[s.n - 1] - s.y[0]) / Math.abs(s.y[0]) * 100;
    /* ONE SEVEN-DAY FIGURE PER PAGE (Sprint 9.1): on 7D the printed change is the readings tile's
       rolling 7-day figure, which the build wrote on this element, so it does not change between
       loads; the line takes that figure's sign (color truth: a figure and its color are one).
       Every other window prints its own series and names its window. */
    var c7 = parseFloat(wrap.getAttribute('data-chg7'));
    if (r === '7d' && isFinite(c7)) { s.chg = c7; s.dir = c7 > 0 ? 'up' : c7 < 0 ? 'down' : 'flat'; }
    return s;
  }

  /* ---- drawing ---- */
  function niceStep(rough) {
    var mag = Math.pow(10, Math.floor(Math.log(rough) / Math.LN10)), m = [1, 2, 2.5, 5, 10];
    for (var i = 0; i < m.length; i++) if (rough <= m[i] * mag * 1.0000001) return m[i] * mag;
    return 10 * mag;
  }
  function decFor(step) {
    var d = 0; while (d < 8 && Math.abs(step * Math.pow(10, d) - Math.round(step * Math.pow(10, d))) > 1e-9) d++;
    return d;
  }
  var NS = 'http://www.w3.org/2000/svg';
  function el(name, attrs, text) {
    var e = document.createElementNS(NS, name);
    for (var k in attrs) if (attrs.hasOwnProperty(k)) e.setAttribute(k, attrs[k]);
    if (text !== undefined) e.textContent = text;
    return e;
  }

  var G = {};   /* the geometry of the chart on screen, for the crosshair */

  function draw(s) {
    var W = Math.max(280, Math.floor(stage.clientWidth));
    var hasMA = !!(s.ma50 || s.ma200), hasVol = DAILY[s.r];
    var R = hasMA ? 100 : 64, L = 6, T = 20, HP = W < 480 ? 210 : 280, GAP = hasVol ? 8 : 16, HV = hasVol ? 44 : 0, AX = 26;
    var H = T + HP + GAP + HV + AX, PW = W - L - R;
    var lo = Math.min.apply(null, s.y), hi = Math.max.apply(null, s.y);
    [s.ma50, s.ma200].forEach(function (m) {
      if (!m) return;
      m.forEach(function (x) { if (x !== null) { lo = Math.min(lo, x); hi = Math.max(hi, x); } });
    });
    var span = (hi - lo) || Math.abs(hi) * 0.01 || 1;
    var pl = lo - span * 0.05, ph = hi + span * 0.1;
    var t0 = s.t[0], t1 = s.t[s.n - 1], tspan = (t1 - t0) || 1;
    var X = function (t) { return L + (t - t0) / tspan * PW; };
    var Y = function (v) { return T + HP - (v - pl) / (ph - pl) * HP; };
    var d = s.dir;
    var svg = el('svg', { 'class': 'cc-svg', width: W, height: H, viewBox: '0 0 ' + W + ' ' + H,
      role: 'img', 'aria-label': RANGES[s.r].label + ' of price.' + (figs(s) ? ' ' + figs(s).w + ' low ' +
        money(figs(s).lo) + ', ' + figs(s).w + ' high ' + money(figs(s).hi) + ',' : '') +
        ' latest ' + money(s.y[s.n - 1]) + ', ' + pct(s.chg) + '.' });

    /* gridlines and the price axis, on the right */
    var step = niceStep((ph - pl) / 4), dec = decFor(step);
    var first = Math.ceil(pl / step) * step;
    for (var tv = first; tv <= ph + step * 1e-9; tv += step) {
      var gy = Y(tv);
      svg.appendChild(el('line', { 'class': 'cc-grid', x1: L, x2: L + PW, y1: gy.toFixed(1), y2: gy.toFixed(1) }));
      svg.appendChild(el('text', { 'class': 'cc-ax', 'data-axis': 'price', x: L + PW + 6,
        y: (gy + 4).toFixed(1) }, money(tv, dec)));
    }

    /* the area under the line, tinted by the window's own direction */
    var gid = 'cc-ag';
    var defs = el('defs', {});
    var lg = el('linearGradient', { id: gid, x1: 0, y1: 0, x2: 0, y2: 1 });
    lg.appendChild(el('stop', { offset: 0, 'class': 'cc-st ' + d, 'stop-opacity': 0.30 }));
    lg.appendChild(el('stop', { offset: 1, 'class': 'cc-st ' + d, 'stop-opacity': 0 }));
    defs.appendChild(lg); svg.appendChild(defs);
    var pts = [], i;
    for (i = 0; i < s.n; i++) pts.push([X(s.t[i]), Y(s.y[i])]);
    var ptxt = pts.map(function (q) { return q[0].toFixed(1) + ',' + q[1].toFixed(1); }).join(' ');
    svg.appendChild(el('path', { 'class': 'cc-area ' + d, fill: 'url(#' + gid + ')',
      d: 'M' + pts[0][0].toFixed(1) + ',' + (T + HP) + ' L' + ptxt.replace(/ /g, ' L') +
         ' L' + pts[s.n - 1][0].toFixed(1) + ',' + (T + HP) + ' Z' }));

    /* volume, on its own small scale: up and down by the close against the one before */
    var vg = el('g', { 'class': 'cc-vol' });
    var vmax = 0;
    for (i = 0; i < s.n; i++) if (s.v[i] !== null && s.v[i] > vmax) vmax = s.v[i];
    if (hasVol && vmax > 0) {
      var bw = Math.max(1, Math.min(8, PW / s.n * 0.72)), vy = T + HP + GAP;
      for (i = 0; i < s.n; i++) {
        if (s.v[i] === null) continue;
        var bh = Math.max(1, s.v[i] / vmax * HV);
        vg.appendChild(el('rect', { 'class': s.up[i] === null ? 'flat' : s.up[i] ? 'up' : 'down',
          x: (pts[i][0] - bw / 2).toFixed(1), y: (vy + HV - bh).toFixed(1), width: bw.toFixed(1),
          height: bh.toFixed(1) }));
      }
    }
    svg.appendChild(vg);

    /* the 50-day and 200-day lines, 1M and 1Y only: thin, dashed, one smooth curve through the daily
       averages, and named in the right gutter beside the price axis, never on the line */
    var labels = [];
    [['50', s.ma50], ['200', s.ma200]].forEach(function (pair) {
      var m = pair[1]; if (!m) return;
      var segs = [[]], lastV = null, prevT = null;
      for (var k = 0; k < m.length; k++) {
        if (m[k] === null) continue;
        /* a line starts where its data starts and is never carried across a gap of more than two days */
        if (prevT !== null && s.t[k] - prevT > 2 * DAY) segs.push([]);
        segs[segs.length - 1].push([X(s.t[k]), Y(m[k])]); lastV = m[k]; prevT = s.t[k];
      }
      var mp = segs[segs.length - 1];
      segs = segs.filter(function (q) { return q.length > 1; });
      if (!segs.length) return;
      svg.appendChild(el('path', { 'class': 'cc-ma m' + pair[0], 'data-ma': pair[0], fill: 'none', d: segs.map(smooth).join(' ') }));
      labels.push({ n: pair[0], y: mp[mp.length - 1][1], v: lastV });
    });
    labels.sort(function (a, b) { return a.y - b.y; });
    labels.forEach(function (lb, k) {
      var ly = lb.y + 4;
      if (k > 0) ly = Math.max(ly, labels[k - 1].ly + 15);
      ly = Math.min(Math.max(ly, T + 8), T + HP - 2);
      lb.ly = ly;
      svg.appendChild(el('text', { 'class': 'cc-ma-label m' + lb.n, x: L + PW + 66,
        y: ly.toFixed(1) }, lb.n + 'D'));
    });

    /* the line itself (glow.py's style) and its marks */
    var line = el('polyline', { 'class': 'gl-l ' + d + ' cc-line', 'data-dir': d, points: ptxt,
      filter: 'url(#gl)', pathLength: 1 });
    svg.appendChild(line);
    var hiV = Math.max.apply(null, s.y), loV = Math.min.apply(null, s.y);
    var gH = s.y.lastIndexOf(hiV), gL = s.y.lastIndexOf(loV);
    var marks = el('g', { 'class': 'gl-marks', filter: 'url(#gl)' });
    var ln = pts[s.n - 1];
    marks.appendChild(el('circle', { 'class': 'gl-halo', cx: ln[0].toFixed(1), cy: ln[1].toFixed(1), r: 16,
      fill: 'url(#gl-halo-' + d + ')' }));
    [[gH, 'gl-hi', hiV, -10], [gL, 'gl-lo', loV, 19]].forEach(function (m) {
      if (m[0] === s.n - 1 || (m[1] === 'gl-lo' && gH === gL)) return;
      marks.appendChild(el('circle', { 'class': m[1], cx: pts[m[0]][0].toFixed(1), cy: pts[m[0]][1].toFixed(1), r: 4.5 }));
    });
    marks.appendChild(el('circle', { 'class': 'gl-now ' + d, cx: ln[0].toFixed(1), cy: ln[1].toFixed(1), r: 3 }));
    svg.appendChild(marks);
    [[gH, hiV, -10], [gL, loV, 20]].forEach(function (m, k) {
      if (m[0] === s.n - 1 || (k === 1 && gH === gL)) return;
      var fg = figs(s);
      if (!fg) return;                     /* no snapshot figure for this window: print none */
      var txt = fg.w + (k === 0 ? ' high ' : ' low ') + money(k === 0 ? fg.hi : fg.lo, dec), tw = txt.length * 7.4, cx = pts[m[0]][0];
      cx = Math.min(Math.max(cx, L + tw / 2), L + PW - tw / 2);
      svg.appendChild(el('text', { 'class': 'cc-hl', x: cx.toFixed(1), y: (pts[m[0]][1] + m[2]).toFixed(1),
        'text-anchor': 'middle' }, txt));
    });

    /* dates along the bottom: three or four labels, from the data's own times */
    var nl = PW < 240 ? 3 : W < 460 ? 4 : 5, ay = T + HP + GAP + HV + 18;
    for (i = 0; i < nl; i++) {
      var f = i / (nl - 1), tt = t0 + tspan * f;
      svg.appendChild(el('text', { 'class': 'cc-ax', 'data-axis': 'date', x: (L + PW * f).toFixed(1), y: ay,
        'text-anchor': i === 0 ? 'start' : i === nl - 1 ? 'end' : 'middle' }, tickLabel(tt, s.r)));
    }

    /* the crosshair, drawn into the same svg and moved by the pointer or the keys */
    svg.appendChild(el('line', { 'class': 'cc-cross', y1: T, y2: T + HP + GAP + HV, x1: 0, x2: 0, style: 'display:none' }));
    svg.appendChild(el('circle', { 'class': 'cc-cdot ' + d, r: 5, cx: 0, cy: 0, style: 'display:none' }));

    stage.innerHTML = '';
    stage.appendChild(svg);
    G = { W: W, L: L, PW: PW, X: X, Y: Y, pts: pts, s: s, svg: svg };
    readout.hidden = true;

    if (!drawn) {
      drawn = true;
      if (!reduce && line.animate) {
        line.style.strokeDasharray = '1';
        var a = line.animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: 900, easing: 'ease-out', iterations: 1 });
        a.onfinish = a.oncancel = function () { line.style.strokeDasharray = ''; line.style.strokeDashoffset = ''; };
        [svg.querySelector('.cc-area'), marks].forEach(function (n) {
          n.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 900, easing: 'ease-out', iterations: 1 });
        });
      }
    }
    if (idx >= 0) at(Math.min(idx, s.n - 1), false);
  }

  function setChg(s) {
    if (!chgEl) return;
    chgEl.textContent = pct(s.chg) + ' over ' + ({ '1d': 'the last 24 hours', '7d': 'the last 7 days', '1m': 'the last month', '1y': 'the last year' }[s.r]);
    chgEl.setAttribute('data-dir', s.dir);
  }
  /* where each average really starts, under the 1Y chart only, and only when it starts after the window's first day */
  function setNote(s) {
    if (!maNote) return;
    var bits = [];
    if (s.r === '1y') {
      [['50', s.ma50], ['200', s.ma200]].forEach(function (pair) {
        var m = pair[1], k = 0;
        if (!m) return;
        while (k < m.length && m[k] === null) k++;
        if (k > 0 && k < m.length) bits.push(pair[0] + '-day average from ' +
          fmtDate(s.t[k], { month: 'short', day: 'numeric' }, true) + ' (needs ' + pair[0] + ' days of history)');
      });
    }
    maNote.textContent = bits.join(' \u00b7 ');
    maNote.hidden = !bits.length;
  }
  function setCap(s, raw) {
    if (!cap) return;
    var r = RANGES[s.r], vmax = 0, i;
    for (i = 0; i < s.n; i++) if (s.v[i] !== null && s.v[i] > vmax) vmax = s.v[i];
    var t = 'CoinGecko, ' + r.spacing + ' points (' + s.n + '). Times are Eastern. ';
    if (DAILY[s.r] && vmax) t += 'Volume bars are each day\u2019s volume, scale 0 to ' + compact(vmax) + '. ';
    if (s.ma50 || s.ma200) {
      t += 'Dashed lines are averages of daily closes';
      if (s.ma50) t += ', 50-day ' + money(s.ma50[s.n - 1], 0);
      if (s.ma200) t += ', 200-day ' + money(s.ma200[s.n - 1], 0);
      t += '. ';
    }
    t += 'Read ' + fmtDate(Date.now(), { hour: 'numeric', minute: '2-digit' }) + ' ET.';
    cap.textContent = t;
  }

  /* ---- the crosshair ---- */
  function at(i, announce) {
    if (!G.s) return;
    i = Math.max(0, Math.min(G.s.n - 1, i)); idx = i;
    var s = G.s, p = G.pts[i];
    var cr = G.svg.querySelector('.cc-cross'), dot = G.svg.querySelector('.cc-cdot');
    cr.setAttribute('x1', p[0]); cr.setAttribute('x2', p[0]); cr.style.display = '';
    dot.setAttribute('cx', p[0]); dot.setAttribute('cy', p[1]); dot.style.display = '';
    var t = '<b>' + money(s.y[i]) + '</b><span>' + readDate(s.t[i], s.r) + '</span>' +
      (DAILY[s.r] && s.v[i] !== null ? '<span>Vol ' + compact(s.v[i]) + '</span>' : '');
    readout.innerHTML = t; readout.hidden = false;
    /* beside the finger, never under it, and always inside the box */
    var rw = readout.offsetWidth, bw = box.clientWidth;
    var left = p[0] > bw / 2 ? 8 : bw - rw - 8;
    readout.style.left = Math.max(0, Math.min(bw - rw, left)) + 'px';
    readout.style.top = '6px';
  }
  function fromEvent(ev) {
    if (!G.s) return;
    var b = G.svg.getBoundingClientRect();
    var x = (ev.clientX - b.left) * (G.W / (b.width || G.W));
    var tt = G.s.t[0] + (x - G.L) / G.PW * (G.s.t[G.s.n - 1] - G.s.t[0]);
    var lo = 0, hi = G.s.n - 1;
    while (hi - lo > 1) { var mid = (lo + hi) >> 1; if (G.s.t[mid] < tt) lo = mid; else hi = mid; }
    at(Math.abs(G.s.t[lo] - tt) <= Math.abs(G.s.t[hi] - tt) ? lo : hi);
  }
  function hide() {
    idx = -1; readout.hidden = true;
    if (G.svg) {
      var cr = G.svg.querySelector('.cc-cross'), dot = G.svg.querySelector('.cc-cdot');
      if (cr) cr.style.display = 'none'; if (dot) dot.style.display = 'none';
    }
  }
  box.addEventListener('pointerdown', fromEvent);
  box.addEventListener('pointermove', fromEvent);
  box.addEventListener('pointerleave', function (ev) { if (ev.pointerType === 'mouse') hide(); });
  box.addEventListener('focus', function () { if (idx < 0 && G.s) at(G.s.n - 1); });
  box.addEventListener('blur', hide);
  box.addEventListener('keydown', function (ev) {
    if (!G.s) return;
    var k = ev.key, big = ev.shiftKey ? 10 : 1, n = idx < 0 ? G.s.n - 1 : idx;
    if (k === 'ArrowLeft') n -= big; else if (k === 'ArrowRight') n += big;
    else if (k === 'Home') n = 0; else if (k === 'End') n = G.s.n - 1;
    else if (k === 'Escape') { hide(); return; } else return;
    ev.preventDefault(); at(n);
  });

  /* ---- tabs ---- */
  function mark(r) {
    tabs.forEach(function (b) {
      var on = b.getAttribute('data-range') === r;
      b.setAttribute('aria-selected', on ? 'true' : 'false');
      b.tabIndex = on ? 0 : -1;
    });
  }
  function show(r) {
    var mine = ++seq;
    cur = r; mark(r);
    load(RANGES[r].fetch).then(function (raw) {
      if (mine !== seq) return;
      var s = build(r, raw);
      if (s.n < 3) throw new Error('short');
      shown = s; hide(); draw(s); setChg(s); setCap(s, raw); setNote(s);
      wrap.setAttribute('data-range', r);
      wrap.removeAttribute('data-failed');
    })['catch'](function () {
      if (mine !== seq) return;
      wrap.setAttribute('data-failed', r);
      if (cap && !shown) cap.textContent = 'The live history did not load, so this is the build’s seven-day line. Choose a window to try again.';
      else if (cap) cap.textContent = 'This window did not load from CoinGecko; the chart above is the last one that did. Choose it again to retry.';
    });
  }
  tabs.forEach(function (b) {
    b.addEventListener('click', function () { show(b.getAttribute('data-range')); });
    b.addEventListener('keydown', function (ev) {
      var i = tabs.indexOf(b), n = ev.key === 'ArrowRight' ? i + 1 : ev.key === 'ArrowLeft' ? i - 1 : -1;
      if (n < 0 || n >= tabs.length) return;
      ev.preventDefault(); tabs[n].focus(); show(tabs[n].getAttribute('data-range'));
    });
  });
  if (tablist) tablist.hidden = false;         /* the tabs are for the script; without it the build's line stands */
  mark(cur);

  /* redraw when the width changes (rotation, the keyboard, a resize); the window stays chosen */
  var rt = 0, lastW = stage.clientWidth;
  function resized() {
    clearTimeout(rt);
    rt = setTimeout(function () {
      var w = stage.clientWidth;
      if (shown && Math.abs(w - lastW) >= 2) { lastW = w; draw(shown); }
    }, 120);
  }
  if (window.ResizeObserver) new ResizeObserver(resized).observe(stage); else window.addEventListener('resize', resized);

  show(cur);
})();
