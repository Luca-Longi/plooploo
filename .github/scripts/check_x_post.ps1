$ErrorActionPreference = 'Stop'
$repository = 'Luca-Longi/plooploo'
$gh = Join-Path $env:ProgramFiles 'GitHub CLI\gh.exe'

# Read live state so a stale local checkout cannot trigger yesterday's piece.
$rawLog = & $gh api "repos/$repository/contents/render_log.json" -H 'Accept: application/vnd.github.raw+json'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$render = ($rawLog -join "`n") | ConvertFrom-Json
$postedNumber = $render.last_tweeted
if ($postedNumber -is [pscustomobject]) { $postedNumber = $postedNumber.video }
if ($postedNumber -eq $render.video_count) { exit 0 }
if ([DateTimeOffset]::UtcNow -ge ([DateTimeOffset]::Parse($render.last_render)).AddHours(24)) {
    exit 0
}

# The workflow enforces the rotating target time, freshness and duplicate checks.
& $gh workflow run tweet.yml --repo $repository --ref main
exit $LASTEXITCODE
