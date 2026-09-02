$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# Load apps/api/.env without printing secrets
# ------------------------------------------------------------

$envFile = Join-Path $PSScriptRoot ".env"

if (-not (Test-Path $envFile)) {
    throw ".env bulunamadi: $envFile"
}

$config = @{}

Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()

    if (
        $line -and
        -not $line.StartsWith("#") -and
        $line.Contains("=")
    ) {
        $parts = $line.Split("=", 2)
        $name = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"').Trim("'")

        $config[$name] = $value
    }
}

$supabaseUrl = $config["SUPABASE_URL"]

if (-not $supabaseUrl) {
    $supabaseUrl = $config["SUPABASE_PROJECT_URL"]
}

# Prefer new Supabase secret key, otherwise legacy service-role key.
$adminKey = $config["SUPABASE_SECRET_KEY"]

if (-not $adminKey) {
    $adminKey = $config["SUPABASE_SERVICE_ROLE_KEY"]
}

if (-not $adminKey) {
    $adminKey = $config["SUPABASE_SERVICE_KEY"]
}

if (-not $supabaseUrl) {
    throw "SUPABASE_URL bulunamadi."
}

if (-not $adminKey) {
    throw "Supabase secret/service-role key bulunamadi."
}

$supabaseUrl = $supabaseUrl.TrimEnd("/")

# ------------------------------------------------------------
# Ask password interactively
# Password is NOT written to .env / source / output.
# ------------------------------------------------------------

$securePassword = Read-Host "Uc development hesabi icin kullanmak istedigin sifreyi gir" -AsSecureString

$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)

try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

if ([string]::IsNullOrWhiteSpace($plainPassword)) {
    throw "Sifre bos olamaz."
}

# ------------------------------------------------------------
# Existing Auth users — UUIDs MUST stay unchanged
# ------------------------------------------------------------

$users = @(
    @{
        Id    = "00000000-0000-0000-0000-000000000201"
        Email = "platform@akademx10.local"
        Role  = "platform"
    },
    @{
        Id    = "00000000-0000-0000-0000-000000000202"
        Email = "hr@northwind.local"
        Role  = "company"
    },
    @{
        Id    = "00000000-0000-0000-0000-000000000203"
        Email = "learner@northwind.local"
        Role  = "learner"
    }
)

# New sb_secret_* keys go in apikey.
# Legacy service_role JWT also needs Authorization Bearer.
$headers = @{
    "apikey"       = $adminKey
    "Content-Type" = "application/json"
}

if (-not $adminKey.StartsWith("sb_secret_")) {
    $headers["Authorization"] = "Bearer $adminKey"
}

Write-Host ""
Write-Host "Supabase Auth development hesaplari guncelleniyor..."
Write-Host ""

foreach ($user in $users) {

    $body = @{
        email         = $user.Email
        password      = $plainPassword
        email_confirm = $true
    } | ConvertTo-Json

    $uri = "$supabaseUrl/auth/v1/admin/users/$($user.Id)"

    try {
        $result = Invoke-RestMethod `
            -Method Put `
            -Uri $uri `
            -Headers $headers `
            -UserAgent "AkademX10-DevAuth-Script/1.0" `
            -Body $body

        if ($result.id -ne $user.Id) {
            throw "Donen UID beklenen UID ile eslesmiyor."
        }

        Write-Host "[PASS] $($user.Role) -> $($result.email) -> $($result.id)"
    }
    catch {
        Write-Host "[FAIL] $($user.Role) -> $($user.Email)"
        Write-Host $_.Exception.Message
        throw
    }
}

# Remove plaintext password from variable after use.
$plainPassword = $null
$securePassword = $null

Write-Host ""
Write-Host "Tamamlandi."
Write-Host ""
Write-Host "Login hesaplari:"
Write-Host "platform@akademx10.local"
Write-Host "hr@northwind.local"
Write-Host "learner@northwind.local"
Write-Host ""
Write-Host "Ucunde de terminalde az once girdigin ayni sifreyi kullan."