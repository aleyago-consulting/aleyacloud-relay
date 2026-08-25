$ErrorActionPreference = 'Stop'

$sshConfig = 'C:\Users\Jorge\.ssh\config'
ssh.exe -tt -F $sshConfig aleyacloud 'bash /home/jorge/prepare-nginx-layout-aleyacloud.sh'
$exitCode = $LASTEXITCODE
Write-Host "`nEl guion remoto termino con codigo $exitCode."
