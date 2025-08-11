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
  [string] $DemoUrl = "https://unreal-demo.b-cdn.net/WindowsDemo.zip"
)

$ErrorActionPreference = 'Stop'

function Ensure-Directory {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Path $Path | Out-Null
  }
}

Write-Host "Installing OBS Studio..."
$obsExe = "C:\\Program Files\\obs-studio\\bin\\64bit\\obs64.exe"

# Try winget first
try {
  $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
  if ($wingetCmd) {
    winget install -e --id OBSProject.OBSStudio --accept-package-agreements --accept-source-agreements | Out-Null
  } else {
    throw "winget not found"
  }
} catch {
  $installer = Join-Path $env:TEMP "OBS-Studio-Installer.exe"
  Invoke-WebRequest -Uri "https://github.com/obsproject/obs-studio/releases/latest/download/OBS-Studio-Full-Installer-x64.exe" -OutFile $installer
  Start-Process -FilePath $installer -ArgumentList "/S" -Wait
  Remove-Item $installer -Force -ErrorAction SilentlyContinue
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
  Invoke-WebRequest -Uri $DemoUrl -OutFile $downloadOut
  Write-Host "Downloaded: $downloadOut"
} catch {
  Write-Warning "Failed to download demo: $($_.Exception.Message)"
}

# Launch OBS with our collection and scene
Write-Host "Starting OBS..."
Start-Process -FilePath $obsExe -ArgumentList @("--collection", "$CollectionName", "--scene", "$SceneName")
Write-Host "OBS launched with collection '$CollectionName' and scene '$SceneName' (source '$SourceName')."


