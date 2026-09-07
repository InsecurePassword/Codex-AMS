#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ThreadId,
    [string]$SessionsDir
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$MaxRolloutBytes = 64MB
$MaxLineChars = 4MB
$MaxDirectories = 10000
$MaxEntries = 200000
$MaxDepth = 16

Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
using System.Text;

public static class AmsRuntimeObservationNative {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern SafeFileHandle CreateFile(
        string name, uint access, uint share, IntPtr security, uint creation,
        uint flags, IntPtr template);

    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern uint GetFinalPathNameByHandle(
        SafeFileHandle handle, StringBuilder path, uint size, uint flags);

    [StructLayout(LayoutKind.Sequential)]
    private struct ByHandleFileInformation {
        public uint FileAttributes;
        public System.Runtime.InteropServices.ComTypes.FILETIME CreationTime;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastAccessTime;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastWriteTime;
        public uint VolumeSerialNumber;
        public uint FileSizeHigh;
        public uint FileSizeLow;
        public uint NumberOfLinks;
        public uint FileIndexHigh;
        public uint FileIndexLow;
    }

    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool GetFileInformationByHandle(
        SafeFileHandle handle, out ByHandleFileInformation info);

    public static uint LinkCount(SafeFileHandle handle) {
        ByHandleFileInformation info;
        if (!GetFileInformationByHandle(handle, out info))
            throw new Win32Exception(Marshal.GetLastWin32Error());
        return info.NumberOfLinks;
    }

    public static SafeFileHandle OpenDirectory(string path) {
        const uint OPEN_EXISTING = 3;
        const uint FILE_FLAG_BACKUP_SEMANTICS = 0x02000000;
        const uint FILE_SHARE_READ = 1;
        const uint FILE_SHARE_WRITE = 2;
        SafeFileHandle handle = CreateFile(path, 0, FILE_SHARE_READ | FILE_SHARE_WRITE,
            IntPtr.Zero, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, IntPtr.Zero);
        if (handle.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error());
        return handle;
    }

