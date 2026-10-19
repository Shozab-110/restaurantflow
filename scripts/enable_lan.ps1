$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Set up the local Python environment first. See docs/GETTING_STARTED.md.' }
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'))
    $elevated = Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -Verb RunAs -WindowStyle Hidden -Wait -PassThru
    if ($elevated.ExitCode -ne 0) { throw 'Windows did not enable LAN access. Approve the administrator prompt, or ask the PC administrator.' }
    Write-Host 'LAN access enabled. Start Offline Demo.cmd and use the displayed Wi-Fi address.'
    exit 0
}
$basePython = (& $python -c 'import sys; print(sys._base_executable)').Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $basePython)) { throw 'Could not identify the Python interpreter.' }
$ruleName = 'RestaurantFlow-Offline-Demo-8001'
$rule = Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
if ($rule) {
    $rule | Set-NetFirewallRule -Enabled True -Direction Inbound -Action Allow -Profile Private,Public
    $rule | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -Protocol TCP -LocalPort 8001
    $rule | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress LocalSubnet
    $rule | Get-NetFirewallApplicationFilter | Set-NetFirewallApplicationFilter -Program $basePython
} else {
    New-NetFirewallRule -Name $ruleName -DisplayName 'RestaurantFlow offline LAN demo (8001)' `
        -Description 'Python demo server, TCP 8001, local-subnet devices only. No database port is opened.' `
        -Enabled True -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8001 `
        -RemoteAddress LocalSubnet -Profile Private,Public -Program $basePython | Out-Null
}
