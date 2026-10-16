/* THE STALE STATE (Sprint 9.1, AUDIT.md 3.4 item 2). Every reading that carries data-asof (a UTC
   instant) is measured against the clock at the moment the page is READ, not the moment it was
   built. Older than its window (data-asof-hours, default 3) it prints its age beside its stamp
   and its figure dims. No storage, no network, no library. A page that never runs this
   still carries the build's own statement of age. */
(function () {
  'use strict';
  var now = Date.now();
  var els = document.querySelectorAll('[data-asof]');
  for (var i = 0; i < els.length; i++) {
    var el = els[i];
    var t = Date.parse(el.getAttribute('data-asof'));
    if (isNaN(t)) continue;
    var h = (now - t) / 36e5;
    var w = parseFloat(el.getAttribute('data-asof-hours')) || 3;
    if (h <= w) continue;
    var age = h < 48 ? Math.floor(h) + ' hours ago' : Math.floor(h / 24) + ' days ago';
    el.classList.add('is-stale');
    var host = el.querySelector('.tl-src, .mh-lt') || el;
    if (!host.querySelector('.asof-age')) {
      var s = document.createElement('span');
      s.className = 'asof-age';
      s.textContent = (host === el && el.classList.contains('mkt-asof') ? ', ' : ' · ') + age;
      host.appendChild(s);
    }
  }
  /* A transfer's "Nh ago" is true at the instant the page was built. data-ago carries the move's
     epoch seconds; the label is rewritten from the clock now, and a move older than 24 hours (the
     window Whale Watch claims) dims its row, whatever the build said. */
  var ago = document.querySelectorAll('[data-ago]');
  for (var k = 0; k < ago.length; k++) {
    var t0 = parseInt(ago[k].getAttribute('data-ago'), 10) * 1000;
    if (isNaN(t0) || t0 > now) continue;
    var hh = Math.floor((now - t0) / 36e5);
    ago[k].textContent = ' \u00b7 ' + (hh < 1 ? 'latest' : hh + 'h ago');
    if (hh > 24) {
      var row = ago[k].closest('tr');
      if (row) row.classList.add('is-stale');
      ago[k].textContent += ', outside the 24-hour window';
    }
  }
})();
