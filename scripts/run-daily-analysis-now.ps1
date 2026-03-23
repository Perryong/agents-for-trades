param(
    [string]$Ticker = ""
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    & git @Args
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$triggerFile = ".github/daily-analysis-trigger.txt"
$timestampUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$lines = @(
    "triggered_at_utc=$timestampUtc"
)

if (-not [string]::IsNullOrWhiteSpace($Ticker)) {
    $lines += "ticker=$($Ticker.Trim().ToUpperInvariant())"
}

Set-Content -Path $triggerFile -Value $lines -Encoding utf8

Invoke-Git -Args @("add", $triggerFile, ".github/workflows/daily-analysis.yml", "scripts/run-daily-analysis-now.ps1")

$commitMessage = "chore: trigger daily analysis now"
if (-not [string]::IsNullOrWhiteSpace($Ticker)) {
    $commitMessage = "$commitMessage ($($Ticker.Trim().ToUpperInvariant()))"
}

Invoke-Git -Args @("commit", "-m", $commitMessage)

Invoke-Git -Args @("push", "origin", "HEAD")

Write-Host "Pushed trigger commit. GitHub Actions should start shortly."
