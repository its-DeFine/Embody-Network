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
  - Creates collection "AutoRTMP" with scene "Vtuber" and source "gst".
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
  [string] $SceneName = "Vtuber",

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
  [switch] $QuietNetwork,

  # Force reinstall even if OBS is already present
  [switch] $ForceInstall,

  # Skip demo zip download entirely
  [switch] $SkipDemo,

  # Force re-download of the demo zip even if it exists
  [switch] $ForceDownloadDemo,

  # Where to extract and run the demo (default: user's Desktop)
  [Parameter(Mandatory = $false)]
  [string] $DemoExtractDir = $null
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

# Runtime deps we can ensure if missing
$global:RuntimeDependencies = @(
  @{ Name = 'vcredist140'; Choco = 'vcredist140' },
  @{ Name = 'directx'; Choco = 'directx' }
)

function Get-DownloadsPath {
  [CmdletBinding()]
  param()
  try {
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
    $name = '{374DE290-123F-4565-9164-39C4925E467B}'
    $val = (Get-ItemProperty -LiteralPath $key -Name $name -ErrorAction Stop).$name
    $expanded = [Environment]::ExpandEnvironmentVariables($val)
    if ($expanded -and (Test-Path -LiteralPath $expanded)) { return $expanded }
  } catch { }
  $fallback = Join-Path $env:USERPROFILE 'Downloads'
  if (-not (Test-Path -LiteralPath $fallback)) { try { New-Item -ItemType Directory -Path $fallback | Out-Null } catch {} }
  return $fallback
}

function Get-DesktopPath {
  [CmdletBinding()]
  param()
  try {
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
    $val = (Get-ItemProperty -LiteralPath $key -Name 'Desktop' -ErrorAction Stop).Desktop
    $expanded = [Environment]::ExpandEnvironmentVariables($val)
    if ($expanded -and (Test-Path -LiteralPath $expanded)) { return $expanded }
  } catch { }
  $fallback = Join-Path $env:USERPROFILE 'Desktop'
  if (-not (Test-Path -LiteralPath $fallback)) { try { New-Item -ItemType Directory -Path $fallback | Out-Null } catch {} }
  return $fallback
}

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

