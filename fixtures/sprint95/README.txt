urls_main.txt: the structural pages and files the site built at main a3984cc (Sprint 9.4 merged, October 20, 2026):
every top-level page, every Board and Learn page, the four coin pages the tests read (btc, eth, sol, xrp), /today/,
the sitemaps, the feed, the redirects file and the four assets the pages load by name. Taken from a throwaway build
of that tree (the stories, the og images, the edition and coverage pages, the dated /today/ and /why/ pages are
content, not structure, and move with the data). sprint95_test.py --tree fails when any of these is not built
(no URL removed or changed). New pages (corrections.html, bottom-line/<YYYY-MM>.html) are additions.
