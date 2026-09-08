#requires -Version 5.1

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$RepositoryOwner = "InsecurePassword"
$RepositoryName = "Codex-AMS"
$RepositoryRef = "main"
$RawBaseUrl = "https://github.com/$RepositoryOwner/$RepositoryName/raw/refs/heads/$RepositoryRef"
$ManifestUrl = "$RawBaseUrl/install-manifest.txt"
$SkillName = "adaptive-master-subagent-orchestration"
$ManagedMarker = "# managed-by: adaptive-master-subagent-orchestration"
$UserAgent = "AMS-Tree-Installer"
$UserHome = if ($HOME) { $HOME } else { [Environment]::GetFolderPath("UserProfile") }
if (-not $UserHome) { throw "Unable to determine the current user home directory." }

$SkillHome = if ($env:AMS_SKILL_HOME) { $env:AMS_SKILL_HOME } else { Join-Path $UserHome ".agents\skills" }
$CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $UserHome ".codex" }
$Destination = Join-Path $SkillHome $SkillName
$AgentHome = Join-Path $CodexHome "agents"
$ProfilesOnly = $false
if ($env:AMS_INSTALL_PROFILES_ONLY) {
    if ($env:AMS_INSTALL_PROFILES_ONLY -cne "1") { throw "AMS_INSTALL_PROFILES_ONLY must be unset or exactly 1." }
    $ProfilesOnly = $true
}
$MaxManifestBytes = 256KB
$MaxFileBytes = 1MB
$MaxTotalBytes = 100MB

$ProfileFiles = @(
    "ams_sol_low.toml", "ams_sol_medium.toml", "ams_sol_high.toml", "ams_sol_xhigh.toml", "ams_sol_max.toml",
    "ams_astra_low.toml", "ams_astra_medium.toml", "ams_astra_high.toml", "ams_astra_xhigh.toml", "ams_astra_max.toml",
    "ams_daybreak_blue_max.toml",
    "ams_terra_low.toml", "ams_terra_medium.toml", "ams_terra_high.toml", "ams_terra_xhigh.toml", "ams_terra_max.toml",
    "ams_luna_low.toml", "ams_luna_medium.toml", "ams_luna_high.toml", "ams_luna_xhigh.toml", "ams_luna_max.toml",
    "ams_spark_low.toml", "ams_spark_medium.toml", "ams_spark_high.toml"
)

$RequiredFiles = @(
    "SKILL.md",
    "agents/openai.yaml",
    "references/blocker-diagnosis.md",
    "references/configuration-maintenance.md",
    "references/computer-use.md",
    "references/daybreak-blue.md",
    "references/hierarchy-control.md",
    "references/intensity-control.md",
    "references/model-governance.md",
    "references/model-guidance.md",
    "references/model-switching.md",
    "references/package-maintenance.md",
    "references/profile-management.md",
    "references/project-control.md",
    "references/project-governance.md",
    "references/root-execution-fallback.md",
    "references/runtime-core.md",
    "references/scope-dependency-control.md",
    "references/zergling-rush.md"
)
foreach ($ProfileFile in $ProfileFiles) { $RequiredFiles += "assets/agent-profiles/$ProfileFile" }