function Test-ValidZip {
  [CmdletBinding()]
  param([Parameter(Mandatory = $true)] [string] $Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  try {
    $fileInfo = Get-Item -LiteralPath $Path -ErrorAction Stop
    if ($fileInfo.Length -lt 1048576) { return $false } # < 1 MB likely not a real demo zip
    $bytes = [byte[]](Get-Content -LiteralPath $Path -Encoding Byte -TotalCount 2)
    if ($bytes.Length -lt 2) { return $false }
    # 'PK' header for zip
    return ($bytes[0] -eq 0x50 -and $bytes[1] -eq 0x4B)
  } catch { return $false }
}

function Extract-ZipWithProgress {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)] [string] $ZipPath,
    [Parameter(Mandatory = $true)] [string] $Destination
  )
  try {
    Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem -ErrorAction SilentlyContinue | Out-Null
    
    # Get zip file size for progress tracking
    $zipFileInfo = Get-Item -LiteralPath $ZipPath
    $zipSizeMB = [Math]::Round($zipFileInfo.Length / 1MB, 2)
    Write-Host ("Starting extraction of {0} MB zip file..." -f $zipSizeMB)
    
    # Ensure destination exists
    if (-not (Test-Path -LiteralPath $Destination)) {
      New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    }
    
    $zip = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
      $total = $zip.Entries.Count
      $totalUncompressedSize = ($zip.Entries | Measure-Object -Property Length -Sum).Sum
      $totalUncompressedMB = [Math]::Round($totalUncompressedSize / 1MB, 2)
      $index = 0
      $extractedBytes = 0
      
      Write-Host ("Total files: {0}, Uncompressed size: {1} MB" -f $total, $totalUncompressedMB)
      
      # Check if zip has a single root folder
      $rootFolders = @{}
      foreach ($entry in $zip.Entries) {
        if ($entry.FullName -match '^([^/\\]+)[/\\]') {
          $rootFolders[$matches[1]] = $true
        }
      }
      $stripRoot = ($rootFolders.Count -eq 1)
      $rootName = if ($stripRoot) { $rootFolders.Keys | Select-Object -First 1 } else { $null }
      
      $lastProgressTime = [DateTime]::Now
      $progressInterval = [TimeSpan]::FromSeconds(1)
      
      foreach ($entry in $zip.Entries) {
        $index++
        
        # Strip the root folder if necessary
        $entryPath = $entry.FullName
        if ($stripRoot -and $rootName) {
          $pattern = "^" + [regex]::Escape($rootName) + "[/\\\\]?"
          $entryPath = $entryPath -replace $pattern, ""
          if ([string]::IsNullOrEmpty($entryPath)) { continue }
        }
        
        $targetPath = Join-Path $Destination $entryPath
        $targetDir = Split-Path -Parent $targetPath
        
        if (-not [string]::IsNullOrEmpty($targetDir) -and -not (Test-Path -LiteralPath $targetDir)) {
          New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        
        if ([string]::IsNullOrEmpty($entry.Name)) { continue } # directory entry
        
        # Update progress with MB info
        $extractedMB = [Math]::Round($extractedBytes / 1MB, 2)
        $percentComplete = if ($totalUncompressedSize -gt 0) { [int](($extractedBytes * 100.0) / $totalUncompressedSize) } else { 0 }
        
        # Only update progress every second to avoid console spam
        $currentTime = [DateTime]::Now
        if (($currentTime - $lastProgressTime) -ge $progressInterval -or $index -eq $total) {
          $statusMsg = "File {0}/{1} | {2:F1} MB / {3:F1} MB ({4}%)" -f $index, $total, $extractedMB, $totalUncompressedMB, $percentComplete
          Write-Progress -Activity "Extracting demo" -Status $statusMsg -PercentComplete $percentComplete
          $lastProgressTime = $currentTime
        }
        
        $inStream = $entry.Open()
        try {
          $outStream = [System.IO.File]::Open($targetPath, [System.IO.FileMode]::Create)
          try {
            $buffer = New-Object byte[] 131072  # Increased buffer size to 128KB for faster extraction
            $fileBytes = 0
            $startTime = [DateTime]::Now
            
            while (($read = $inStream.Read($buffer, 0, $buffer.Length)) -gt 0) {
              $outStream.Write($buffer, 0, $read)
              $fileBytes += $read
              $extractedBytes += $read
              
              # Check for timeout (if single file takes more than 30 seconds, warn)
              $elapsed = ([DateTime]::Now - $startTime).TotalSeconds
              if ($elapsed -gt 30 -and $fileBytes -gt 0) {
                $mbPerSec = [Math]::Round(($fileBytes / 1MB) / $elapsed, 2)
                Write-Verbose ("Extracting large file: {0} at {1} MB/s" -f $entry.Name, $mbPerSec)
                $startTime = [DateTime]::Now  # Reset timer
                $fileBytes = 0
              }
            }
          } finally { $outStream.Dispose() }
        } finally { $inStream.Dispose() }
      }
    } finally { $zip.Dispose() }
    
    Write-Progress -Activity "Extracting demo" -Completed
    Write-Host ("Extraction completed: {0:F1} MB extracted to {1}" -f ($extractedBytes / 1MB), $Destination)
    return $true
  } catch {
    Write-Warning ("Managed extraction failed: {0}" -f $_.Exception.Message)
    return $false
  }
}

