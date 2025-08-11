<#
.SYNOPSIS
  Installs OBS Studio on Windows, creates a scene collection with a Media Source (named "gst")
  pointing to an RTMP endpoint for audio/video, starts OBS, and downloads a demo ZIP.

.USAGE
  Run in an elevated PowerShell:
    Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
    scripts\windows\setup_obs_rtmp.ps1 -RtmpUrl "rtmp://localhost:1935/live/mystream"

.PARAMETER RtmpUrl
  The RTMP input URL to use for the Media Source.

.NOTES
  - Uses winget when available; otherwise falls back to the official silent installer.
  - Writes a scene collection file under %APPDATA%\obs-studio\basic\scenes.
  - Creates collection "AutoRTMP" with scene "Scene" and source "gst".
  - Downloads Windows demo zip to the user's Downloads folder.
  - Compatible with modern OBS releases that support ffmpeg_source.
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory = $false)]
  [string] $RtmpUrl = "rtmp://localhost:1935/live/mystream",

  [Parameter(Mandatory = $false)]
  [string] $CollectionName = "AutoRTMP",

  [Parameter(Mandatory = $false)]
  [string] $SceneName = "Scene",

  [Parameter(Mandatory = $false)]
  [string] $SourceName = "gst",

  [Parameter(Mandatory = $false)]
  [string] $DemoUrl = "https://unreal-demo.b-cdn.net/WindowsDemo.zip",

  # Optional corporate proxy, e.g. http://proxy.corp:8080 or http://user:pass@proxy.corp:8080
  [Parameter(Mandatory = $false)]
  [string] $Proxy = $null,

  # Optional path to a pre-downloaded OBS installer .exe to skip network download
  [Parameter(Mandatory = $false)]
  [string] $InstallerPath = $null,

  # Reduce verbose network diagnostics
  [switch] $QuietNetwork
)

$ErrorActionPreference = 'Stop'

<#
  Ensure modern TLS and define a resilient downloader with retries and fallbacks.
#>

# Force-enable TLS 1.2+ where available
try {
  $currentProtocols = [System.Net.ServicePointManager]::SecurityProtocol
  if (-not $currentProtocols.HasFlag([System.Net.SecurityProtocolType]::Tls12)) {
    [System.Net.ServicePointManager]::SecurityProtocol = $currentProtocols -bor [System.Net.SecurityProtocolType]::Tls12
  }
  # Try to enable TLS 1.3 if the platform supports it
  try {
    $tls13 = [System.Net.SecurityProtocolType]::Tls13
    if (-not $currentProtocols.HasFlag($tls13)) {
      [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor $tls13
    }
  } catch { }
} catch { }

$global:SetupScriptUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) setup_obs_rtmp.ps1/1.0 PowerShell"

function Download-File {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)] [string] $Uri,
    [Parameter(Mandatory = $true)] [string] $Destination,
    [int] $MaxRetries = 4,
    [int] $DelaySeconds = 3,
    [string] $Proxy = $null,
    [switch] $Quiet
  )

  $headers = @{ 'User-Agent' = $global:SetupScriptUserAgent }

  # Primary: Invoke-WebRequest with retries
  for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
    try {
      $iwrParams = @{ Uri = $Uri; OutFile = $Destination; Headers = $headers; UseBasicParsing = $true; MaximumRedirection = 5; TimeoutSec = 300 }
      if ($Proxy) { $iwrParams['Proxy'] = $Proxy; $iwrParams['ProxyUseDefaultCredentials'] = $true }
      Invoke-WebRequest @iwrParams
      if (Test-Path -LiteralPath $Destination) { return }
    } catch {
      if (-not $Quiet) { Write-Verbose ("Invoke-WebRequest attempt {0} failed: {1}" -f $attempt, $_.Exception.Message) }
      if ($attempt -lt $MaxRetries) {
        Start-Sleep -Seconds $DelaySeconds
      }
    }
  }

  # Fallback 1: curl.exe if available
  try {
    $curlExe = (Get-Command curl.exe -ErrorAction SilentlyContinue).Path
    if ($curlExe) {
      $curlArgs = @('-L','--fail','--connect-timeout','20','--max-time','600','-A',$headers['User-Agent'],'-o',$Destination,$Uri)
      if ($Proxy) { $curlArgs = @('-x', $Proxy) + $curlArgs }
      & $curlExe @curlArgs | Out-Null
      if (Test-Path -LiteralPath $Destination) { return }
    }
  } catch { }

  # Fallback 2: BITS
  try {
    if ($Proxy) {
      Start-BitsTransfer -Source $Uri -Destination $Destination -DisplayName "Download $(Split-Path -Leaf $Destination)" -Description "Downloading $Uri" -ProxyUsage Override -ProxyList $Proxy -ErrorAction Stop
    } else {
      Start-BitsTransfer -Source $Uri -Destination $Destination -DisplayName "Download $(Split-Path -Leaf $Destination)" -Description "Downloading $Uri" -ErrorAction Stop
    }
    if (Test-Path -LiteralPath $Destination) { return }
  } catch { }

  throw "Failed to download $Uri to $Destination after retries and fallbacks."
}

