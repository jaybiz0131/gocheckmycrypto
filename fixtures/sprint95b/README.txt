Sprint 9.5b baselines: Sprint 9.5's output, kept so the claim "nothing changes under 1280" is a byte comparison.
Made on Tuesday October 20, 2026 from the branch head 2453529 (Sprint 9.5, review 2 PASS), before any 9.5b change:
  home-board-card.95.html, home-board-nocard.95.html   scripts/sprint95b_fixture.py pages(), the recorded 15 October Board
                                                       (fixtures/why) with its recorded whale flows, with and without the verdict
                                                       it really grades; SITE_BUILD_NOW=2026-10-20T07:20:00Z
  site.95.css, system.95.css                           site/assets/site.css and system.css at 2453529, byte for byte
The ?v=<hash> on the asset links is the CSS content's hash and changes when the CSS does; the tests mask it on both sides.
Records are real (Jack, October 13); nothing here is synthetic.
