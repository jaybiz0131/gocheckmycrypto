Sprint 9.5b baselines: Sprint 9.5's output, kept so the claim "nothing changes under 1280" is a byte comparison.
REBASELINED on Wednesday October 21, 2026 to Sprint 9.5 AS MERGED (main ca7ff70), replacing the October 20 set made at 2453529. Regenerated the
same way: git archive ca7ff70 into a clean directory, scripts/sprint95b_fixture.py pages() run in it with SITE_BUILD_NOW=2026-10-20T07:20:00Z, and
site/assets/site.css and system.css taken with git show ca7ff70:<path>. (Compared with the 2453529 set before replacing it: the CSS files and
both pages were identical apart from the build-commit meta, which the tests mask.)
The J-11 rules (j11-stamp.css, j11-nav.css) are the only additions the 375 render test allows to the 9.5 side.
Originally made from the branch head 2453529 (Sprint 9.5, review 2 PASS), before any 9.5b change:
  home-board-card.95.html, home-board-nocard.95.html   scripts/sprint95b_fixture.py pages(), the recorded 15 October Board
                                                       (fixtures/why) with its recorded whale flows, with and without the verdict
                                                       it really grades; SITE_BUILD_NOW=2026-10-20T07:20:00Z
  site.95.css, system.95.css                           site/assets/site.css and system.css at 2453529, byte for byte
The ?v=<hash> on the asset links is the CSS content's hash and changes when the CSS does; the tests mask it on both sides.
Records are real (Jack, October 13); nothing here is synthetic.