function Test-ValidWindowsExecutable {
  [CmdletBinding()]
  param([Parameter(Mandatory = $true)] [string] $Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  try {
    $fileInfo = Get-Item -LiteralPath $Path -ErrorAction Stop
    if ($fileInfo.Length -lt 5242880) { return $false } # < 5 MB is suspicious for OBS installer
    $bytes = [byte[]](Get-Content -LiteralPath $Path -Encoding Byte -TotalCount 2)
    if ($bytes.Length -lt 2) { return $false }
    # 'MZ' header for PE executables
    return ($bytes[0] -eq 0x4D -and $bytes[1] -eq 0x5A)
  } catch { return $false }
}

function Get-ObsInstallerUrls {
  [CmdletBinding()]
  param()
  @(
    'https://github.com/obsproject/obs-studio/releases/latest/download/OBS-Studio-Full-Installer-x64.exe',
    'https://cdn-fastly.obsproject.com/downloads/OBS-Studio-Full-Installer-x64.exe',
    'https://cdn-fastly.obsproject.com/downloads/OBS-Studio-Installer-x64.exe'
  )
}

function Parse-ProxyUri {
  [CmdletBinding()]
  param([string] $Proxy)
  if (-not $Proxy) { return $null }
  try {
    $uri = [System.Uri]::new($Proxy)
    $hostPort = if ($uri.Port -gt 0) { "{0}:{1}" -f $uri.Host, $uri.Port } else { $uri.Host }
    $user = $null; $pass = $null
    if ($uri.UserInfo) {
      $parts = $uri.UserInfo.Split(':',2)
      if ($parts.Length -ge 1) { $user = $parts[0] }
      if ($parts.Length -ge 2) { $pass = $parts[1] }
    }
    return [PSCustomObject]@{ HostPort = $hostPort; User = $user; Password = $pass }
  } catch { return $null }
}

function Ensure-Chocolatey {
  [CmdletBinding()]
  param([string] $Proxy)

  $choco = Get-Command choco.exe -ErrorAction SilentlyContinue
  if ($choco) { return }

  $installPs1 = Join-Path $env:TEMP "choco-install.ps1"
  $installUrl = 'https://community.chocolatey.org/install.ps1'
  Write-Host "Installing Chocolatey..."

  # Provide proxy to the bootstrapping process via environment variables
  if ($Proxy) {
    $parsed = Parse-ProxyUri -Proxy $Proxy
    $env:ChocolateyProxyLocation = $Proxy
    if ($parsed -and $parsed.User) { $env:ChocolateyProxyUserName = $parsed.User }
    if ($parsed -and $parsed.Password) { $env:ChocolateyProxyPassword = $parsed.Password }
  }

  Download-File -Uri $installUrl -Destination $installPs1 -Proxy $Proxy -Quiet
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installPs1 | Out-Null
  Remove-Item -LiteralPath $installPs1 -Force -ErrorAction SilentlyContinue

  $choco = Get-Command choco.exe -ErrorAction SilentlyContinue
  if (-not $choco) {
    $defaultChoco = 'C:\ProgramData\chocolatey\bin\choco.exe'
    if (Test-Path -LiteralPath $defaultChoco) {
      $env:PATH = ("{0};{1}" -f (Split-Path -Parent $defaultChoco), $env:PATH)
      return
    }
    throw "Chocolatey installation failed or choco.exe not found in PATH."
  }

  # Configure proxy in Chocolatey for future operations
  if ($Proxy) {
    $parsed = Parse-ProxyUri -Proxy $Proxy
    $hostPort = if ($parsed) { $parsed.HostPort } else { $null }
    $chocoExe = $choco.Path
    if ($hostPort) { & $chocoExe config set proxy $hostPort | Out-Null }
    if ($parsed -and $parsed.User) { & $chocoExe config set proxyUser $parsed.User | Out-Null }
    if ($parsed -and $parsed.Password) { & $chocoExe config set proxyPassword $parsed.Password | Out-Null }
  }
}

function Get-Url-Diagnostics {
  [CmdletBinding()] param([string] $Uri, [string] $Proxy = $null)
  try {
    $iwrParams = @{ Uri = $Uri; Method = 'Head'; UseBasicParsing = $true; MaximumRedirection = 5; TimeoutSec = 60 }
    if ($Proxy) { $iwrParams['Proxy'] = $Proxy; $iwrParams['ProxyUseDefaultCredentials'] = $true }
    $resp = Invoke-WebRequest @iwrParams
    return [PSCustomObject]@{ StatusCode = $resp.StatusCode; ContentLength = $resp.Headers['Content-Length']; Location = $resp.Headers['Location']; Server = $resp.Headers['Server'] }
  } catch {
    return [PSCustomObject]@{ Error = $_.Exception.Message }
  }
}

function Ensure-Directory {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path | Out-Null
  }
}

