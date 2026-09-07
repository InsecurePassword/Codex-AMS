#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

repo_owner="InsecurePassword"
repo_name="Codex-AMS"
repo_ref="main"
raw_base_url="https://github.com/${repo_owner}/${repo_name}/raw/refs/heads/${repo_ref}"
manifest_url="${raw_base_url}/install-manifest.txt"
skill_name="adaptive-master-subagent-orchestration"
managed_marker="# managed-by: adaptive-master-subagent-orchestration"
user_agent="AMS-Tree-Installer"
skill_home="${AMS_SKILL_HOME:-${HOME:?HOME is not set}/.agents/skills}"
codex_home="${CODEX_HOME:-${HOME}/.codex}"
destination="${skill_home}/${skill_name}"
agent_home="${codex_home}/agents"
profiles_only="${AMS_INSTALL_PROFILES_ONLY:-0}"
max_manifest_bytes=262144
max_file_bytes=1048576
max_total_bytes=104857600

profile_files=(
  ams_sol_low.toml ams_sol_medium.toml ams_sol_high.toml ams_sol_xhigh.toml ams_sol_max.toml
  ams_astra_low.toml ams_astra_medium.toml ams_astra_high.toml ams_astra_xhigh.toml ams_astra_max.toml
  ams_daybreak_blue_max.toml
  ams_terra_low.toml ams_terra_medium.toml ams_terra_high.toml ams_terra_xhigh.toml ams_terra_max.toml
  ams_luna_low.toml ams_luna_medium.toml ams_luna_high.toml ams_luna_xhigh.toml ams_luna_max.toml
  ams_spark_low.toml ams_spark_medium.toml ams_spark_high.toml
)

required_files=(
  SKILL.md
  agents/openai.yaml
  references/blocker-diagnosis.md
  references/configuration-maintenance.md
  references/computer-use.md
  references/daybreak-blue.md
  references/hierarchy-control.md
  references/intensity-control.md
  references/package-maintenance.md
  references/profile-management.md
  references/project-control.md
  references/project-governance.md
  references/root-execution-fallback.md
  references/runtime-core.md
  references/scope-dependency-control.md
  references/zergling-rush.md
)
for profile_file in "${profile_files[@]}"; do
  required_files+=("assets/agent-profiles/${profile_file}")
done

fail() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

case "$profiles_only" in
  0|1) ;;
  *) fail "AMS_INSTALL_PROFILES_ONLY must be unset or exactly 1." ;;
esac

for command_name in curl awk sort uniq cmp mktemp wc tr grep head find dirname stat chmod mkdir mv rm cp date sleep ps od hostname; do
  command -v "$command_name" >/dev/null 2>&1 || fail "Required command not found: ${command_name}"
done

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print tolower($1)}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print tolower($1)}'
  else
    fail "A SHA-256 tool is required (sha256sum or shasum)."
  fi
}

