param(
  [switch]$IUnderstandThisIsDisposable
)

$ErrorActionPreference = "Stop"

if (-not $IUnderstandThisIsDisposable) {
  throw "Refusing to run without -IUnderstandThisIsDisposable. Use only with a local disposable Supabase database."
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$migrations = Join-Path $root "migrations"
$files = @(
  "0001_initial_schema.sql",
  "0002_rls_policies.sql",
  "..\local_bootstrap_auth_fixtures.sql",
  "0003_seed_demo_data.sql",
  "0004_fix_membership_consistency_trigger.sql",
  "0005_session_evaluation_finalize.sql",
  "0006_restrict_finalize_rpc_grants.sql",
  "0007_restrict_session_evaluation_table_grants.sql",
  "0003_seed_demo_data.sql"
)

foreach ($file in $files) {
  $path = if ($file.StartsWith("..")) {
    Join-Path $migrations $file
  } else {
    Join-Path $migrations $file
  }
  $resolved = Resolve-Path -LiteralPath $path
  Write-Host "Applying local bootstrap step: $file"
  npx.cmd --yes supabase db query --local --file $resolved
}

Write-Host "Local disposable bootstrap completed. The second seed run is the idempotency check."
