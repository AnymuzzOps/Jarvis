# Compatible con Windows PowerShell 5.1.
[CmdletBinding()]
param(
    [switch]$InstallWhisper,
    [switch]$DownloadVoiceModels,
    [switch]$PullOllamaModel,
    [ValidateSet('qwen3:0.6b', 'qwen3:1.7b', 'qwen3:4b', 'qwen3:8b')]
    [string]$Model = 'qwen3:4b'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$data = Join-Path $env:LOCALAPPDATA 'Jarvis'
$models = Join-Path $data 'models'
$python = Join-Path $root '.venv\Scripts\python.exe'
$whisper = Join-Path $data 'whisper'
$whisperExe = Join-Path $whisper 'whisper-cli.exe'

function Assert-Success([string]$Operation) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation fallo (codigo $LASTEXITCODE)."
    }
}

function Receive-File([string]$Url, [string]$Target) {
    if ((Test-Path -LiteralPath $Target -PathType Leaf) -and (Get-Item -LiteralPath $Target).Length -gt 0) {
        return
    }
    $temporary = "$Target.$([guid]::NewGuid()).part"
    try {
        Write-Host "Descargando $Url"
        Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $temporary
        if ((Get-Item -LiteralPath $temporary).Length -eq 0) {
            throw "La descarga esta vacia: $Url"
        }
        Move-Item -LiteralPath $temporary -Destination $Target -Force
    } finally {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }
}

if ([Environment]::OSVersion.Version.Major -lt 10) {
    throw 'Se requiere Windows 10 u 11.'
}
if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) {
    throw 'Instala Python 3.12 x64 con el Python Launcher desde https://www.python.org/downloads/windows/.'
}
& py.exe -3.12 -c "import platform,sys; sys.exit(not (sys.version_info[:2] == (3,12) and platform.machine().upper() in ('AMD64','X86_64')))"
Assert-Success 'Validacion de Python 3.12 x64'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    & py.exe -3.12 -m venv (Join-Path $root '.venv')
    Assert-Success 'Creacion del entorno virtual'
}
& $python -c "import platform,sys; sys.exit(not (sys.version_info[:2] == (3,12) and platform.machine().upper() in ('AMD64','X86_64')))"
Assert-Success 'Validacion del entorno virtual .venv'
& $python -m pip install -e "${root}[test]"
Assert-Success 'Instalacion de las dependencias'

$ollama = Get-Command ollama.exe -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Warning 'Instala Ollama desde https://ollama.com/download/windows y vuelve a abrir PowerShell.'
}
New-Item -ItemType Directory -Force -Path $models | Out-Null

if ($InstallWhisper -and -not (Test-Path -LiteralPath $whisperExe -PathType Leaf)) {
    $stage = Join-Path $data ([guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $stage | Out-Null
    try {
        $zip = Join-Path $stage 'whisper.zip'
        $expanded = Join-Path $stage 'expanded'
        Receive-File 'https://github.com/ggml-org/whisper.cpp/releases/download/v1.8.2/whisper-bin-x64.zip' $zip
        Expand-Archive -LiteralPath $zip -DestinationPath $expanded
        $cli = Get-ChildItem -LiteralPath $expanded -Recurse -Filter 'whisper-cli.exe' -File | Select-Object -First 1
        if (-not $cli) {
            throw 'El ZIP oficial no contiene whisper-cli.exe.'
        }
        New-Item -ItemType Directory -Path $whisper -Force | Out-Null
        Get-ChildItem -LiteralPath $cli.DirectoryName | Copy-Item -Destination $whisper -Force -Recurse
        if (-not (Test-Path -LiteralPath $whisperExe -PathType Leaf)) {
            throw 'No se encontro whisper-cli.exe tras la instalacion.'
        }
    } finally {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}

if ($DownloadVoiceModels) {
    Receive-File 'https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin' (Join-Path $models 'ggml-base.bin')
    $voiceUrl = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium'
    foreach ($file in @('es_ES-sharvard-medium.onnx', 'es_ES-sharvard-medium.onnx.json')) {
        Receive-File "$voiceUrl/$file" (Join-Path $models $file)
    }
}

if ($PullOllamaModel) {
    if (-not $ollama) { throw 'Instala Ollama antes de descargar el modelo.' }
    $env:OLLAMA_HOST = '127.0.0.1:11434'
    & $ollama.Source pull $Model
    Assert-Success 'Descarga del modelo de Ollama'
} else {
    Write-Host "Con Ollama abierto, puedes descargar el modelo ejecutando: ollama pull $Model"
}
if ($Model -ne 'qwen3:4b') {
    Write-Host "Selecciona $Model en Configuracion de JARVIS."
}
Write-Host 'Ejecuta .\scripts\Test-JarvisSetup.ps1 para verificar los componentes.'
