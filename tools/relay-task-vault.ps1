[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Set", "Status", "Submit", "Remove")]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[a-z0-9-]+$")]
    [string]$Profile,

    [string]$BrandId,
    [string]$Title = "",
    [string]$Body,
    [string]$BodyFile,
    [string]$ImagePath,
    [string]$RelayBaseUrl = "https://relay.aleyacloud.com",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$VaultRoot = Join-Path $env:LOCALAPPDATA "AleyaCloud\Relay\TaskSecrets"
$VaultPath = Join-Path $VaultRoot "$Profile.dat"

function Set-PrivateAcl([string]$Path) {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $acl = New-Object System.Security.AccessControl.FileSecurity
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $identity,
        [System.Security.AccessControl.FileSystemRights]::FullControl,
        [System.Security.AccessControl.AccessControlType]::Allow
    )
    $acl.SetAccessRule($rule)
    Set-Acl -LiteralPath $Path -AclObject $acl
}

function ConvertTo-PlainText([System.Security.SecureString]$Value) {
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}

function Protect-VaultValue([string]$Value) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
    $protected = [Security.Cryptography.ProtectedData]::Protect(
        $bytes,
        $null,
        [Security.Cryptography.DataProtectionScope]::CurrentUser
    )
    return [Convert]::ToBase64String($protected)
}

function Unprotect-VaultValue([string]$Value) {
    $bytes = [Convert]::FromBase64String($Value)
    $plain = [Security.Cryptography.ProtectedData]::Unprotect(
        $bytes,
        $null,
        [Security.Cryptography.DataProtectionScope]::CurrentUser
    )
    return [Text.Encoding]::UTF8.GetString($plain)
}

function Get-ProfileConfig {
    if (-not (Test-Path -LiteralPath $VaultPath)) {
        throw "No existe un secreto para '$Profile'. Un administrador debe ejecutar primero la acción Set."
    }
    try { return (Unprotect-VaultValue (Get-Content -LiteralPath $VaultPath -Raw) | ConvertFrom-Json) }
    catch { throw "No se ha podido abrir el secreto de '$Profile' para este usuario de Windows." }
}

function Invoke-RelayJson($Config, [string]$Method, [string]$Path, $Payload, [hashtable]$ExtraHeaders = @{}) {
    $headers = @{ Authorization = "Bearer $($Config.token)" }
    foreach ($key in $ExtraHeaders.Keys) { $headers[$key] = $ExtraHeaders[$key] }
    $parameters = @{ Uri = "$($Config.base_url)$Path"; Method = $Method; Headers = $headers; ContentType = "application/json" }
    if ($null -ne $Payload) { $parameters.Body = ($Payload | ConvertTo-Json -Compress -Depth 6) }
    return Invoke-RestMethod @parameters
}

if ($Action -eq "Set") {
    if (-not $BrandId) { throw "Set requiere -BrandId." }
    if ((Test-Path -LiteralPath $VaultPath) -and -not $Force) {
        throw "Ya existe un perfil '$Profile'. Usa -Force solo para sustituir su token."
    }
    New-Item -ItemType Directory -Path $VaultRoot -Force | Out-Null
    $secureToken = Read-Host "Pega el token de Relay para $Profile (no se mostrará)" -AsSecureString
    $token = ConvertTo-PlainText $secureToken
    if ([string]::IsNullOrWhiteSpace($token)) { throw "El token no puede estar vacío." }
    $config = @{ base_url = $RelayBaseUrl.TrimEnd("/"); brand_id = $BrandId; token = $token } | ConvertTo-Json -Compress
    [IO.File]::WriteAllText($VaultPath, (Protect-VaultValue $config), [Text.Encoding]::ASCII)
    Set-PrivateAcl $VaultPath
    Write-Host "Perfil '$Profile' guardado para esta cuenta de Windows. El token no se ha mostrado ni guardado en el repositorio."
    exit 0
}

if ($Action -eq "Status") {
    $config = Get-ProfileConfig
    Write-Output ("Perfil: {0}`nMarca: {1}`nAPI: {2}`nEstado: listo" -f $Profile, $config.brand_id, $config.base_url)
    exit 0
}

if ($Action -eq "Remove") {
    if (-not (Test-Path -LiteralPath $VaultPath)) { throw "No existe el perfil '$Profile'." }
    Remove-Item -LiteralPath $VaultPath -Force
    Write-Host "Perfil '$Profile' eliminado."
    exit 0
}

if (-not $ImagePath -or -not (Test-Path -LiteralPath $ImagePath -PathType Leaf)) {
    throw "Submit requiere una imagen existente con -ImagePath."
}
if ($BodyFile) {
    if (-not (Test-Path -LiteralPath $BodyFile -PathType Leaf)) { throw "No existe -BodyFile." }
    $Body = Get-Content -LiteralPath $BodyFile -Raw
}
if ([string]::IsNullOrWhiteSpace($Body)) { throw "Submit requiere -Body o -BodyFile." }

$extension = [IO.Path]::GetExtension($ImagePath).ToLowerInvariant()
$contentType = @{ ".jpg" = "image/jpeg"; ".jpeg" = "image/jpeg"; ".png" = "image/png" }[$extension]
if (-not $contentType) { throw "Solo se admiten imágenes JPG, JPEG o PNG." }
$file = Get-Item -LiteralPath $ImagePath
if ($file.Length -gt 10MB) { throw "La imagen supera el límite de 10 MiB." }

$config = Get-ProfileConfig
$checksum = (Get-FileHash -LiteralPath $ImagePath -Algorithm SHA256).Hash.ToLowerInvariant()
$intent = Invoke-RelayJson $config "POST" "/api/v1/media/upload-intents/" @{
    brand_id = $config.brand_id
    filename = $file.Name
    content_type = $contentType
    size_bytes = $file.Length
    checksum = $checksum
}

$uploadHeaders = @{}
$intent.upload_headers.psobject.Properties | ForEach-Object { $uploadHeaders[$_.Name] = [string]$_.Value }
if ($uploadHeaders.ContainsKey("Content-Type")) { $uploadHeaders.Remove("Content-Type") }
Invoke-WebRequest -Uri $intent.upload_url -Method Put -Headers $uploadHeaders -ContentType $contentType -InFile $file.FullName | Out-Null
Invoke-RelayJson $config "POST" "/api/v1/media/$($intent.asset.id)/confirm/" $null | Out-Null
$post = Invoke-RelayJson $config "POST" "/api/v1/posts/" @{
    brand_id = $config.brand_id
    title = $Title
    body = $Body
    media_asset_ids = @($intent.asset.id)
} @{ "Idempotency-Key" = [guid]::NewGuid().ToString() }

Write-Output ("Borrador creado en Relay`nID: {0}`nEstado: {1}`nTítulo: {2}" -f $post.id, $post.state, $post.title)
