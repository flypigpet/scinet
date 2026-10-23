param([string]$Workspace = $PSScriptRoot, [string]$Model, [switch]$ComputeOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Please create .venv and install requirements.txt first; see README.md.' }
if ($Model -and -not $ComputeOnly) { & $pythonExe -m scinet --workspace $Workspace run --ai --model $Model }
else { & $pythonExe -m scinet --workspace $Workspace run }
if ($LASTEXITCODE -ne 0) { throw 'Run failed. Retained evidence and logs are in output/. No successful review is implied.' }
