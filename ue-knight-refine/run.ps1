<#
  Run one step of the character pipeline headless, without touching anything outside this folder.

  .\run.ps1 step1_import    # import SourceAssets/<Character>_Loadout.glb as one skeletal mesh each
  .\run.ps1 step2_refine    # look-dev materials, LOD chain, glTF export to Export/
  .\run.ps1 step3_beauty    # studio stills: raw HDR captures to Export/Beauty (then: python Scripts/grade_beauty.py)
  .\run.ps1 step2_refine -Characters Barbarian,Mage   # only some characters (default: all, see Scripts/characters.py)

  Isolation: the project's own derived-data cache (-DDC=KnightIsolated, defined in Config/DefaultEngine.ini),
  no trace server, no pip installs; the shared recent-projects list is restored and the crash-reporter
  monitor's session logs from this run are removed afterwards.
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('step1_import', 'step2_refine', 'step3_beauty', 'step4_realm_import', 'step5_realm_refine', 'step6_realm_beauty', 'probe_realm')]
    [string]$Step,
    [string[]]$Characters = @(),
    [ValidateSet('', 'poses', 'angles')]
    [string]$Preview = '',  # step3_beauty only: small frames of several poses, or of the chosen pose from four sides
    [string[]]$Only = @()   # realm steps only: world, dragon, horse, skeletons (step5) or source file names (step4)
)
$ErrorActionPreference = 'Stop'

$Editor  = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$Project = Join-Path $PSScriptRoot 'KnightRefine.uproject'
$Script  = Join-Path $PSScriptRoot "Scripts\$Step.py"
$Log     = Join-Path $PSScriptRoot "Saved\Logs\run_$Step.txt"
# Unreal adds every opened project to this per-user list, which the whole team shares on this machine.
$Shared  = Join-Path $env:LOCALAPPDATA 'UnrealEngine\5.8\Saved\Config\WindowsEditor\EditorSettings.ini'

if (Get-Process -Name 'UnrealEditor*' -ErrorAction SilentlyContinue) {
    throw 'Another Unreal Editor is running on this machine. Run this again when it has closed.'
}

# Every launch also starts Unreal's crash-reporter monitor, which writes a session log to this shared folder.
$CrcLogs = Join-Path $env:LOCALAPPDATA 'CrashReportClient\Saved\Logs'
$crcBefore = @{}
if (Test-Path $CrcLogs) { Get-ChildItem $CrcLogs -File | ForEach-Object { $crcBefore[$_.Name] = $_.LastWriteTimeUtc } }

# A run stopped before its clean-up (for example by piping this script into Select-Object -First 1, which ends it
# early) leaves Unreal's version of the shared list in place: possibly empty, or listing this project. So keep a
# reference copy taken only from a clean list, and repair the shared list from it before anything else.
$Reference = Join-Path $PSScriptRoot 'Saved\SharedBackup\EditorSettings.ini'
$selfName = $Project.Replace('\', '/')
function Test-CleanList([string]$path) {
    (Test-Path $path) -and (Get-Item $path).Length -gt 0 -and -not (Select-String -Path $path -SimpleMatch $selfName -Quiet)
}
if (Test-CleanList $Shared) {
    New-Item -ItemType Directory -Force (Split-Path $Reference) | Out-Null
    Copy-Item $Shared $Reference -Force
}
elseif ((Test-Path $Shared) -and (Test-Path $Reference)) {
    Copy-Item $Reference $Shared -Force
    Write-Warning 'The shared recent-projects list was left over from an interrupted run; repaired it from the reference copy.'
}

$backup = Join-Path $env:TEMP ("KnightRefine-EditorSettings-{0}.ini" -f [guid]::NewGuid())
$hadShared = Test-Path $Shared
if ($hadShared) { Copy-Item $Shared $backup }

New-Item -ItemType Directory -Force (Split-Path $Log) | Out-Null
# Unreal's command-line parser can misread backslashes in quoted paths, so pass forward slashes.
$argList = @(
    "`"$($Project.Replace('\', '/'))`"", '-run=pythonscript', "-script=`"$($Script.Replace('\', '/'))`"",
    '-DDC=KnightIsolated', '-AllowCommandletRendering', '-NoTextureStreaming', '-notraceserver',
    '-unattended', '-nop4', '-nosplash', '-NoSound', '-stdout', '-FullStdOutLogOutput'
)
$started = Get-Date
# read by Scripts/characters.py inside Unreal
$env:KNIGHT_REFINE_CHARACTERS = ($Characters -join ',')
$env:KNIGHT_REFINE_REALM_ONLY = ($Only -join ',')
$env:KNIGHT_REFINE_PREVIEW = @{ '' = ''; 'poses' = '1'; 'angles' = 'angles' }[$Preview]
try {
    $p = Start-Process -FilePath $Editor -ArgumentList $argList -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $Log -RedirectStandardError "$Log.err"
    $secs = [int]((Get-Date) - $started).TotalSeconds
    if ($p.ExitCode -eq 0) { Write-Host "$Step finished in $secs s. Log: $Log" }
    else { Write-Warning "$Step exited with code $($p.ExitCode) after $secs s. Log: $Log" }
}
finally {
    Remove-Item Env:KNIGHT_REFINE_CHARACTERS, Env:KNIGHT_REFINE_PREVIEW, Env:KNIGHT_REFINE_REALM_ONLY -ErrorAction SilentlyContinue
    if ($hadShared) {
        Copy-Item $backup $Shared -Force
        if ((Get-FileHash $backup).Hash -ne (Get-FileHash $Shared).Hash) { throw "The shared recent-projects list could not be restored; the copy is at $backup" }
        Remove-Item $backup
    }
    elseif (Test-Path $Shared) { Remove-Item $Shared }
    Write-Host 'Shared recent-projects list restored.'
    if (Test-Path $CrcLogs) {
        $now = Get-ChildItem $CrcLogs -File
        # put back the name of any earlier session's log that the monitor rotated
        foreach ($name in @($crcBefore.Keys)) {
            if (-not (Test-Path (Join-Path $CrcLogs $name))) {
                $moved = $now | Where-Object { -not $crcBefore.ContainsKey($_.Name) -and $_.LastWriteTimeUtc -eq $crcBefore[$name] } | Select-Object -First 1
                if ($moved) { Rename-Item $moved.FullName $name }
            }
        }
        # and remove the logs this run created
        Get-ChildItem $CrcLogs -File | Where-Object { -not $crcBefore.ContainsKey($_.Name) -and $_.CreationTimeUtc -ge $started.ToUniversalTime() } | Remove-Item
        Write-Host 'Crash-reporter session logs from this run removed.'
    }
}
