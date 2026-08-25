$ErrorActionPreference = 'Stop'

$sshConfig = 'C:\Users\Jorge\.ssh\config'
ssh.exe -tt -F $sshConfig aleyacloud 'bash /home/jorge/harden-aleyacloud.sh'
$exitCode = $LASTEXITCODE
Write-Host "`nEl guion remoto terminó con código $exitCode. Conserva esta ventana abierta hasta recibir la validación de la segunda conexión SSH."