function Extract-ZipFallbackExpandArchive {
  [CmdletBinding()] param([string] $ZipPath, [string] $Destination)
  try {
    # Get zip file size for progress tracking
    $zipFileInfo = Get-Item -LiteralPath $ZipPath
    $zipSizeMB = [Math]::Round($zipFileInfo.Length / 1MB, 2)
    Write-Host ("Fallback extraction of {0} MB zip file using Expand-Archive..." -f $zipSizeMB)
    
    # Use PowerShell's built-in Expand-Archive as fallback
    if (-not (Test-Path -LiteralPath $Destination)) {
      New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    }
    
    # First try: extract to temp and handle root folder
    $tempExtract = Join-Path $env:TEMP ("extract_" + [System.Guid]::NewGuid().ToString())
    
    Write-Host "Extracting to temporary location..."
    # Note: Expand-Archive doesn't provide progress, so we just show a message
    $extractStart = [DateTime]::Now
    Expand-Archive -Path $ZipPath -DestinationPath $tempExtract -Force
    $extractTime = ([DateTime]::Now - $extractStart).TotalSeconds
    Write-Host ("Extraction took {0:F1} seconds" -f $extractTime)
    
    # Check if there's a single root folder
    Write-Host "Organizing extracted files..."
    $items = Get-ChildItem -LiteralPath $tempExtract
    $totalItems = 0
    $movedItems = 0
    
    if ($items.Count -eq 1 -and $items[0].PSIsContainer) {
      # Move contents of single root folder to destination
      $sourceFolder = $items[0].FullName
      $filesToMove = Get-ChildItem -LiteralPath $sourceFolder -Recurse -File
      $totalItems = $filesToMove.Count
      
      Write-Host ("Moving {0} files from extracted content..." -f $totalItems)
      Get-ChildItem -LiteralPath $sourceFolder | ForEach-Object {
        Move-Item -Path $_.FullName -Destination $Destination -Force
        $movedItems++
        if ($movedItems % 100 -eq 0) {
          Write-Host ("Moved {0}/{1} items..." -f $movedItems, $totalItems)
        }
      }
    } else {
      # Move all items to destination
      $filesToMove = Get-ChildItem -LiteralPath $tempExtract -Recurse -File
      $totalItems = $filesToMove.Count
      
      Write-Host ("Moving {0} files from extracted content..." -f $totalItems)
      Get-ChildItem -LiteralPath $tempExtract | ForEach-Object {
        Move-Item -Path $_.FullName -Destination $Destination -Force
        $movedItems++
        if ($movedItems % 100 -eq 0) {
          Write-Host ("Moved {0}/{1} items..." -f $movedItems, $totalItems)
        }
      }
    }
    
    # Clean up temp folder
    Write-Host "Cleaning up temporary files..."
    Remove-Item -Recurse -Force $tempExtract -ErrorAction SilentlyContinue
    
    Write-Host ("Fallback extraction completed to {0}" -f $Destination)
    return $true
  } catch { 
    Write-Warning ("Expand-Archive fallback failed: {0}" -f $_.Exception.Message)
    return $false 
  }
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

function Find-ObsExecutable {
  [CmdletBinding()] param()
  $candidates = @(
    (Join-Path ${env:ProgramFiles} 'obs-studio\bin\64bit\obs64.exe'),
    'C:\\Program Files\\obs-studio\\bin\\64bit\\obs64.exe',
    'C:\\Program Files (x86)\\obs-studio\\bin\\64bit\\obs64.exe'
  )
  foreach ($path in $candidates) {
    if ($path -and (Test-Path -LiteralPath $path)) { return $path }
  }
  $cmd = Get-Command obs64.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  return $null
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

function Ensure-RuntimeDependencies {
  [CmdletBinding()]
  param([string] $Proxy)
  Ensure-Chocolatey -Proxy $Proxy
  $chocoExe = (Get-Command choco.exe -ErrorAction SilentlyContinue).Path
  if (-not $chocoExe) { return }
  foreach ($dep in $global:RuntimeDependencies) {
    try {
      Write-Host ("Ensuring runtime dependency: {0}" -f $dep.Name)
      Start-Process -FilePath $chocoExe -ArgumentList @('install', $dep.Choco, '-y', '--no-progress') -Wait -WindowStyle Hidden | Out-Null
    } catch { Write-Warning ("Failed to install dependency {0}: {1}" -f $dep.Name, $_.Exception.Message) }
  }
}

function Invoke-ExtractAndLaunchDemo {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $true)] [string] $ZipPath,
    [Parameter(Mandatory = $false)] [string] $Proxy,
    [Parameter(Mandatory = $false)] [string] $ExtractDir
  )

  $targetBase = if ([string]::IsNullOrWhiteSpace($ExtractDir)) { Get-DesktopPath } else { $ExtractDir }
  if (-not (Test-Path -LiteralPath $targetBase)) { try { New-Item -ItemType Directory -Path $targetBase | Out-Null } catch {} }
  $demoDir = Join-Path $targetBase 'WindowsDemo'
  Write-Host ("Demo target directory: {0}" -f $demoDir)

  # If already extracted and contains an exe, launch directly
  try {
    $existingExe = Get-ChildItem -LiteralPath $demoDir -Recurse -Filter *.exe -ErrorAction SilentlyContinue | Select-Object -First 1
  } catch { $existingExe = $null }
  if ($existingExe) {
    Write-Host "Demo already extracted; launching existing build..."
    try {
      Start-Process -FilePath $existingExe.FullName -WorkingDirectory (Split-Path -Parent $existingExe.FullName)
    } catch { Write-Warning ("Failed to launch demo: {0}" -f $_.Exception.Message) }
    return
  }

  # Validate the zip before attempting extraction
  if (-not (Test-ValidZip -Path $ZipPath)) {
    Write-Warning ("Demo zip appears invalid: {0}" -f $ZipPath)
    return
  }

  # Extract
  Write-Host "Extracting demo..."
  try { if (Test-Path -LiteralPath $demoDir) { Remove-Item -Recurse -Force $demoDir } } catch {}
  $extracted = $false
  if (-not $extracted) { $extracted = Extract-ZipWithProgress -ZipPath $ZipPath -Destination $demoDir }
  if (-not $extracted) {
    Write-Host "Trying Expand-Archive fallback extraction..."
    $extracted = Extract-ZipFallbackExpandArchive -ZipPath $ZipPath -Destination $demoDir
  }
  if (-not $extracted) {
    Write-Warning "All extraction methods failed; cannot launch demo."
    return
  }

  Ensure-RuntimeDependencies -Proxy $Proxy

  # Determine scan root; if single top-level dir and no root exes, use it
  $scanRoot = $demoDir
  try {
    $rootExes = Get-ChildItem -LiteralPath $demoDir -Filter *.exe -ErrorAction SilentlyContinue
    if (-not $rootExes) {
      $dirs = Get-ChildItem -LiteralPath $demoDir -Directory -ErrorAction SilentlyContinue
      if ($dirs.Count -eq 1) { $scanRoot = $dirs[0].FullName }
    }
  } catch {}

  try {
    $exeCandidates = Get-ChildItem -LiteralPath $scanRoot -Recurse -Filter *.exe -ErrorAction SilentlyContinue | Sort-Object Length -Descending
    if ($exeCandidates -and $exeCandidates.Count -gt 0) {
      $target = $exeCandidates[0]
      Write-Host ("Launching demo: {0}" -f $target.FullName)
      Start-Process -FilePath $target.FullName -WorkingDirectory (Split-Path -Parent $target.FullName)
    } else {
      Write-Warning "Could not find a demo executable to launch after extraction."
    }
  } catch { Write-Warning ("Failed to launch demo: {0}" -f $_.Exception.Message) }
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
  "AuxAudioDevice1": {"balance": 0.5, "deinterlace_field_order": 0, "deinterlace_mode": 0, "enabled": true, "flags": 0, "hotkeys": {}, "id": "wasapi_output_capture", "mixers": 255, "monitoring_type": 0, "muted": false, "name": "Desktop Audio", "prev_ver": 486604803, "private_settings": {}, "push-to-mute": false, "push-to-mute-delay": 0, "push-to-talk": false, "push-to-talk-delay": 0, "settings": {"device_id": "default"}, "sync": 0, "versioned_id": "wasapi_output_capture", "volume": 1.0},
  "AuxAudioDevice2": {"balance": 0.5, "deinterlace_field_order": 0, "deinterlace_mode": 0, "enabled": true, "flags": 0, "hotkeys": {}, "id": "wasapi_input_capture", "mixers": 255, "monitoring_type": 0, "muted": false, "name": "Mic/Aux", "prev_ver": 486604803, "private_settings": {}, "push-to-mute": false, "push-to-mute-delay": 0, "push-to-talk": false, "push-to-talk-delay": 0, "settings": {"device_id": "default"}, "sync": 0, "versioned_id": "wasapi_input_capture", "volume": 1.0},
  "current_program_scene": "$SceneName",
  "current_scene": "$SceneName",
  "current_transition": "Fade",
  "groups": [],
  "modules": {},
  "name": "$CollectionName",
  "preview_locked": false,
  "quick_transitions": [{"duration": 300, "fade_to_black": false, "hotkeys": [], "id": 1, "name": "Cut"}],
  "saved_projectors": [],
  "scaling_enabled": false,
  "scaling_level": 0,
  "scaling_off_x": 0.0,
  "scaling_off_y": 0.0,
  "scene_order": [{"name": "$SceneName"}],
  "sources": [
    {
      "balance": 0.5,
      "deinterlace_field_order": 0,
      "deinterlace_mode": 0,
      "enabled": true,
      "flags": 0,
      "hotkeys": {"libobs.show_scene_item.RTMP Stream": [], "libobs.hide_scene_item.RTMP Stream": []},
      "id": "scene",
      "mixers": 0,
      "monitoring_type": 0,
      "muted": false,
      "name": "$SceneName",
      "prev_ver": 486604803,
      "private_settings": {},
      "push-to-mute": false,
      "push-to-mute-delay": 0,
      "push-to-talk": false,
      "push-to-talk-delay": 0,
      "settings": {
        "custom_size": false,
        "id_counter": 1,
        "items": [
          {
            "align": 5,
            "blend_method": "default",
            "blend_type": "normal",
            "bounds": {"x": 1920.0, "y": 1080.0},
            "bounds_align": 0,
            "bounds_type": 2,
            "crop_bottom": 0,
            "crop_left": 0,
            "crop_right": 0,
            "crop_top": 0,
            "group_item_backup": false,
            "hide_transition": {"duration": 0},
            "id": 1,
            "locked": false,
            "name": "RTMP Stream",
            "pos": {"x": 0.0, "y": 0.0},
            "private_settings": {},
            "rot": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "scale_filter": "disable",
            "show_transition": {"duration": 0},
            "visible": true
          }
        ]
      },
      "sync": 0,
      "versioned_id": "scene",
      "volume": 1.0
    },
    {
      "balance": 0.5,
      "deinterlace_field_order": 0,
      "deinterlace_mode": 0,
      "enabled": true,
      "flags": 0,
      "hotkeys": {"MediaSource.Pause": [], "MediaSource.Play": [], "MediaSource.Restart": [], "MediaSource.Stop": [], "libobs.mute": [], "libobs.unmute": [], "libobs.push-to-mute": [], "libobs.push-to-talk": []},
      "id": "ffmpeg_source",
      "mixers": 255,
      "monitoring_type": 0,
      "muted": false,
      "name": "RTMP Stream",
      "prev_ver": 486604803,
      "private_settings": {},
      "push-to-mute": false,
      "push-to-mute-delay": 0,
      "push-to-talk": false,
      "push-to-talk-delay": 0,
      "settings": {
        "buffering_mb": 2,
        "clear_on_media_end": false,
        "close_when_inactive": false,
        "color_range": 0,
        "hw_decode": true,
        "input": "rtmp://localhost:1935/live/mystream",
        "input_format": "",
        "is_local_file": false,
        "linear_alpha": false,
        "looping": false,
        "reconnect_delay_sec": 10,
        "restart_on_activate": true,
        "seekable": false,
        "speed_percent": 100
      },
      "sync": 0,
      "versioned_id": "ffmpeg_source",
      "volume": 1.0
    }
  ],
  "transition_duration": 300,
  "transitions": [],
  "version": "30.2.3"
}
"@

