#requires -Version 5.1
Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Helper = Join-Path $Root "extensions\ams-runtime-observation\tools\Inspect-AgentRuntime.ps1"
$Temp = Join-Path ([IO.Path]::GetTempPath()) ("ams-observation-" + [Guid]::NewGuid().ToString("N"))
$Id = "11111111-1111-7111-8111-111111111111"
function Write-Rollout([string]$Path) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
    @(
        '{"type":"response_item","payload":{"prompt":"DO_NOT_LEAK"}}',
        '{"type":"session_meta","payload":{"id":"11111111-1111-7111-8111-111111111111","parent_thread_id":"00000000-0000-7000-8000-000000000000","agent_role":"ams_terra_high","agent_path":"/root/a","model_provider":"openai"}}',
        '{"type":"turn_context","payload":{"model":"gpt-5.6-terra","effort":"high","sandbox_policy":{"type":"danger-full-access"},"permission_profile":{"type":"disabled"},"cwd":"/fixture"}}'
    ) | Set-Content -LiteralPath $Path -Encoding UTF8
}
function Invoke-ExpectedFailure([string]$ThreadId) {
    $PreviousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Helper -ThreadId $ThreadId -SessionsDir $Temp 2>$null | Out-Null
        return $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $PreviousPreference }
}
try {
    New-Item -ItemType Directory -Force -Path $Temp | Out-Null
    $Rollout = Join-Path $Temp "2026\08\03\rollout-x-$Id.jsonl"
    Write-Rollout $Rollout
    $HelperSource = Get-Content -LiteralPath $Helper -Raw
    foreach ($Required in @('OpenDirectory','GetFinalPathNameByHandle','FinalPath','Test-PathWithin')) {
        if ($HelperSource -notmatch [regex]::Escape($Required)) { throw "helper containment contract is missing $Required" }
    }

    $Output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Helper -ThreadId $Id -SessionsDir $Temp
    if ($LASTEXITCODE -ne 0) { throw "valid helper invocation failed" }
    if ($Output -match "DO_NOT_LEAK") { throw "helper leaked prompt data" }
    $Data = $Output | ConvertFrom-Json
    if ($Data.model -cne "gpt-5.6-terra" -or $Data.effort -cne "high") { throw "wrong routing evidence" }

    Write-Rollout (Join-Path $Temp "2026\08\04\rollout-y-$Id.jsonl")
    if ((Invoke-ExpectedFailure -ThreadId $Id) -eq 0) { throw "duplicate rollout was accepted" }
    if ((Invoke-ExpectedFailure -ThreadId "invalid") -eq 0) { throw "invalid id was accepted" }
    Write-Host "PASS: PowerShell runtime observation fixtures"
}
finally { Remove-Item -LiteralPath $Temp -Recurse -Force -ErrorAction SilentlyContinue }

exit 0