$PriorCanonicalProfileHashes = @{
    "ams_luna_high.toml" = @("6400ff519bf08e609d663274a03ab63103da0e3c263a75913434a47bb84f6963", "f727d164f9517f5d654bf8d6192b4db39a1f7a5a67473793daf755c2bbe2abee", "22cd43c99ba332d8e5902f1ee96a9f8c481a21bd9c3b108f2ee6ecdaaf50f986", "f7a8bd41fb963aa79319bbe4ad9531204568d6a212013f1116029ddca9d805d6", "99a75b8f47ece6fae8ea4e13d81441cb857e0034ab87611788b6b1a2b152b0e8")
    "ams_luna_low.toml" = @("1a8d32c5bab48bec8a8389ebf3e5fa4d341ae148ad50c5cb43daebe6c953fc56", "1032905d4e79c15b02397657f2641397b7af49540c34ed271737e5310155c124", "869cce6526326fe89cc9f698890ce50f99f6f2e7bec7b06460e55fe1ab8cfac1", "fb47eec631a3eb6ade50951939dcce9cefe894607d27654eb67a476a1f3918f8", "c9f4b4fc800f4f3dfe8d3205bc0c6842d17d0b49fa4fbce83a203ceac57600a9")
    "ams_luna_max.toml" = @("3d50cdf5952caa16c2109d3ec4237c52f11fb26ffd5914889b25eaf6b390d424", "91dba7802d9695cf77fac845f80a85f7f64cc9548e5519b50de1c5c9914f6a50", "16a6e2472f3117e145b300cc2ee1ac30734f079240cc19a2f6d936e577cb4133", "3b1fcb9e66d1a402212e3a8387bc63c557f8a7ed048a315bd53e1b91d487e441", "29bafcd1ce190892e187651be15eacb9f75768f7e552770ff46620107bf7bd58")
    "ams_luna_medium.toml" = @("29d95fae263c531dba5a4c5ec0ab31f92b122e427773fc0c88a4e6b0325bf161", "64d81fa0ac68fb3ff7dc57bc3caf125ff01284dbf975587071bbe196c85c11f9", "43222d1cd3b9a5991e7d02cf9648bc67d879b6fd8d96271f0ec01ddc025df290", "5cf1e7778d634bc3521e952a8d3dbb0c78dadd7c0a4fb5c4e5d1e3b147154f00", "c5e3cb8af09a764f82ad8433642eba28aa2fe626feb7776710874b9f5d6d754a")
    "ams_luna_xhigh.toml" = @("f5681143cc0831adf65747d4dcd0be7877b72c5c314c63f4ef458008cf531fe8", "b889ae809d725c3c3073cdee6f89428b7ed7b421cb6b56727a6b002fd46f9630", "5ad2eb60b6e8bec121bec6365c890cf0c7dfe357686061ebd8e490fda3a1466d", "799766e76b4c9f384ca451b0139bd2147b2dd654ac82ad11e71ce02c09a679bb", "c2dbc5e81baad3b329038658f71dccc1c8b8946b475e62f25a57abdbe74c3e54")
    "ams_sol_high.toml" = @("b68803ff09b267ee6b859c00d1fcac5e99f7c1b05dffc85a3f3876e1978e2130", "6a32011598b28c5d3058f99194ae4512faceae74f6af39e5dadc9fe10c1fadcd", "00050f8f207231976c73d2f433d502bbd1d39493373a829bb6428f67d802ab3f", "8ad9d1e8d4794eb2d1c53ee52d5d08633f874d3d5bd6ab470b4be7a958c3435a", "773b05567bd7517d80bb8a7ae268be675ee1ddd931edb1689afa8ded954df9b5")
    "ams_sol_low.toml" = @("0dafc7dd89929f2fb736b044e3b3d9e735061adf3c1846d7db3fed77e551173a", "16b12b325277c175afb8be1e51396684d11a82cf497fd6951f790d370925eb04", "0f45cc7f558a11d1b3bf87c5f2e845cb7e9e45f5cc6cc447b9e39f49d512a24d", "dfc27a14798dee38474a5940c523a59b91d7ce9358a83d9f135ef97ace2bd84e", "34b055c1fbe1580ab3f724564b65d289956d5a1ed2bd62b5aa0cf6d4d01f78f6")
    "ams_sol_max.toml" = @("405f2215ea3d52444d8cee8e32fcd96fc0c3d4adf34423a3aa5994c8d24c28d6", "4503e3bd52732afeefb74082b749791b4140dfbbb5af7bd2849fb4e426d3f799", "6a75ed8581a148d275c18e832e5c78d6b44c0ee12bbeb466b8aa229d356ea4f1", "25146436a686e49130355359ee177b1f9a562c1814570f1c93500a8ab83877a4", "5b42a2dae627b2466d592a05d8e16a65476aac6d60423470c901a0c3fa242477")
    "ams_sol_medium.toml" = @("52b6648fb3d32770a2ae25048f7017ce03c0af571d05770845a48f6255e3cd2c", "fbb90b8ec0f0718810ce4657bf50db082177cde35a5749851f126e02c7cbf9d1", "5c5032948c980f8735426d296d757d841d5be35dc513e6c0cadb2764adfa8180", "fe8d6a89ed465f091ace53adfaefa4b654f5db66175aa6d90b32e6853a29e4b3", "dd1535eb93a892870ac987ecc3c59e6325726938a3e27d3bb93cfad44a468811")
    "ams_sol_xhigh.toml" = @("f36b2a946c56a9d51b38f7158a9ce0be5efa87da55670a2e2718ea88bf07080f", "b040633e393b5eb6777d83273eb78d6e969a324a686d0a60c544c9341fcdd345", "875810a10c1ae9da5dd53ae1d667c4d2d4e98426b651cb6ebf21bae890489e86", "d0c34e563b7fc9d4203ba939cba7e984cffd322ee896d912052108044e5a8212", "a399d1d02e35028298ccf5e4a138b1a1778febe3dc090aed7da7aec3d97f48e9")
    "ams_spark_high.toml" = @("be9abba98a4d0adef6eb8a44b3cb189df52ea6d31ec964ad2eb2d85064a17f0b", "bba200c3e72c26b8c5ae569749116427b5da17052cbe163d63dbe128b966709b", "bd0122c1f87b08ddb08b24df74979cf89c80c6be47627e9e0270ac2799c5320e", "048808da9efabbc56766c5ade32384f40b9bf70cdca552951107543d2c8b8cf9", "6fdc11666d81261b3b8c06ad6df4deb61d8f208754d437a8d8185d7fd8504c80", "cf8fc04c0bf2209c4ad3290b2bf57f6e3cfe2e7f0ce51ce84b0ad14d89955b78")
    "ams_spark_low.toml" = @("000d9f512aa90a52caa2d1bdaf302e1abb8a81a40e380b51fd14b993befa9043", "848d7b8f77177a864cec1c33609f375b0aae288108f488f3f2e2aeeb686a202e", "b082a31f60627f4364b870c663deed670eff3c5c2adce03cb37b98452d9f0a1b", "e665b2dd2c0fb25321af2a87eb8aee7b3ef91366bf679f8bc57f74afa6be8635", "e37d29aa369bdf32ef5bf5bec4f5fc03b771167a8b8d15d7c7c521c159d65a1c", "bd80dbf9c30cbfb7302a25194632834e7a749267b9b7d841f7a4dee28e203a8d")
    "ams_spark_medium.toml" = @("b0cf2357f80ef4e3129f231dc9fe78b528fc4cf375d3dfa08a9d8b7004b6baae", "ccf76ac7b22544ede2928d8aff579c7fb28ee59132b4dd61beb43e9cd2eba5a6", "c387ffa3c419d66e404ebcc9a7b82a21995690a43a12350a690e9aa13dd5f45a", "6423fdc127044a8ac3963cf54ca385231aac9e322ed9eb422953b2a4d751c154", "22d7f5f1de7baa32e5bde234b70d8bc3e9b69c40165deaee625454261c2e69a9", "d74d42e0c2befb6c843732bf3738a5b719ad3681675e787886aac1ae850ee198")
    "ams_terra_high.toml" = @("2ee408e2ed7a1cb736a06aa7d50d7b82508c53a8f8c8b6fd29f7093620783b46", "9d0b3a814f1877871d21fc8a00b0c0beef9a84cd158749bf67e8ba5eae956319", "8aea92a175187689b1fb16fba76a42b23bc1e3f60349bf642c629a2f3f76014d", "5a0cf2b3009bb9d5afa4f56b8d4d5ec1da3fa3de13ef0209040c3f88e8bc7f7c", "b0bd03cfef9d2783661425e70c4c271d846deffa49c4b04a2b192cd346b272ed")
    "ams_terra_low.toml" = @("361ff9a1cdc9576d81002eac9aa5dae266cf8d8143a3b003324ef92a586a8f8c", "782b82115e95283ef86b68816320a8a151a015ce3e211f09a10cfa47ff485d58", "11980063c0bd805b5b89e119d2d108985b617d3251cc87ecadc28c65097d5190", "863a494b3867da89137a5f5f5134d47872730b561319daa6d7ee69bddfb6797c", "bab5d611ab62ba30d57eb798c9629606889bd350f9b2a33c3832cc16a9c1d45e")
    "ams_terra_max.toml" = @("a0b7553fbe6f2c0a8e0a719bb9469a9fd9be182d1fb0625be73cc63ac27fa623", "765478c11314d58de0e2e9ad375ba8d37582d77356309bc5484f61f69f2290c3", "ab51eab6288db70ae5fa5a725eb92828b98cf95a9ccb8c595d5519e28734af75", "f6f872f0fa8499f43f9b98512122e43acc94c9e79d1184b1c4bb87a4136fc283", "d97fb7d3e41e68228d5799e583cab3b990df6745afa7bc249ad7ddd20b8c8fdf")
    "ams_terra_medium.toml" = @("9d80c212c31d9515dd94e76bb6907f1ce59f7d2689d98fdfdd346fc876d57ac5", "635eefe3f1cd943578d33e64fd47438aab59cbacd4836ee2c2825519a1cd628a", "461a0c2250f2ae535fda672fef5e5918742f3a49ea3677150f4711a059cbba33", "ccc90cb09ba17e170355621bfb354f15f2727965acbe112d423d2865e10b79d3", "dd078cb3e3849cd3b2f5d8f9994f122fbe48f60df148cafb2d1f1540754f434a")
    "ams_terra_xhigh.toml" = @("c5cfbf2fe7c25b49323decf62ca3acf0949ea006f94ebb77f161d7cef9513a02", "7d97b8241c924eeb867b0d4eeffdda363d73026fb8c0aa679855efe9221bff8b", "2c8159222aaeef4d739b74f622b494eb77051c0b15584ad9e48f1f5a39dcdd7a", "1928dd03259ca23e4aa80bd45f32cf1361826519a4e59468c6a4713633a80395", "d371e764a0c22e561a6cb441b04aa1c4f521e1ae3cf6d433f4d42ad7361dd477")
    "ams_astra_high.toml" = @("d4fb1917f82cb4c428d3606fdc4ccd0a274500327ad4a34fa0bf0846fa97fb77", "049bdaf498f30d3d0b12d974a300b1c4b2b2a7637f15faf8828305a0a5d3089f")
    "ams_astra_low.toml" = @("5a0d513c3dd22a64a9f516de2492e457fae617a65b70d2e376d97bcba775bd86", "6a84b9ea942a89c13532b3778b15e784add31ac7bd6aaadce130bdf9726bbab4")
    "ams_astra_max.toml" = @("171fc462327ca4eb3f4633664d9410c8f30126f216368e46d603ed62f13cdeb3", "1a21720488f4bc3f2fc29d605cb4463c5db43c616a159595246d005446b54ed8")
    "ams_astra_medium.toml" = @("50f3156c0c916fea14b772ad447f8249126e5be88129d7fac1e4fceb6b7513a7", "9ea29f923af3a2918c7bb528b092b636cdcf53b0718afdcbd3e380d854262f35")
    "ams_astra_xhigh.toml" = @("b5023cf34a8bbd815193f09a0b9726f73e5985cf2d88d247075be9f13c481a68", "cc32498d22312873f795effe9ca488e448c109a650a5c6ed7d971e72368d3ac3")
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Assert-SafeDirectory {
    param([Parameter(Mandatory=$true)][string]$Path, [Parameter(Mandatory=$true)][string]$Label)
    $Item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if ($Item) {
        if (-not $Item.PSIsContainer) { throw "$Label is not a directory: $Path" }
        if ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "$Label is redirected: $Path" }
        return
    }
    [void](New-Item -ItemType Directory -Path $Path -Force)
    $Item = Get-Item -LiteralPath $Path -Force
    if (-not $Item.PSIsContainer -or ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "$Label could not be established safely: $Path"
    }
}