is_authorized_prior_profile() {
  case "$1:$2" in
    "ams_luna_high.toml:f727d164f9517f5d654bf8d6192b4db39a1f7a5a67473793daf755c2bbe2abee"|\
    "ams_luna_high.toml:22cd43c99ba332d8e5902f1ee96a9f8c481a21bd9c3b108f2ee6ecdaaf50f986"|\
    "ams_luna_high.toml:f7a8bd41fb963aa79319bbe4ad9531204568d6a212013f1116029ddca9d805d6"|\
    "ams_luna_low.toml:1032905d4e79c15b02397657f2641397b7af49540c34ed271737e5310155c124"|\
    "ams_luna_low.toml:869cce6526326fe89cc9f698890ce50f99f6f2e7bec7b06460e55fe1ab8cfac1"|\
    "ams_luna_low.toml:fb47eec631a3eb6ade50951939dcce9cefe894607d27654eb67a476a1f3918f8"|\
    "ams_luna_max.toml:91dba7802d9695cf77fac845f80a85f7f64cc9548e5519b50de1c5c9914f6a50"|\
    "ams_luna_max.toml:16a6e2472f3117e145b300cc2ee1ac30734f079240cc19a2f6d936e577cb4133"|\
    "ams_luna_max.toml:3b1fcb9e66d1a402212e3a8387bc63c557f8a7ed048a315bd53e1b91d487e441"|\
    "ams_luna_medium.toml:64d81fa0ac68fb3ff7dc57bc3caf125ff01284dbf975587071bbe196c85c11f9"|\
    "ams_luna_medium.toml:43222d1cd3b9a5991e7d02cf9648bc67d879b6fd8d96271f0ec01ddc025df290"|\
    "ams_luna_medium.toml:5cf1e7778d634bc3521e952a8d3dbb0c78dadd7c0a4fb5c4e5d1e3b147154f00"|\
    "ams_luna_xhigh.toml:b889ae809d725c3c3073cdee6f89428b7ed7b421cb6b56727a6b002fd46f9630"|\
    "ams_luna_xhigh.toml:5ad2eb60b6e8bec121bec6365c890cf0c7dfe357686061ebd8e490fda3a1466d"|\
    "ams_luna_xhigh.toml:799766e76b4c9f384ca451b0139bd2147b2dd654ac82ad11e71ce02c09a679bb"|\
    "ams_sol_high.toml:6a32011598b28c5d3058f99194ae4512faceae74f6af39e5dadc9fe10c1fadcd"|\
    "ams_sol_high.toml:00050f8f207231976c73d2f433d502bbd1d39493373a829bb6428f67d802ab3f"|\
    "ams_sol_high.toml:8ad9d1e8d4794eb2d1c53ee52d5d08633f874d3d5bd6ab470b4be7a958c3435a"|\
    "ams_sol_low.toml:16b12b325277c175afb8be1e51396684d11a82cf497fd6951f790d370925eb04"|\
    "ams_sol_low.toml:0f45cc7f558a11d1b3bf87c5f2e845cb7e9e45f5cc6cc447b9e39f49d512a24d"|\
    "ams_sol_low.toml:dfc27a14798dee38474a5940c523a59b91d7ce9358a83d9f135ef97ace2bd84e"|\
    "ams_sol_max.toml:4503e3bd52732afeefb74082b749791b4140dfbbb5af7bd2849fb4e426d3f799"|\
    "ams_sol_max.toml:6a75ed8581a148d275c18e832e5c78d6b44c0ee12bbeb466b8aa229d356ea4f1"|\
    "ams_sol_max.toml:25146436a686e49130355359ee177b1f9a562c1814570f1c93500a8ab83877a4"|\
    "ams_sol_medium.toml:fbb90b8ec0f0718810ce4657bf50db082177cde35a5749851f126e02c7cbf9d1"|\
    "ams_sol_medium.toml:5c5032948c980f8735426d296d757d841d5be35dc513e6c0cadb2764adfa8180"|\
    "ams_sol_medium.toml:fe8d6a89ed465f091ace53adfaefa4b654f5db66175aa6d90b32e6853a29e4b3"|\
    "ams_sol_xhigh.toml:b040633e393b5eb6777d83273eb78d6e969a324a686d0a60c544c9341fcdd345"|\
    "ams_sol_xhigh.toml:875810a10c1ae9da5dd53ae1d667c4d2d4e98426b651cb6ebf21bae890489e86"|\
    "ams_sol_xhigh.toml:d0c34e563b7fc9d4203ba939cba7e984cffd322ee896d912052108044e5a8212"|\
    "ams_spark_high.toml:bba200c3e72c26b8c5ae569749116427b5da17052cbe163d63dbe128b966709b"|\
    "ams_spark_high.toml:bd0122c1f87b08ddb08b24df74979cf89c80c6be47627e9e0270ac2799c5320e"|\
    "ams_spark_high.toml:048808da9efabbc56766c5ade32384f40b9bf70cdca552951107543d2c8b8cf9"|\
    "ams_spark_high.toml:6fdc11666d81261b3b8c06ad6df4deb61d8f208754d437a8d8185d7fd8504c80"|\
    "ams_spark_low.toml:848d7b8f77177a864cec1c33609f375b0aae288108f488f3f2e2aeeb686a202e"|\
    "ams_spark_low.toml:b082a31f60627f4364b870c663deed670eff3c5c2adce03cb37b98452d9f0a1b"|\
    "ams_spark_low.toml:e665b2dd2c0fb25321af2a87eb8aee7b3ef91366bf679f8bc57f74afa6be8635"|\
    "ams_spark_low.toml:e37d29aa369bdf32ef5bf5bec4f5fc03b771167a8b8d15d7c7c521c159d65a1c"|\
    "ams_spark_medium.toml:ccf76ac7b22544ede2928d8aff579c7fb28ee59132b4dd61beb43e9cd2eba5a6"|\
    "ams_spark_medium.toml:c387ffa3c419d66e404ebcc9a7b82a21995690a43a12350a690e9aa13dd5f45a"|\
    "ams_spark_medium.toml:6423fdc127044a8ac3963cf54ca385231aac9e322ed9eb422953b2a4d751c154"|\
    "ams_spark_medium.toml:22d7f5f1de7baa32e5bde234b70d8bc3e9b69c40165deaee625454261c2e69a9"|\
    "ams_terra_high.toml:9d0b3a814f1877871d21fc8a00b0c0beef9a84cd158749bf67e8ba5eae956319"|\
    "ams_terra_high.toml:8aea92a175187689b1fb16fba76a42b23bc1e3f60349bf642c629a2f3f76014d"|\
    "ams_terra_high.toml:5a0cf2b3009bb9d5afa4f56b8d4d5ec1da3fa3de13ef0209040c3f88e8bc7f7c"|\
    "ams_terra_low.toml:782b82115e95283ef86b68816320a8a151a015ce3e211f09a10cfa47ff485d58"|\
    "ams_terra_low.toml:11980063c0bd805b5b89e119d2d108985b617d3251cc87ecadc28c65097d5190"|\
    "ams_terra_low.toml:863a494b3867da89137a5f5f5134d47872730b561319daa6d7ee69bddfb6797c"|\
    "ams_terra_max.toml:765478c11314d58de0e2e9ad375ba8d37582d77356309bc5484f61f69f2290c3"|\
    "ams_terra_max.toml:ab51eab6288db70ae5fa5a725eb92828b98cf95a9ccb8c595d5519e28734af75"|\
    "ams_terra_max.toml:f6f872f0fa8499f43f9b98512122e43acc94c9e79d1184b1c4bb87a4136fc283"|\
    "ams_terra_medium.toml:635eefe3f1cd943578d33e64fd47438aab59cbacd4836ee2c2825519a1cd628a"|\
    "ams_terra_medium.toml:461a0c2250f2ae535fda672fef5e5918742f3a49ea3677150f4711a059cbba33"|\
    "ams_terra_medium.toml:ccc90cb09ba17e170355621bfb354f15f2727965acbe112d423d2865e10b79d3"|\
    "ams_terra_xhigh.toml:7d97b8241c924eeb867b0d4eeffdda363d73026fb8c0aa679855efe9221bff8b"|\
    "ams_terra_xhigh.toml:2c8159222aaeef4d739b74f622b494eb77051c0b15584ad9e48f1f5a39dcdd7a"|\
    "ams_terra_xhigh.toml:1928dd03259ca23e4aa80bd45f32cf1361826519a4e59468c6a4713633a80395"|\
    "ams_astra_high.toml:049bdaf498f30d3d0b12d974a300b1c4b2b2a7637f15faf8828305a0a5d3089f"|\
    "ams_astra_low.toml:6a84b9ea942a89c13532b3778b15e784add31ac7bd6aaadce130bdf9726bbab4"|\
    "ams_astra_max.toml:1a21720488f4bc3f2fc29d605cb4463c5db43c616a159595246d005446b54ed8"|\
    "ams_astra_medium.toml:9ea29f923af3a2918c7bb528b092b636cdcf53b0718afdcbd3e380d854262f35"|\
    "ams_astra_xhigh.toml:cc32498d22312873f795effe9ca488e448c109a650a5c6ed7d971e72368d3ac3"|\
    "ams_luna_high.toml:99a75b8f47ece6fae8ea4e13d81441cb857e0034ab87611788b6b1a2b152b0e8"|\
    "ams_luna_low.toml:c9f4b4fc800f4f3dfe8d3205bc0c6842d17d0b49fa4fbce83a203ceac57600a9"|\
    "ams_luna_max.toml:29bafcd1ce190892e187651be15eacb9f75768f7e552770ff46620107bf7bd58"|\
    "ams_luna_medium.toml:c5e3cb8af09a764f82ad8433642eba28aa2fe626feb7776710874b9f5d6d754a"|\
    "ams_luna_xhigh.toml:c2dbc5e81baad3b329038658f71dccc1c8b8946b475e62f25a57abdbe74c3e54"|\
    "ams_sol_high.toml:773b05567bd7517d80bb8a7ae268be675ee1ddd931edb1689afa8ded954df9b5"|\
    "ams_sol_low.toml:34b055c1fbe1580ab3f724564b65d289956d5a1ed2bd62b5aa0cf6d4d01f78f6"|\
    "ams_sol_max.toml:5b42a2dae627b2466d592a05d8e16a65476aac6d60423470c901a0c3fa242477"|\
    "ams_sol_medium.toml:dd1535eb93a892870ac987ecc3c59e6325726938a3e27d3bb93cfad44a468811"|\
    "ams_sol_xhigh.toml:a399d1d02e35028298ccf5e4a138b1a1778febe3dc090aed7da7aec3d97f48e9"|\
    "ams_spark_high.toml:cf8fc04c0bf2209c4ad3290b2bf57f6e3cfe2e7f0ce51ce84b0ad14d89955b78"|\
    "ams_spark_low.toml:bd80dbf9c30cbfb7302a25194632834e7a749267b9b7d841f7a4dee28e203a8d"|\
    "ams_spark_medium.toml:d74d42e0c2befb6c843732bf3738a5b719ad3681675e787886aac1ae850ee198"|\
    "ams_terra_high.toml:b0bd03cfef9d2783661425e70c4c271d846deffa49c4b04a2b192cd346b272ed"|\
    "ams_terra_low.toml:bab5d611ab62ba30d57eb798c9629606889bd350f9b2a33c3832cc16a9c1d45e"|\
    "ams_terra_max.toml:d97fb7d3e41e68228d5799e583cab3b990df6745afa7bc249ad7ddd20b8c8fdf"|\
    "ams_terra_medium.toml:dd078cb3e3849cd3b2f5d8f9994f122fbe48f60df148cafb2d1f1540754f434a"|\
    "ams_terra_xhigh.toml:d371e764a0c22e561a6cb441b04aa1c4f521e1ae3cf6d433f4d42ad7361dd477")
      return 0 ;;
    *) return 1 ;;
  esac
}

