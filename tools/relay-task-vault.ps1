[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Set", "Status", "Submit", "SubmitBatch", "Remove")]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[a-z0-9-]+$")]
    [string]$Profile,

    [string]$BrandId,
    [string]$Title = "",
    [string]$Body,
    [string]$BodyFile,
    [string[]]$ImagePath,
    [string]$ScheduleFor,
    [string]$ManifestPath,
    [string[]]$ConnectionId,
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

function Get-RelayIdempotencyKey([string]$Prefix, [string]$Value) {
    $bytes = [Text.Encoding]::UTF8.GetBytes("$Prefix`:$Value")
    $hash = [Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return "relay-$Prefix-" + ([Convert]::ToHexString($hash)).ToLowerInvariant()
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
    $config = @{
        base_url = $RelayBaseUrl.TrimEnd("/")
        brand_id = $BrandId
        token = $token
        connection_ids = @($ConnectionId | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    } | ConvertTo-Json -Compress
    [IO.File]::WriteAllText($VaultPath, (Protect-VaultValue $config), [Text.Encoding]::ASCII)
    Set-PrivateAcl $VaultPath
    Write-Host "Perfil '$Profile' guardado para esta cuenta de Windows. El token no se ha mostrado ni guardado en el repositorio."
    exit 0
}

if ($Action -eq "Status") {
    $config = Get-ProfileConfig
    $connections = @($config.connection_ids) -join ", "
    Write-Output ("Perfil: {0}`nMarca: {1}`nCanales: {2}`nAPI: {3}`nEstado: listo" -f $Profile, $config.brand_id, $connections, $config.base_url)
    exit 0
}

if ($Action -eq "Remove") {
    if (-not (Test-Path -LiteralPath $VaultPath)) { throw "No existe el perfil '$Profile'." }
    Remove-Item -LiteralPath $VaultPath -Force
    Write-Host "Perfil '$Profile' eliminado."
    exit 0
}

function Get-RelayMediaAsset($Config, [string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "No existe la imagen '$Path'."
    }
    $extension = [IO.Path]::GetExtension($Path).ToLowerInvariant()
    $contentType = @{ ".jpg" = "image/jpeg"; ".jpeg" = "image/jpeg"; ".png" = "image/png" }[$extension]
    if (-not $contentType) { throw "Solo se admiten imágenes JPG, JPEG o PNG." }
    $file = Get-Item -LiteralPath $Path
    if ($file.Length -gt 10MB) { throw "La imagen '$Path' supera el límite de 10 MiB." }

    $checksum = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    $intent = Invoke-RelayJson $Config "POST" "/api/v1/media/upload-intents/" @{
        brand_id = $Config.brand_id
        filename = $file.Name
        content_type = $contentType
        size_bytes = $file.Length
        checksum = $checksum
    }
    $uploadHeaders = @{}
    $intent.upload_headers.psobject.Properties | ForEach-Object { $uploadHeaders[$_.Name] = [string]$_.Value }
    if ($uploadHeaders.ContainsKey("Content-Type")) { $uploadHeaders.Remove("Content-Type") }
    Invoke-WebRequest -Uri $intent.upload_url -Method Put -Headers $uploadHeaders -ContentType $contentType -InFile $file.FullName | Out-Null
    Invoke-RelayJson $Config "POST" "/api/v1/media/$($intent.asset.id)/confirm/" $null | Out-Null
    return [string]$intent.asset.id
}

function Submit-RelayItem($Config, [string]$ItemTitle, [string]$ItemBody, [string[]]$ItemImagePaths, [string]$ItemScheduleFor, [string]$ItemKey = "") {
    if ([string]::IsNullOrWhiteSpace($ItemBody)) { throw "Cada contenido requiere texto." }
    if (@($ItemImagePaths).Count -lt 1 -or @($ItemImagePaths).Count -gt 10) {
        throw "Cada contenido requiere entre una y diez imágenes."
    }
    $assetIds = @($ItemImagePaths | ForEach-Object { Get-RelayMediaAsset $Config $_ })
    $postKey = if ($ItemKey) { Get-RelayIdempotencyKey "post" $ItemKey } else { [guid]::NewGuid().ToString() }
    $post = Invoke-RelayJson $Config "POST" "/api/v1/posts/" @{
        brand_id = $Config.brand_id
        title = $ItemTitle
        body = $ItemBody
        media_asset_ids = $assetIds
    } @{ "Idempotency-Key" = $postKey }

    if ([string]::IsNullOrWhiteSpace($ItemScheduleFor)) {
        return [pscustomobject]@{ id = $post.id; state = $post.state; title = $post.title; publications = @() }
    }
    $scheduledFor = [DateTimeOffset]::Parse($ItemScheduleFor).ToString("o")
    if (@($Config.connection_ids).Count -eq 0) {
        throw "El perfil no tiene canales configurados. Vuelve a ejecutar Set con -ConnectionId para Facebook e Instagram."
    }
    $approved = Invoke-RelayJson $Config "POST" "/api/v1/posts/$($post.id)/approve/" $null
    $connectionIndex = 0
    $publications = @(
        $Config.connection_ids | ForEach-Object {
            $connectionIndex++
            $publicationKey = if ($ItemKey) {
                Get-RelayIdempotencyKey "publication" "$ItemKey`:$connectionIndex"
            } else { [guid]::NewGuid().ToString() }
            Invoke-RelayJson $Config "POST" "/api/v1/publications/" @{
                post_variant_id = $approved.default_variant_id
                channel_connection_id = $_
                scheduled_for = $scheduledFor
            } @{ "Idempotency-Key" = $publicationKey }
        }
    )
    return [pscustomobject]@{ id = $post.id; state = $approved.state; title = $post.title; publications = $publications }
}

$config = Get-ProfileConfig
if ($Action -eq "Submit") {
    if ($BodyFile) {
        if (-not (Test-Path -LiteralPath $BodyFile -PathType Leaf)) { throw "No existe -BodyFile." }
        $Body = Get-Content -LiteralPath $BodyFile -Raw
    }
    $result = Submit-RelayItem $config $Title $Body $ImagePath $ScheduleFor
    $publicationCount = @($result.publications).Count
    Write-Output ("Contenido enviado a Relay`nID: {0}`nEstado: {1}`nPublicaciones programadas: {2}`nTítulo: {3}" -f $result.id, $result.state, $publicationCount, $result.title)
    exit 0
}

if (-not $ManifestPath -or -not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "SubmitBatch requiere un manifiesto JSON existente con -ManifestPath."
}
try { $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json }
catch { throw "El manifiesto no contiene JSON válido." }
$items = @($manifest.items)
if ($items.Count -eq 0) { throw "El manifiesto no contiene items." }
$manifestDirectory = Split-Path -Parent (Resolve-Path -LiteralPath $ManifestPath)
$results = @()
foreach ($item in $items) {
    if ([string]::IsNullOrWhiteSpace([string]$item.id)) { throw "Cada item del manifiesto requiere un id estable." }
    if ([string]::IsNullOrWhiteSpace([string]$item.scheduled_for)) { throw "Cada item del manifiesto requiere scheduled_for." }
    $paths = @($item.image_paths)
    if ($paths.Count -eq 0 -and $item.image_path) { $paths = @($item.image_path) }
    $resolvedPaths = @($paths | ForEach-Object {
        if ([IO.Path]::IsPathRooted($_)) { $_ } else { Join-Path $manifestDirectory $_ }
    })
    $results += Submit-RelayItem $config ([string]$item.title) ([string]$item.body) $resolvedPaths ([string]$item.scheduled_for) ([string]$item.id)
}
$results | Select-Object id, state, title, @{ Name = "publicaciones_programadas"; Expression = { @($_.publications).Count } } | Format-Table -AutoSize
Write-Output ("Lote completado: {0} contenidos enviados a Relay." -f $results.Count)