Set-Content -Path $scenePath -Value $sceneJson -Encoding UTF8
Write-Host "Scene collection written to $scenePath"

# Update OBS global configuration to set our collection as current
$globalConfigPath = Join-Path $env:APPDATA "obs-studio\global.ini"
$profilesConfigPath = Join-Path $env:APPDATA "obs-studio\basic\profiles\Untitled\basic.ini"

# Ensure the global.ini exists and set our collection as current
if (Test-Path -LiteralPath $globalConfigPath) {
  $globalConfig = Get-Content -Path $globalConfigPath -Raw
  # Update or add the SceneCollection setting
  if ($globalConfig -match 'SceneCollection=.*') {
    $globalConfig = $globalConfig -replace 'SceneCollection=.*', "SceneCollection=$CollectionName"
  } else {
    # Add it to the [Basic] section if it doesn't exist
    if ($globalConfig -match '\[Basic\]') {
      $globalConfig = $globalConfig -replace '\[Basic\]', "[Basic]`nSceneCollection=$CollectionName"
    } else {
      $globalConfig += "`n[Basic]`nSceneCollection=$CollectionName`n"
    }
  }
  Set-Content -Path $globalConfigPath -Value $globalConfig -Encoding UTF8
} else {
  # Create a minimal global.ini if it doesn't exist
  $globalIniContent = @"
[General]
Name=Untitled

[Basic]
SceneCollection=$CollectionName
SceneCollectionFile=$CollectionName
"@
  Ensure-Directory (Split-Path -Parent $globalConfigPath)
  Set-Content -Path $globalConfigPath -Value $globalIniContent -Encoding UTF8
}

