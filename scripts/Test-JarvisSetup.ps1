[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Ejecuta primero .\scripts\Setup-Jarvis.ps1.'
}
if (-not (Get-Command ollama.exe -ErrorAction SilentlyContinue)) {
    Write-Warning 'ollama.exe no esta en PATH. Se comprobara la API local igualmente.'
}
& $python -m jarvis.verify
if ($LASTEXITCODE -ne 0) {
    throw 'La configuracion de JARVIS tiene componentes pendientes. Revisa los mensajes anteriores.'
}
