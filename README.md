# plooploo
p loop loo

Daily X posts run on GitHub Actions, with checks at :07 and :37 every hour.
Each piece keeps its rotating target hour in Central European local time
(CET/CEST, the same time as Rome). The first run after that hour publishes;
later runs skip pieces already recorded in `render_log.json`.

Checks run before publishing dependencies are installed. GitHub may delay or
miss scheduled runs, so later checks can catch up. Posting runs are serialized
to prevent overlapping workflows from publishing the same piece.

To publish early, run **Tweet Daily Render** manually with `force` enabled.
This bypasses the target hour but still skips a piece already recorded as posted.
Posts made directly on X are not detected automatically.