Write-Host "Installing OBS Studio..."
$obsExe = "C:\\Program Files\\obs-studio\\bin\\64bit\\obs64.exe"

# Preferred path: install via Chocolatey (auto-install choco if missing)
Ensure-Chocolatey -Proxy $Proxy
try {
  $chocoCmd = Get-Command choco.exe -ErrorAction Stop
  $chocoExe = $chocoCmd.Path
} catch {
  $fallbackChoco = 'C:\ProgramData\chocolatey\bin\choco.exe'
  if (Test-Path -LiteralPath $fallbackChoco) {
    $env:PATH = ("{0};{1}" -f (Split-Path -Parent $fallbackChoco), $env:PATH)
    $chocoExe = $fallbackChoco
  } else {
    throw "Chocolatey was installed but choco.exe is not available in PATH or default location."
  }
}

# Try obs-studio.install first, fallback to obs-studio if needed
$installSucceeded = $false
foreach ($pkg in @('obs-studio.install','obs-studio')) {
  Write-Host ("Installing {0} via Chocolatey..." -f $pkg)
  $args = @('install', $pkg, '-y', '--no-progress')
  $process = Start-Process -FilePath $chocoExe -ArgumentList $args -Wait -PassThru -WindowStyle Hidden
  if ($process.ExitCode -in @(0, 3010, 1641)) { $installSucceeded = $true; break }
  Write-Warning ("Chocolatey failed to install {0} (exit code {1})." -f $pkg, $process.ExitCode)
}

if (-not $installSucceeded) {
  throw "Chocolatey failed to install OBS. Please check network/proxy access to Chocolatey and the OBS CDN, or run manually: 'choco install obs-studio.install -y'."
}



if (-not (Test-Path -LiteralPath $obsExe)) {
  throw "OBS executable not found at $obsExe after installation."
}

# Ensure OBS is not running to avoid overwriting our scene
Get-Process obs64 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

# Prepare scene collection JSON
$scenesDir = Join-Path $env:APPDATA "obs-studio\basic\scenes"
Ensure-Directory $scenesDir
$scenePath = Join-Path $scenesDir ("{0}.json" -f $CollectionName)

$sceneJson = @"
{
  "name": "$CollectionName",
  "current_scene": "$SceneName",
  "scene_order": [
    { "name": "$SceneName" }
  ],
  "sources": [
    {
      "name": "$SceneName",
      "type": "scene",
      "settings": {
        "id_counter": 1,
        "items": [
          {
            "name": "$SourceName",
            "id": 1,
            "visible": true,
            "locked": false,
            "alignment": 5,
            "bounds_type": 0,
            "bounds_alignment": 0,
            "bounds": { "x": 0.0, "y": 0.0 },
            "crop": { "left": 0, "top": 0, "right": 0, "bottom": 0 },
            "pos": { "x": 0.0, "y": 0.0 },
            "rot": 0.0,
            "scale": { "x": 1.0, "y": 1.0 }
          }
        ]
      }
    },
    {
      "name": "$SourceName",
      "type": "ffmpeg_source",
      "settings": {
        "is_local_file": false,
        "input": "$RtmpUrl",
        "input_format": "",
        "hw_decode": true,
        "restart_on_activate": true,
        "buffering_mb": 2,
        "reconnect_delay_sec": 10,
        "clear_on_media_end": false,
        "close_when_inactive": false
      }
    }
  ]
}
"@

Set-Content -Path $scenePath -Value $sceneJson -Encoding UTF8
Write-Host "Scene collection written to $scenePath"

# Download demo zip
try {
  $downloadOut = Join-Path $env:USERPROFILE "Downloads\WindowsDemo.zip"
  Write-Host "Downloading demo: $DemoUrl -> $downloadOut"
  Download-File -Uri $DemoUrl -Destination $downloadOut -Proxy $Proxy -Quiet:$QuietNetwork
  Write-Host "Downloaded: $downloadOut"
} catch {
  Write-Warning "Failed to download demo: $($_.Exception.Message)"
}

# Launch OBS with our collection and scene
Write-Host "Starting OBS..."
Start-Process -FilePath $obsExe -ArgumentList @("--collection", "$CollectionName", "--scene", "$SceneName")
Write-Host "OBS launched with collection '$CollectionName' and scene '$SceneName' (source '$SourceName')."


