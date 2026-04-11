param([string]$Token)
if (-not $Token) { $Token = Read-Host "Paste your GitHub token" }

$Repo  = "mojolists/mojolists.github.io"
$Root  = Split-Path $MyInvocation.MyCommand.Path
$Files = @(
    "scripts/scrape_venues.py",
    "scripts/venues.json",
    ".github/workflows/scrape-shows.yml",
    ".github/workflows/ticketmaster-shows.yml",
    ".github/workflows/deploy.yml"
)
$Headers = @{
    Authorization = "token $Token"
    Accept        = "application/vnd.github.v3+json"
}

Write-Host "`nPushing $($Files.Count) files to $Repo ...`n"
foreach ($rel in $Files) {
    $path    = Join-Path $Root ($rel -replace "/","\\")
    $bytes   = [System.IO.File]::ReadAllBytes($path)
    $b64     = [Convert]::ToBase64String($bytes)
    $apiUrl  = "https://api.github.com/repos/$Repo/contents/$rel"

    # get current SHA
    $sha = $null
    try {
        $existing = Invoke-RestMethod -Uri $apiUrl -Headers $Headers -Method Get
        $sha = $existing.sha
    } catch {}

    $body = @{ message = "feat: update $rel (scraper rewrite)"; content = $b64 }
    if ($sha) { $body.sha = $sha }

    Invoke-RestMethod -Uri $apiUrl -Headers $Headers -Method Put `
        -ContentType "application/json" -Body ($body | ConvertTo-Json) | Out-Null
    Write-Host "  v  $rel"
}

Write-Host "`nDone! Now go trigger the workflow:"
Write-Host "https://github.com/mojolists/mojolists.github.io/actions`n"
