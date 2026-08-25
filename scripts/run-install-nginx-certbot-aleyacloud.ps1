$ErrorActionPreference = 'Stop'

$sshConfig = 'C:\Users\Jorge\.ssh\config'
$acmeEmail = 'soporte@aleyacloud.com'
ssh.exe -tt -F $sshConfig aleyacloud "bash /home/jorge/install-nginx-certbot-aleyacloud.sh $acmeEmail"
$exitCode = $LASTEXITCODE
Write-Host "`nEl guion remoto termino con codigo $exitCode."