Write-Host "OBS configuration updated to use collection '$CollectionName'"

# Determine extraction path based on script location
$scriptPath = $PSScriptRoot
if (-not $scriptPath) { $scriptPath = Get-Location }
$currentFolderName = Split-Path -Leaf $scriptPath

# If we're in a 'windows' folder, extract to parent's parent (../../)
# Otherwise use the specified DemoExtractDir or default
if ($currentFolderName -eq 'windows') {
  $autoExtractDir = Join-Path (Split-Path -Parent (Split-Path -Parent $scriptPath)) ''
  Write-Host "Script running from 'windows' folder, will extract to: $autoExtractDir"
  
  # Check if game already exists at parent location
  $parentDemoDir = Join-Path $autoExtractDir 'WindowsDemo'
  if (Test-Path -LiteralPath $parentDemoDir) {
    try {
      $existingExe = Get-ChildItem -LiteralPath $parentDemoDir -Recurse -Filter *.exe -ErrorAction SilentlyContinue | Select-Object -First 1
      if ($existingExe) {
        Write-Host "Demo already extracted at parent location; launching existing build..."
        Start-Process -FilePath $existingExe.FullName -WorkingDirectory (Split-Path -Parent $existingExe.FullName)
        $SkipDemo = $true  # Skip further download/extraction
      }
    } catch {
      Write-Warning ("Failed to launch existing demo: {0}" -f $_.Exception.Message)
    }
  }
  
  # Use the parent location for extraction if not specified
  if (-not $DemoExtractDir) {
    $DemoExtractDir = $autoExtractDir
  }
}