    public static string FinalPath(SafeFileHandle handle) {
        uint needed = GetFinalPathNameByHandle(handle, null, 0, 0);
        if (needed == 0) throw new Win32Exception(Marshal.GetLastWin32Error());
        StringBuilder value = new StringBuilder((int)needed + 1);
        uint written = GetFinalPathNameByHandle(handle, value, (uint)value.Capacity, 0);
        if (written == 0 || written >= value.Capacity) throw new Win32Exception(Marshal.GetLastWin32Error());
        string path = value.ToString();
        if (path.StartsWith(@"\\?\UNC\", StringComparison.OrdinalIgnoreCase)) path = @"\\" + path.Substring(8);
        else if (path.StartsWith(@"\\?\", StringComparison.OrdinalIgnoreCase)) path = path.Substring(4);
        return System.IO.Path.GetFullPath(path).TrimEnd(System.IO.Path.DirectorySeparatorChar, System.IO.Path.AltDirectorySeparatorChar);
    }
}
'@

function Get-OptionalProperty {
    param([object]$Object, [string]$Name)
    if ($null -eq $Object) { return $null }
    $Property = $Object.PSObject.Properties[$Name]
    if ($null -eq $Property -or $Property.Value -isnot [string]) { return $null }
    return [string]$Property.Value
}

function Get-UniqueValue {
    param([object[]]$Values, [string]$Label, [switch]$AllowNull)
    if ($Values.Count -eq 0) { throw "missing $Label" }
    $Unique = New-Object 'System.Collections.Generic.List[object]'
    foreach ($Value in $Values) {
        if (-not $AllowNull -and ($null -eq $Value -or $Value -eq '')) { throw "missing $Label" }
        $Found = $false
        foreach ($Existing in $Unique) {
            if (($null -eq $Existing -and $null -eq $Value) -or
                ($null -ne $Existing -and $null -ne $Value -and ([string]$Existing -ceq [string]$Value))) {
                $Found = $true; break
            }
        }
        if (-not $Found) { $Unique.Add($Value) }
    }
    if ($Unique.Count -ne 1) { throw "conflicting $Label" }
    $Result = $Unique[0]
    if (-not $AllowNull -and ($null -eq $Result -or $Result -eq '')) { throw "missing $Label" }
    return $Result
}

function Test-PathWithin {
    param([string]$Root, [string]$Child)
    $RootValue = [IO.Path]::GetFullPath($Root).TrimEnd('\','/')
    $ChildValue = [IO.Path]::GetFullPath($Child).TrimEnd('\','/')
    if ($ChildValue -ceq $RootValue) { return $true }
    return $ChildValue.StartsWith($RootValue + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)
}

function Find-ExactRollouts {
    param([string]$Root, [string]$Suffix)
    $Matches = New-Object 'System.Collections.Generic.List[object]'
    $Pending = New-Object 'System.Collections.Generic.Stack[object]'
    $Pending.Push([PSCustomObject]@{ Path = $Root; Depth = 0 })
    $DirectoryCount = 0; $EntryCount = 0
    while ($Pending.Count -gt 0) {
        $Current = $Pending.Pop(); $DirectoryCount++
        if ($DirectoryCount -gt $MaxDirectories -or $Current.Depth -gt $MaxDepth) { throw 'sessions-tree traversal bound exceeded' }
        foreach ($Item in @(Get-ChildItem -LiteralPath $Current.Path -Force -ErrorAction Stop)) {
            $EntryCount++
            if ($EntryCount -gt $MaxEntries) { throw 'sessions-tree entry bound exceeded' }
            $ExactName = $Item.Name.StartsWith('rollout-', [StringComparison]::Ordinal) -and $Item.Name.EndsWith($Suffix, [StringComparison]::Ordinal)
            $Redirected = [bool]($Item.Attributes -band [IO.FileAttributes]::ReparsePoint)
            if ($ExactName -and $Redirected) { throw 'an exact rollout filename match is redirected' }
            if ($Redirected) { continue }
            if ($Item.PSIsContainer) { $Pending.Push([PSCustomObject]@{ Path = $Item.FullName; Depth = $Current.Depth + 1 }); continue }
            if ($ExactName) { $Matches.Add($Item.FullName); if ($Matches.Count -gt 1) { return $Matches.ToArray() } }
        }
    }
    return $Matches.ToArray()
}

try {
    if ($ThreadId -cnotmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') { throw 'ThreadId must be a lowercase UUID' }
    if (-not $SessionsDir) {
        $CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else {
            $UserHome = if ($HOME) { $HOME } else { [Environment]::GetFolderPath('UserProfile') }
            if (-not $UserHome) { throw 'HOME/UserProfile is unavailable; pass -SessionsDir' }
            Join-Path $UserHome '.codex'
        }
        $SessionsDir = Join-Path $CodexHome 'sessions'
    }

    $Root = Get-Item -LiteralPath $SessionsDir -Force -ErrorAction SilentlyContinue
    if (-not $Root -or -not $Root.PSIsContainer -or ($Root.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'sessions directory is unavailable or unsafe' }
    $RootHandle = [AmsRuntimeObservationNative]::OpenDirectory($Root.FullName)
    try {
        $RootFinal = [AmsRuntimeObservationNative]::FinalPath($RootHandle)
        $Matches = @(Find-ExactRollouts -Root $Root.FullName -Suffix "-$ThreadId.jsonl")
        if ($Matches.Count -eq 0) { throw 'no rollout filename matched the requested thread id' }
        if ($Matches.Count -ne 1) { throw 'multiple rollout filenames matched the requested thread id' }

        # Denying delete sharing prevents final-component replacement while the snapshot is open.
        $Stream = [IO.File]::Open($Matches[0], [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        try {
            $FinalPath = [AmsRuntimeObservationNative]::FinalPath($Stream.SafeFileHandle)
            if (-not (Test-PathWithin -Root $RootFinal -Child $FinalPath)) { throw 'matched rollout escaped the sessions root' }
            if ([AmsRuntimeObservationNative]::LinkCount($Stream.SafeFileHandle) -ne 1) { throw 'matched rollout has multiple hard links' }
            if ($Stream.Length -le 0 -or $Stream.Length -gt $MaxRolloutBytes) { throw 'matched rollout size is invalid' }
            $InitialLength = $Stream.Length
            $Utf8 = New-Object Text.UTF8Encoding($false, $true)
            $Reader = New-Object IO.StreamReader($Stream, $Utf8, $true, 4096, $true)
            try {
                $Sessions = @(); $Turns = @()
                while (($Line = $Reader.ReadLine()) -ne $null) {
                    if ($Line.Length -gt $MaxLineChars) { throw 'rollout contains an oversized JSONL record' }
                    try { $Record = $Line | ConvertFrom-Json -ErrorAction Stop } catch { throw 'rollout contains invalid JSONL' }
                    $Type = Get-OptionalProperty -Object $Record -Name 'type'
                    $Payload = $Record.PSObject.Properties['payload']
                    if ($null -eq $Payload -or $null -eq $Payload.Value) { continue }
                    if ($Type -ceq 'session_meta') { $Sessions += $Payload.Value }
                    elseif ($Type -ceq 'turn_context') { $Turns += $Payload.Value }
                }
            }
            finally { $Reader.Dispose() }
            if ($Stream.Length -ne $InitialLength) { throw 'rollout changed during inspection' }
        }
        finally { $Stream.Dispose() }
    }
    finally { $RootHandle.Dispose() }

    if ($Sessions.Count -ne 1 -or $Turns.Count -eq 0) { throw 'missing or ambiguous session metadata or turn context' }
    $Session = $Sessions[0]
    $ObservedThreadId = Get-OptionalProperty -Object $Session -Name 'id'
    if ($ObservedThreadId -cne $ThreadId) { throw 'session metadata does not identify the requested thread' }
    $AgentRole = Get-OptionalProperty -Object $Session -Name 'agent_role'
    if (-not $AgentRole) { throw 'missing agent role' }

    $Models=@(); $Efforts=@(); $Sandboxes=@(); $Permissions=@(); $WorkingDirs=@()
    foreach ($Turn in $Turns) {
        $Models += ,(Get-OptionalProperty -Object $Turn -Name 'model')
        $Efforts += ,(Get-OptionalProperty -Object $Turn -Name 'effort')
        $Sandbox = $Turn.PSObject.Properties['sandbox_policy']
        $Sandboxes += ,($(if ($null -ne $Sandbox) { Get-OptionalProperty -Object $Sandbox.Value -Name 'type' } else { $null }))
        $Permission = $Turn.PSObject.Properties['permission_profile']
        $Permissions += ,($(if ($null -ne $Permission) { Get-OptionalProperty -Object $Permission.Value -Name 'type' } else { $null }))
        $WorkingDirs += ,(Get-OptionalProperty -Object $Turn -Name 'cwd')
    }

    [ordered]@{
        thread_id = $ObservedThreadId
        parent_thread_id = Get-OptionalProperty -Object $Session -Name 'parent_thread_id'
        agent_role = $AgentRole
        agent_path = Get-OptionalProperty -Object $Session -Name 'agent_path'
        model_provider = Get-OptionalProperty -Object $Session -Name 'model_provider'
        model = Get-UniqueValue -Values $Models -Label 'model'
        effort = Get-UniqueValue -Values $Efforts -Label 'effort'
        sandbox_policy_type = Get-UniqueValue -Values $Sandboxes -Label 'sandbox policy types' -AllowNull
        permission_profile_type = Get-UniqueValue -Values $Permissions -Label 'permission profile types' -AllowNull
        cwd = Get-UniqueValue -Values $WorkingDirs -Label 'working directories' -AllowNull
    } | ConvertTo-Json -Compress
}
catch {
    [Console]::Error.WriteLine('error: ' + $_.Exception.Message)
    exit 1
}