function Get-Sha256 {
    param([Parameter(Mandatory=$true)][string]$Path)
    return ([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash([IO.File]::ReadAllBytes($Path)))).Replace("-", "").ToLowerInvariant()
}

function Invoke-Download {
    param([Parameter(Mandatory=$true)][string]$Url, [Parameter(Mandatory=$true)][string]$OutFile)
    $Last = $null
    foreach ($Attempt in 1..3) {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $OutFile -UserAgent $UserAgent -TimeoutSec 180
            return
        }
        catch {
            $Last = $_
            if ($Attempt -lt 3) { Start-Sleep -Seconds 1 }
        }
    }
    throw "Download failed: $Url`n$Last"
}

function Test-SafeManifestPath {
    param([Parameter(Mandatory=$true)][string]$Path)
    $Prefix = "$SkillName/"
    if (-not $Path.StartsWith($Prefix, [StringComparison]::Ordinal)) { return $false }
    if ($Path.StartsWith("/", [StringComparison]::Ordinal) -or $Path.Contains("\") -or $Path.Contains("//")) { return $false }
    if ($Path.Contains("/./") -or $Path.EndsWith("/.", [StringComparison]::Ordinal) -or $Path.Contains("/../") -or $Path.EndsWith("/..", [StringComparison]::Ordinal)) { return $false }
    return [Text.RegularExpressions.Regex]::IsMatch($Path, '^[A-Za-z0-9._/-]+$')
}

function Read-Manifest {
    param([Parameter(Mandatory=$true)][string]$Path)
    $Item = Get-Item -LiteralPath $Path -Force
    if ($Item.PSIsContainer -or ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Manifest is not a regular file." }
    if ($Item.Length -le 0 -or $Item.Length -gt $MaxManifestBytes) { throw "Manifest size is invalid." }
    $Bytes = [IO.File]::ReadAllBytes($Path)
    if ($Bytes.Length -eq 0 -or $Bytes[0] -eq 0xEF -or $Bytes -contains 0 -or $Bytes -contains 13) { throw "Manifest encoding is invalid." }
    $Text = [Text.UTF8Encoding]::new($false, $true).GetString($Bytes)
    if (-not $Text.EndsWith("`n", [StringComparison]::Ordinal)) { throw "Manifest must end with LF." }
    $Lines = $Text.Split(@("`n"), [StringSplitOptions]::None)
    if ($Lines.Count -lt 3 -or $Lines[0] -cne "ams-install-manifest-v1") { throw "Manifest header mismatch." }
    $Entries = New-Object System.Collections.Generic.List[object]
    $Seen = @{}
    [Int64]$Total = 0
    for ($Index = 1; $Index -lt $Lines.Count - 1; $Index++) {
        $Parts = $Lines[$Index].Split("`t")
        if ($Parts.Count -ne 3) { throw "Malformed manifest line $($Index + 1)." }
        $Hash, $SizeText, $PackagePath = $Parts
        if (-not [Text.RegularExpressions.Regex]::IsMatch($Hash, '^[0-9a-f]{64}$')) { throw "Invalid manifest hash at line $($Index + 1)." }
        [Int64]$Size = 0
        if (-not [Int64]::TryParse($SizeText, [ref]$Size) -or $Size -lt 0 -or $Size -gt $MaxFileBytes) { throw "Invalid manifest size at line $($Index + 1)." }
        if (-not (Test-SafeManifestPath -Path $PackagePath)) { throw "Unsafe manifest path at line $($Index + 1): $PackagePath" }
        if ($Seen.ContainsKey($PackagePath)) { throw "Duplicate manifest path: $PackagePath" }
        $Seen[$PackagePath] = $true
        $Total += $Size
        if ($Total -gt $MaxTotalBytes) { throw "Manifest total size exceeds the allowed bound." }
        $Entries.Add([pscustomobject]@{ Hash=$Hash; Size=$Size; PackagePath=$PackagePath })
    }
    if ($Entries.Count -eq 0) { throw "Manifest contains no package files." }
    $Expected = @($RequiredFiles | ForEach-Object { "$SkillName/$_" } | Sort-Object)
    $Observed = @($Entries | ForEach-Object PackagePath | Sort-Object)
    if ($Expected.Count -ne $Observed.Count) { throw "Manifest membership count mismatch." }
    for ($Index = 0; $Index -lt $Expected.Count; $Index++) {
        if ($Expected[$Index] -cne $Observed[$Index]) { throw "Manifest membership does not match the exact core package." }
    }
    return $Entries.ToArray()
}

function Test-AuthorizedPriorProfile {
    param([string]$Name, [string]$Hash)
    return $PriorCanonicalProfileHashes.ContainsKey($Name) -and ($PriorCanonicalProfileHashes[$Name] -contains $Hash)
}

function Assert-ProfilePreflight {
    param([Parameter(Mandatory=$true)][string]$SourceRoot)
    foreach ($ProfileFile in $ProfileFiles) {
        $SourceProfile = Join-Path $SourceRoot "assets\agent-profiles\$ProfileFile"
        $TargetProfile = Join-Path $AgentHome $ProfileFile
        $Source = Get-Item -LiteralPath $SourceProfile -Force
        if ($Source.PSIsContainer -or ($Source.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Bundled profile is invalid: $ProfileFile" }
        $FirstLine = [IO.File]::ReadAllLines($SourceProfile)[0]
        if ($FirstLine -cne $ManagedMarker) { throw "Bundled profile lacks the managed marker: $ProfileFile" }
        $Target = Get-Item -LiteralPath $TargetProfile -Force -ErrorAction SilentlyContinue
        if ($Target) {
            if ($Target.PSIsContainer -or ($Target.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Profile target is redirected or not regular: $TargetProfile" }
            $SourceHash = Get-Sha256 $SourceProfile
            $TargetHash = Get-Sha256 $TargetProfile
            if ($SourceHash -cne $TargetHash -and -not (Test-AuthorizedPriorProfile $ProfileFile $TargetHash)) {
                throw "Existing profile differs from current and recognized official predecessor bytes: $TargetProfile"
            }
        }
    }
}


$CurrentHost = [Environment]::MachineName
if ($CurrentHost -cnotmatch '^[A-Za-z0-9._-]{1,128}$') { throw "Unable to establish a safe local host identity." }
$LockGraceSeconds = 30
$ParsedOwnerToken = $null
$ParsedOwnerHost = $null
$ParsedOwnerPid = 0
$ParsedOwnerEpoch = 0

function Get-LockSnapshot {
    param([Parameter(Mandatory=$true)][string]$Path)
    $Directory = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if (-not $Directory -or -not $Directory.PSIsContainer -or ($Directory.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Installer lock is not a safe directory: $Path" }
    $Builder = New-Object Text.StringBuilder
    [void]$Builder.AppendLine("directory_ticks=$($Directory.LastWriteTimeUtc.Ticks)")
    $Items = @(Get-ChildItem -LiteralPath $Path -Force | Sort-Object -Property Name)
    foreach ($Item in $Items) {
        if ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Installer lock contains redirected content: $Path" }
        [void]$Builder.AppendLine("entry=$($Item.Name)`t$([int]$Item.Attributes)`t$($Item.Length)`t$($Item.LastWriteTimeUtc.Ticks)")
    }
    $Owner = Join-Path $Path "owner.log"
    if (Test-Path -LiteralPath $Owner) {
        $OwnerItem = Get-Item -LiteralPath $Owner -Force
        if ($OwnerItem.PSIsContainer -or ($OwnerItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $OwnerItem.Length -le 0 -or $OwnerItem.Length -gt 4096) {
            throw "Installer lock owner record is unsafe: $Path"
        }
        [void]$Builder.AppendLine("owner_hash=$(Get-Sha256 $Owner)")
    }
    return $Builder.ToString()
}

function Read-LockOwner {
    param([Parameter(Mandatory=$true)][string]$Path)
    $script:ParsedOwnerToken = $null
    $script:ParsedOwnerHost = $null
    $script:ParsedOwnerPid = 0
    $script:ParsedOwnerEpoch = 0
    $Item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if (-not $Item -or $Item.PSIsContainer -or ($Item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $Item.Length -le 0 -or $Item.Length -gt 4096) { return $false }
    $Bytes = [IO.File]::ReadAllBytes($Path)
    if ($Bytes[0] -eq 0xEF -or $Bytes -contains 0 -or $Bytes -contains 13) { return $false }
    try { $Text = [Text.UTF8Encoding]::new($false, $true).GetString($Bytes) } catch { return $false }
    if (-not $Text.EndsWith("`n", [StringComparison]::Ordinal)) { return $false }
    $Lines = $Text.Split(@("`n"), [StringSplitOptions]::None)
    if ($Lines.Count -ne 6 -or $Lines[0] -cne "ams-install-lock-v1" -or $Lines[5] -cne "") { return $false }
    $Fields = @{}
    foreach ($Index in 1..4) {
        $Parts = $Lines[$Index].Split("`t")
        if ($Parts.Count -ne 2 -or $Fields.ContainsKey($Parts[0])) { return $false }
        $Fields[$Parts[0]] = $Parts[1]
    }
    $SortedKeys = @($Fields.Keys | Sort-Object) -join ','
    if ($SortedKeys -cne 'acquired_epoch,host,owner_token,pid') { return $false }
    if ($Fields.owner_token -cnotmatch '^[0-9a-f]{32}$' -or $Fields.host -cnotmatch '^[A-Za-z0-9._-]{1,128}$' -or $Fields.pid -cnotmatch '^[1-9][0-9]*$' -or $Fields.acquired_epoch -cnotmatch '^[0-9]+$') { return $false }
    [Int64]$Epoch = 0
    [Int32]$OwnerPid = 0
    if (-not [Int64]::TryParse($Fields.acquired_epoch, [ref]$Epoch) -or -not [Int32]::TryParse($Fields.pid, [ref]$OwnerPid)) { return $false }
    $script:ParsedOwnerToken = $Fields.owner_token
    $script:ParsedOwnerHost = $Fields.host
    $script:ParsedOwnerPid = $OwnerPid
    $script:ParsedOwnerEpoch = $Epoch
    return $true
}

function Test-ProcessExists {
    param([Parameter(Mandatory=$true)][int]$ProcessId)
    return $null -ne (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

function Publish-InstallLockOwner {
    param([Parameter(Mandatory=$true)][string]$Path, [Parameter(Mandatory=$true)][string]$OwnerToken)
    [Int64]$Now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $Temp = Join-Path $Path ".owner.$OwnerToken"
    $Text = "ams-install-lock-v1`nowner_token`t$OwnerToken`nhost`t$CurrentHost`npid`t$PID`nacquired_epoch`t$Now`n"
    [IO.File]::WriteAllText($Temp, $Text, [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $Temp -Destination (Join-Path $Path "owner.log") -Force
}

function Acquire-InstallLock {
    param([Parameter(Mandatory=$true)][string]$Path, [Parameter(Mandatory=$true)][string]$OwnerToken)
    $Existing = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if (-not $Existing) {
        [void](New-Item -ItemType Directory -Path $Path)
        Publish-InstallLockOwner -Path $Path -OwnerToken $OwnerToken
        return
    }
    if (-not $Existing.PSIsContainer -or ($Existing.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Installer lock is not a safe directory: $Path" }
    $First = Get-LockSnapshot -Path $Path
    $OwnerPath = Join-Path $Path "owner.log"
    [Int64]$Now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    if (Test-Path -LiteralPath $OwnerPath) {
        if (-not (Read-LockOwner -Path $OwnerPath)) { throw "Installer lock owner record is malformed: $Path" }
        if ($ParsedOwnerHost -cne $CurrentHost) { throw "Installer lock belongs to another host: $Path" }
        if ($Now -lt $ParsedOwnerEpoch -or ($Now - $ParsedOwnerEpoch) -lt $LockGraceSeconds) { throw "Another AMS install/profile transaction may be active: $Path" }
        if (Test-ProcessExists -ProcessId $ParsedOwnerPid) { throw "Another AMS install/profile transaction is active: $Path" }
    }
    else {
        $Children = @(Get-ChildItem -LiteralPath $Path -Force)
        if ($Children.Count -ne 0) { throw "Ownerless installer lock contains unexpected files: $Path" }
        [Int64]$Modified = [DateTimeOffset]::new($Existing.LastWriteTimeUtc).ToUnixTimeSeconds()
        if ($Now -lt $Modified -or ($Now - $Modified) -lt $LockGraceSeconds) { throw "Another AMS install/profile transaction may be starting: $Path" }
    }
    Start-Sleep -Seconds 1
    $Second = Get-LockSnapshot -Path $Path
    if ($First -cne $Second) { throw "Installer lock changed during stale-lock inspection: $Path" }
    $Quarantine = "$Path.stale.$OwnerToken"
    if (Test-Path -LiteralPath $Quarantine) { throw "Unexpected stale-lock quarantine collision: $Quarantine" }
    Move-Item -LiteralPath $Path -Destination $Quarantine
    try {
        [void](New-Item -ItemType Directory -Path $Path)
        Publish-InstallLockOwner -Path $Path -OwnerToken $OwnerToken
    }
    catch {
        Remove-Item -LiteralPath $Quarantine -Recurse -Force -ErrorAction SilentlyContinue
        throw "Another installer acquired the lock during stale-lock recovery: $Path`n$_"
    }
    Remove-Item -LiteralPath $Quarantine -Recurse -Force
}

function Release-InstallLock {
    param([Parameter(Mandatory=$true)][string]$Path, [Parameter(Mandatory=$true)][string]$OwnerToken)
    $OwnerPath = Join-Path $Path "owner.log"
    if ((Test-Path -LiteralPath $OwnerPath) -and (Read-LockOwner -Path $OwnerPath) -and $ParsedOwnerToken -ceq $OwnerToken) {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Assert-SafeDirectory -Path $SkillHome -Label "Skill parent"
Assert-SafeDirectory -Path $CodexHome -Label "CODEX_HOME"
Assert-SafeDirectory -Path $AgentHome -Label "Agent registry"

$LockPath = Join-Path $CodexHome ".adaptive-master-subagent-orchestration.install.lock"
$LockAcquired = $false
$LockOwnerToken = [Guid]::NewGuid().ToString("N")
$StageRoot = Join-Path $SkillHome (".ams-install-{0}-{1}" -f $PID, [Guid]::NewGuid().ToString("N"))
$Candidate = Join-Path $StageRoot $SkillName
$ManifestBefore = Join-Path $StageRoot "install-manifest.before.txt"
$ManifestAfter = Join-Path $StageRoot "install-manifest.after.txt"
$BackupPath = Join-Path $SkillHome (".{0}.backup-{1}" -f $SkillName, $PID)
$ProfileBackupRoot = Join-Path $StageRoot "profile-backups"
$ExistingMoved = $false
$CandidateInstalled = $false
$Committed = $false
$ProfileCreated = New-Object System.Collections.Generic.List[string]
$ProfileReplaced = New-Object System.Collections.Generic.List[string]
$ProfileTemps = New-Object System.Collections.Generic.List[string]

try {
    Acquire-InstallLock -Path $LockPath -OwnerToken $LockOwnerToken
    $LockAcquired = $true

    [void](New-Item -ItemType Directory -Path $Candidate -Force)
    [void](New-Item -ItemType Directory -Path $ProfileBackupRoot -Force)

    Invoke-Download -Url $ManifestUrl -OutFile $ManifestBefore
    $Entries = Read-Manifest -Path $ManifestBefore
    foreach ($Entry in $Entries) {
        $Relative = $Entry.PackagePath.Substring($SkillName.Length + 1).Replace('/', [IO.Path]::DirectorySeparatorChar)
        $Target = Join-Path $Candidate $Relative
        $Parent = Split-Path -Parent $Target
        [void](New-Item -ItemType Directory -Path $Parent -Force)
        Invoke-Download -Url "$RawBaseUrl/$($Entry.PackagePath)" -OutFile $Target
        $TargetItem = Get-Item -LiteralPath $Target -Force
        if ($TargetItem.Length -ne $Entry.Size) { throw "Size mismatch: $($Entry.PackagePath)" }
        if ((Get-Sha256 $Target) -cne $Entry.Hash) { throw "SHA-256 mismatch: $($Entry.PackagePath)" }
    }

    Invoke-Download -Url $ManifestUrl -OutFile $ManifestAfter
    if ((Get-Sha256 $ManifestBefore) -cne (Get-Sha256 $ManifestAfter)) {
        throw "Manifest changed during installation."
    }
    Assert-ProfilePreflight -SourceRoot $Candidate

    $ProfileSourceRoot = $Candidate
    if (-not $ProfilesOnly) {
        $Existing = Get-Item -LiteralPath $Destination -Force -ErrorAction SilentlyContinue
        if ($Existing) {
            if (-not $Existing.PSIsContainer -or ($Existing.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Refusing to replace an invalid existing skill path: $Destination" }
            if (Test-Path -LiteralPath $BackupPath) { throw "Unexpected backup collision: $BackupPath" }
            Move-Item -LiteralPath $Destination -Destination $BackupPath
            $ExistingMoved = $true
        }
        Move-Item -LiteralPath $Candidate -Destination $Destination
        $CandidateInstalled = $true
        $ProfileSourceRoot = $Destination
    }

    $ProfilesChanged = 0
    $ProfilesUnchanged = 0
    foreach ($ProfileFile in $ProfileFiles) {
        $SourceProfile = Join-Path $ProfileSourceRoot "assets\agent-profiles\$ProfileFile"
        $TargetProfile = Join-Path $AgentHome $ProfileFile
        $SourceHash = Get-Sha256 $SourceProfile
        $Target = Get-Item -LiteralPath $TargetProfile -Force -ErrorAction SilentlyContinue
        if ($Target) {
            $TargetHash = Get-Sha256 $TargetProfile
            if ($SourceHash -ceq $TargetHash) {
                $ProfilesUnchanged++
                continue
            }
            Copy-Item -LiteralPath $TargetProfile -Destination (Join-Path $ProfileBackupRoot $ProfileFile)
            $ProfileReplaced.Add($ProfileFile)
        }
        else {
            $ProfileCreated.Add($ProfileFile)
        }
        $TempProfile = Join-Path $AgentHome (".{0}.ams-new-{1}" -f $ProfileFile, $PID)
        $ProfileTemps.Add($TempProfile)
        Copy-Item -LiteralPath $SourceProfile -Destination $TempProfile
        Move-Item -LiteralPath $TempProfile -Destination $TargetProfile -Force
        if ((Get-Sha256 $TargetProfile) -cne $SourceHash) { throw "Profile post-write verification failed: $ProfileFile" }
        $ProfilesChanged++
    }

    $Committed = $true
    if ($ProfilesOnly) {
        Write-Host "Installed the AMS profile registry bootstrap only."
        Write-Host "Skill installation: unchanged (managed separately)."
    }
    else {
        Write-Host "Installed Adaptive Master-Subagent Orchestration."
        Write-Host "Skill: $Destination"
    }
    Write-Host "Repository ref: $RepositoryRef"
    Write-Host "Profiles: $AgentHome ($ProfilesChanged changed, $ProfilesUnchanged unchanged)"
    Write-Host "Installation complete. Start a new Codex thread before using newly installed profiles."
}
finally {
    if (-not $Committed) {
        foreach ($ProfileFile in $ProfileCreated) {
            Remove-Item -LiteralPath (Join-Path $AgentHome $ProfileFile) -Force -ErrorAction SilentlyContinue
        }
        foreach ($ProfileFile in $ProfileReplaced) {
            Copy-Item -LiteralPath (Join-Path $ProfileBackupRoot $ProfileFile) -Destination (Join-Path $AgentHome $ProfileFile) -Force -ErrorAction SilentlyContinue
        }
        if ($CandidateInstalled) { Remove-Item -LiteralPath $Destination -Recurse -Force -ErrorAction SilentlyContinue }
        if ($ExistingMoved -and (Test-Path -LiteralPath $BackupPath)) { Move-Item -LiteralPath $BackupPath -Destination $Destination -Force -ErrorAction SilentlyContinue }
    }
    foreach ($TempProfile in $ProfileTemps) {
        Remove-Item -LiteralPath $TempProfile -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $StageRoot -Recurse -Force -ErrorAction SilentlyContinue
    if ($Committed -and (Test-Path -LiteralPath $BackupPath)) { Remove-Item -LiteralPath $BackupPath -Recurse -Force -ErrorAction SilentlyContinue }
    if ($LockAcquired) { Release-InstallLock -Path $LockPath -OwnerToken $LockOwnerToken }
}
