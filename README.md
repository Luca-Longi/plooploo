# plooploo
p loop loo

Configure the renderer PC's Windows task `PlooplooXPostingCheck` to check every
30 minutes using `.github/scripts/check_x_post.ps1`. It reads the live posting record and
requests a GitHub Actions run for an unpublished current render. It uses the
existing GitHub CLI login, so X credentials stay in GitHub secrets.
The task requires the Windows user to be logged in and the PC awake and online.
Missed checks resume when the PC is available.
Use `-CheckOnly` to verify the live state without requesting a publishing run.

GitHub's scheduled checks at :07 and :37 and new-render pushes provide additional
triggers. All triggers use the same serialized publishing workflow.
Each piece keeps its rotating target hour in Central European local time
(CET/CEST, the same time as Rome), between 04:00 and 18:00. The first run after that hour publishes;
later runs skip pieces already recorded in `render_log.json`.

Checks run before publishing dependencies are installed. GitHub may delay or
miss scheduled runs, so later checks can catch up after midnight while the
same render is still current and less than 24 hours old. The workflow checks
the latest render on `main` again just before publishing. Posting
runs are serialized to prevent overlapping workflows from publishing the same
piece.

To publish early, run **Tweet Daily Render** manually with `force` enabled.
This bypasses the target hour for the current render within its 24-hour window
and still skips a piece already recorded as posted.
Posts made directly on X are not detected automatically.

After X returns a post ID, the workflow saves a receipt artifact and retries
saving the posting record against the latest `main`. Concurrent render updates
are preserved. If all save attempts fail, recover `tweet_receipt.json` from the
run's artifact and save its `last_tweeted` record before retrying publication.
An X timeout may leave the outcome unknown. Check the account before manually
retrying such a failure.
