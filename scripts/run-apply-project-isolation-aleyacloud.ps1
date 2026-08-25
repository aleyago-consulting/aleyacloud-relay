$ErrorActionPreference = 'Stop'

# Requiere una TTY porque sudo solicitara la credencial local de jorge.
$sshConfig = 'C:\Users\Jorge\.ssh\config'
ssh.exe -tt -F $sshConfig aleyacloud 'bash /home/jorge/apply-project-isolation-aleyacloud.sh'
$exitCode = $LASTEXITCODE
Write-Host "`nEl guion remoto termino con codigo $exitCode."