# Download demo zip
if ($SkipDemo) {
  Write-Host "Skipping demo download per parameter."
} else {
  try {
    $downloadsPath = Get-DownloadsPath
    $downloadOut = Join-Path $downloadsPath "WindowsDemo.zip"
    if ((-not (Test-Path -LiteralPath $downloadOut)) -or $ForceDownloadDemo) {
      Write-Host "Downloading demo: $DemoUrl -> $downloadOut"
      Download-File -Uri $DemoUrl -Destination $downloadOut -Proxy $Proxy -Quiet:$QuietNetwork
      Write-Host "Downloaded: $downloadOut"
      Invoke-ExtractAndLaunchDemo -ZipPath $downloadOut -Proxy $Proxy -ExtractDir $DemoExtractDir
    } else {
      Write-Host "Demo already present: $downloadOut."
      $zipLooksValid = Test-ValidZip -Path $downloadOut
      if (-not $zipLooksValid -or $ForceDownloadDemo) {
        Write-Warning "Existing demo zip appears invalid or corrupted. Re-downloading..."
        Download-File -Uri $DemoUrl -Destination $downloadOut -Proxy $Proxy -Quiet:$QuietNetwork
      }
      Invoke-ExtractAndLaunchDemo -ZipPath $downloadOut -Proxy $Proxy -ExtractDir $DemoExtractDir
    }
  } catch {
    Write-Warning "Failed to download demo: $($_.Exception.Message)"
  }
}

# Small delay to ensure configuration files are written
Start-Sleep -Milliseconds 500

# Launch OBS with our collection and scene
Write-Host "Starting OBS..."
$obsWorkingDir = Split-Path -Parent $obsExe

# Check if OBS is already running and kill it first to ensure clean start
$obsProcesses = Get-Process obs64 -ErrorAction SilentlyContinue
if ($obsProcesses) {
  Write-Host "Stopping existing OBS instances..."
  $obsProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 2
}

# Launch OBS with the collection parameter
Start-Process -FilePath $obsExe -WorkingDirectory $obsWorkingDir -ArgumentList @("--collection", "$CollectionName", "--scene", "$SceneName")
Write-Host "OBS launched with collection '$CollectionName' and scene '$SceneName' (source '$SourceName')."
Write-Host ""
Write-Host "If the scene doesn't appear:"
Write-Host "  1. In OBS, go to Scene Collection menu"
Write-Host "  2. Select 'AutoRTMP' collection"
Write-Host "  3. The 'Vtuber' scene with RTMP source should be loaded"