assert_safe_directory() {
  local path=$1 label=$2
  [[ ! -L "$path" ]] || fail "${label} is redirected: ${path}"
  [[ ! -e "$path" || -d "$path" ]] || fail "${label} is not a directory: ${path}"
  mkdir -p -- "$path"
  [[ -d "$path" && ! -L "$path" ]] || fail "${label} could not be established safely: ${path}"
}

safe_manifest_path() {
  local path=$1 prefix="${skill_name}/"
  [[ "$path" == "$prefix"* ]] || return 1
  [[ "$path" != *'\'* && "$path" != /* && "$path" != *'//'* ]] || return 1
  [[ "$path" != *'/./'* && "$path" != */. && "$path" != *'/../'* && "$path" != */.. ]] || return 1
  [[ "$path" =~ ^[A-Za-z0-9._/-]+$ ]] || return 1
  return 0
}

download_file() {
  local url=$1 destination_path=$2
  curl --fail --silent --show-error --location \
    --retry 2 --retry-delay 1 --connect-timeout 20 --max-time 180 \
    --user-agent "$user_agent" --output "$destination_path" "$url"
}

validate_manifest() {
  local manifest=$1 line_number=0 total=0 hash size path extra
  [[ -f "$manifest" && ! -L "$manifest" ]] || fail "Manifest is not a regular file."
  local manifest_size
  manifest_size=$(wc -c < "$manifest" | tr -d '[:space:]')
  (( manifest_size > 0 && manifest_size <= max_manifest_bytes )) || fail "Manifest size is invalid."
  [[ $(head -n 1 "$manifest") == "ams-install-manifest-v1" ]] || fail "Unsupported manifest header."

  local paths_file="${manifest}.paths" required_file="${manifest}.required"
  : > "$paths_file"
  while IFS=$'\t' read -r hash size path extra; do
    line_number=$((line_number + 1))
    (( line_number <= 1 )) && continue
    [[ -z "${extra:-}" && "$hash" =~ ^[0-9a-f]{64}$ && "$size" =~ ^[0-9]+$ ]] || fail "Malformed manifest line ${line_number}."
    (( size >= 0 && size <= max_file_bytes )) || fail "Manifest file size is invalid at line ${line_number}."
    safe_manifest_path "$path" || fail "Unsafe manifest path at line ${line_number}: ${path}"
    printf '%s\n' "$path" >> "$paths_file"
    total=$((total + size))
    (( total <= max_total_bytes )) || fail "Manifest total size exceeds the allowed bound."
  done < "$manifest"

  [[ $(wc -l < "$paths_file" | tr -d '[:space:]') -gt 0 ]] || fail "Manifest contains no package files."
  [[ $(sort "$paths_file" | uniq | wc -l | tr -d '[:space:]') == $(wc -l < "$paths_file" | tr -d '[:space:]') ]] || fail "Manifest contains duplicate paths."

  : > "$required_file"
  local relative
  for relative in "${required_files[@]}"; do
    printf '%s/%s\n' "$skill_name" "$relative" >> "$required_file"
  done
  sort "$paths_file" -o "$paths_file"
  sort "$required_file" -o "$required_file"
  cmp -s "$paths_file" "$required_file" || fail "Manifest membership does not match the exact core package."
}

assert_profile_preflight() {
  local source_root=$1 profile_file source_profile target_profile source_hash target_hash first_line
  for profile_file in "${profile_files[@]}"; do
    source_profile="${source_root}/assets/agent-profiles/${profile_file}"
    target_profile="${agent_home}/${profile_file}"
    [[ -f "$source_profile" && ! -L "$source_profile" ]] || fail "Bundled profile is missing or redirected: ${profile_file}"
    IFS= read -r first_line < "$source_profile" || true
    [[ "$first_line" == "$managed_marker" ]] || fail "Bundled profile lacks the managed marker: ${profile_file}"
    [[ ! -L "$target_profile" ]] || fail "Refusing a redirected profile target: ${target_profile}"
    [[ ! -e "$target_profile" || -f "$target_profile" ]] || fail "Profile target is not a regular file: ${target_profile}"
    if [[ -e "$target_profile" ]]; then
      source_hash=$(sha256_file "$source_profile")
      target_hash=$(sha256_file "$target_profile")
      [[ "$source_hash" == "$target_hash" ]] || is_authorized_prior_profile "$profile_file" "$target_hash" || \
        fail "Existing profile differs from current and recognized official predecessor bytes: ${target_profile}"
    fi
  done
}


current_host=$(hostname 2>/dev/null || true)
[[ "$current_host" =~ ^[A-Za-z0-9._-]{1,128}$ ]] || fail "Unable to establish a safe local host identity."
lock_grace_seconds=30
parsed_owner_token=""
parsed_owner_host=""
parsed_owner_pid=""
parsed_owner_epoch=""

path_mtime_epoch() {
  stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null
}

lock_snapshot() {
  local dir=$1 owner mtime entries owner_size owner_hash
  owner="${dir}/owner.log"
  [[ -d "$dir" && ! -L "$dir" ]] || return 1
  mtime=$(path_mtime_epoch "$dir") || return 1
  entries=$(find "$dir" -mindepth 1 -maxdepth 1 -print | LC_ALL=C sort)
  printf 'mtime=%s\nentries=%s\n' "$mtime" "$entries"
  if [[ -e "$owner" ]]; then
    [[ -f "$owner" && ! -L "$owner" ]] || return 1
    owner_size=$(wc -c < "$owner" | tr -d '[:space:]')
    (( owner_size > 0 && owner_size <= 4096 )) || return 1
    ! grep -q $'\r' "$owner" || return 1
    ! od -An -tx1 "$owner" | grep -qiE '(^|[[:space:]])00([[:space:]]|$)' || return 1
    owner_hash=$(sha256_file "$owner") || return 1
    printf 'owner_size=%s\nowner_hash=%s\n' "$owner_size" "$owner_hash"
  fi
}

parse_lock_owner() {
  local owner=$1 line_count header token host pid acquired extra
  [[ -f "$owner" && ! -L "$owner" ]] || return 1
  [[ $(wc -c < "$owner" | tr -d '[:space:]') -le 4096 ]] || return 1
  ! grep -q $'\r' "$owner" || return 1
  ! od -An -tx1 "$owner" | grep -qiE '(^|[[:space:]])00([[:space:]]|$)' || return 1
  line_count=$(wc -l < "$owner" | tr -d '[:space:]')
  [[ "$line_count" == 5 ]] || return 1
  header=$(awk 'NR==1 {print; exit}' "$owner")
  token=$(awk -F '\t' 'NR==2 && $1=="owner_token" {print $2}' "$owner")
  host=$(awk -F '\t' 'NR==3 && $1=="host" {print $2}' "$owner")
  pid=$(awk -F '\t' 'NR==4 && $1=="pid" {print $2}' "$owner")
  acquired=$(awk -F '\t' 'NR==5 && $1=="acquired_epoch" {print $2}' "$owner")
  [[ "$header" == "ams-install-lock-v1" ]] || return 1
  [[ "$token" =~ ^[0-9a-f]{32}$ ]] || return 1
  [[ "$host" =~ ^[A-Za-z0-9._-]{1,128}$ ]] || return 1
  [[ "$pid" =~ ^[1-9][0-9]*$ ]] || return 1
  [[ "$acquired" =~ ^[0-9]+$ ]] || return 1
  parsed_owner_token=$token
  parsed_owner_host=$host
  parsed_owner_pid=$pid
  parsed_owner_epoch=$acquired
}

process_exists() {
  local pid=$1
  ps -p "$pid" -o pid= 2>/dev/null | grep -q '[0-9]'
}

new_owner_token() {
  od -An -N16 -tx1 /dev/urandom | tr -d ' \n'
}

assert_safe_directory "$skill_home" "Skill parent"
assert_safe_directory "$codex_home" "CODEX_HOME"
assert_safe_directory "$agent_home" "Agent registry"

lock_dir="${codex_home}/.adaptive-master-subagent-orchestration.install.lock"
lock_owner_token=$(new_owner_token)
[[ "$lock_owner_token" =~ ^[0-9a-f]{32}$ ]] || fail "Unable to generate installer owner token."
lock_acquired=0
stale_quarantine=""
stage_root=""
candidate=""
manifest_before=""
manifest_after=""
backup_path="${skill_home}/.${skill_name}.backup.$$"
profile_backup_root=""
created_profiles=""
replaced_profiles=""
existing_moved=0
candidate_installed=0
committed=0

release_install_lock() {
  if (( lock_acquired == 1 )) && parse_lock_owner "${lock_dir}/owner.log" && [[ "$parsed_owner_token" == "$lock_owner_token" ]]; then
    rm -rf -- "$lock_dir"
  fi
}

cleanup() {
  local exit_code=$?
  set +e
  if (( committed == 0 )); then
    if [[ -n "$created_profiles" && -f "$created_profiles" ]]; then
      while IFS= read -r profile_file; do
        [[ -n "$profile_file" ]] && rm -f -- "${agent_home}/${profile_file}"
      done < "$created_profiles"
    fi
    if [[ -n "$replaced_profiles" && -f "$replaced_profiles" ]]; then
      while IFS= read -r profile_file; do
        [[ -n "$profile_file" ]] && cp -f -- "${profile_backup_root}/${profile_file}" "${agent_home}/${profile_file}"
      done < "$replaced_profiles"
    fi
    if (( candidate_installed == 1 )); then rm -rf -- "$destination"; fi
    if (( existing_moved == 1 )) && [[ -d "$backup_path" ]]; then mv -- "$backup_path" "$destination"; fi
  fi
  rm -f -- "${agent_home}"/.*.ams-new."$$" 2>/dev/null || true
  [[ -z "$stage_root" ]] || rm -rf -- "$stage_root"
  if (( committed == 1 )) && [[ -d "$backup_path" ]]; then rm -rf -- "$backup_path"; fi
  release_install_lock
  exit "$exit_code"
}
trap cleanup EXIT

publish_lock_owner() {
  local now owner_tmp
  now=$(date +%s)
  owner_tmp="${lock_dir}/.owner.${lock_owner_token}"
  printf 'ams-install-lock-v1\nowner_token\t%s\nhost\t%s\npid\t%s\nacquired_epoch\t%s\n' \
    "$lock_owner_token" "$current_host" "$$" "$now" > "$owner_tmp"
  chmod 600 "$owner_tmp" 2>/dev/null || true
  mv -- "$owner_tmp" "${lock_dir}/owner.log"
  chmod 700 "$lock_dir" 2>/dev/null || true
  lock_acquired=1
}

acquire_install_lock() {
  local owner now age mtime first second entry_count quarantine
  [[ ! -L "$lock_dir" ]] || fail "Installer lock path is redirected: ${lock_dir}"
  if mkdir -- "$lock_dir" 2>/dev/null; then
    publish_lock_owner
    return
  fi
  [[ -d "$lock_dir" && ! -L "$lock_dir" ]] || fail "Installer lock is not a safe directory: ${lock_dir}"
  first=$(lock_snapshot "$lock_dir") || fail "Installer lock is unsafe or changing: ${lock_dir}"
  owner="${lock_dir}/owner.log"
  now=$(date +%s)
  if [[ -e "$owner" ]]; then
    parse_lock_owner "$owner" || fail "Installer lock owner record is malformed: ${lock_dir}"
    [[ "$parsed_owner_host" == "$current_host" ]] || fail "Installer lock belongs to another host: ${lock_dir}"
    (( now >= parsed_owner_epoch && now - parsed_owner_epoch >= lock_grace_seconds )) || fail "Another AMS install/profile transaction may be active: ${lock_dir}"
    ! process_exists "$parsed_owner_pid" || fail "Another AMS install/profile transaction is active: ${lock_dir}"
  else
    entry_count=$(find "$lock_dir" -mindepth 1 -maxdepth 1 -print | wc -l | tr -d '[:space:]')
    [[ "$entry_count" == 0 ]] || fail "Ownerless installer lock contains unexpected files: ${lock_dir}"
    mtime=$(path_mtime_epoch "$lock_dir") || fail "Unable to inspect ownerless installer lock: ${lock_dir}"
    (( now >= mtime && now - mtime >= lock_grace_seconds )) || fail "Another AMS install/profile transaction may be starting: ${lock_dir}"
  fi
  sleep 1
  second=$(lock_snapshot "$lock_dir") || fail "Installer lock changed during stale-lock inspection: ${lock_dir}"
  [[ "$first" == "$second" ]] || fail "Installer lock changed during stale-lock inspection: ${lock_dir}"
  quarantine="${lock_dir}.stale.${lock_owner_token}"
  [[ ! -e "$quarantine" ]] || fail "Unexpected stale-lock quarantine collision: ${quarantine}"
  mv -- "$lock_dir" "$quarantine" || fail "Could not quarantine stale installer lock: ${lock_dir}"
  if ! mkdir -- "$lock_dir" 2>/dev/null; then
    rm -rf -- "$quarantine"
    fail "Another installer acquired the lock during stale-lock recovery: ${lock_dir}"
  fi
  stale_quarantine=$quarantine
  publish_lock_owner
  rm -rf -- "$stale_quarantine"
  stale_quarantine=""
}

acquire_install_lock

stage_root=$(mktemp -d "${skill_home}/.ams-install.XXXXXX")
candidate="${stage_root}/${skill_name}"
manifest_before="${stage_root}/install-manifest.before.txt"
manifest_after="${stage_root}/install-manifest.after.txt"
profile_backup_root="${stage_root}/profile-backups"
created_profiles="${stage_root}/created-profiles.txt"
replaced_profiles="${stage_root}/replaced-profiles.txt"
: > "$created_profiles"
: > "$replaced_profiles"
mkdir -p "$candidate" "$profile_backup_root"

download_file "$manifest_url" "$manifest_before"
validate_manifest "$manifest_before"

while IFS=$'\t' read -r expected_hash expected_size package_path; do
  [[ "$expected_hash" == "ams-install-manifest-v1" ]] && continue
  relative=${package_path#"${skill_name}/"}
  target="${candidate}/${relative}"
  mkdir -p -- "$(dirname "$target")"
  download_file "${raw_base_url}/${package_path}" "$target"
  [[ $(wc -c < "$target" | tr -d '[:space:]') == "$expected_size" ]] || fail "Size mismatch: ${package_path}"
  [[ $(sha256_file "$target") == "$expected_hash" ]] || fail "SHA-256 mismatch: ${package_path}"
done < "$manifest_before"

download_file "$manifest_url" "$manifest_after"
cmp -s "$manifest_before" "$manifest_after" || fail "Manifest changed during installation."
assert_profile_preflight "$candidate"

profile_source_root="$candidate"
if (( profiles_only == 0 )); then
  [[ ! -L "$destination" ]] || fail "Refusing to replace a redirected skill path: ${destination}"
  [[ ! -e "$destination" || -d "$destination" ]] || fail "Existing skill path is not a directory: ${destination}"
  [[ ! -e "$backup_path" ]] || fail "Unexpected backup collision: ${backup_path}"
  if [[ -d "$destination" ]]; then
    mv -- "$destination" "$backup_path"
    existing_moved=1
  fi
  mv -- "$candidate" "$destination"
  candidate_installed=1
  profile_source_root="$destination"
fi

profiles_changed=0
profiles_unchanged=0
for profile_file in "${profile_files[@]}"; do
  source_profile="${profile_source_root}/assets/agent-profiles/${profile_file}"
  target_profile="${agent_home}/${profile_file}"
  source_hash=$(sha256_file "$source_profile")
  if [[ -e "$target_profile" ]]; then
    target_hash=$(sha256_file "$target_profile")
    if [[ "$source_hash" == "$target_hash" ]]; then
      profiles_unchanged=$((profiles_unchanged + 1))
      continue
    fi
    cp -p -- "$target_profile" "${profile_backup_root}/${profile_file}"
    printf '%s\n' "$profile_file" >> "$replaced_profiles"
  else
    printf '%s\n' "$profile_file" >> "$created_profiles"
  fi
  temp_profile="${agent_home}/.${profile_file}.ams-new.$$"
  cp -- "$source_profile" "$temp_profile"
  chmod 600 "$temp_profile" 2>/dev/null || true
  mv -f -- "$temp_profile" "$target_profile"
  [[ $(sha256_file "$target_profile") == "$source_hash" ]] || fail "Profile post-write verification failed: ${profile_file}"
  profiles_changed=$((profiles_changed + 1))
done

committed=1
if (( profiles_only == 1 )); then
  printf 'Installed the AMS profile registry bootstrap only.\n'
  printf 'Skill installation: unchanged (managed separately).\n'
else
  printf 'Installed Adaptive Master-Subagent Orchestration.\n'
  printf 'Skill: %s\n' "$destination"
fi
printf 'Repository ref: %s\n' "$repo_ref"
printf 'Profiles: %s (%s changed, %s unchanged)\n' "$agent_home" "$profiles_changed" "$profiles_unchanged"
printf 'Installation complete. Start a new Codex thread before using newly installed profiles.\n'
