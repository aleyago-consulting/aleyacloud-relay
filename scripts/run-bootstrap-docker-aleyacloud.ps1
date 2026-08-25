$ErrorActionPreference = 'Stop'

# La clave dedicada de Codex no permite PTY; sudo requiere la clave personal ya
# validada en la fase 2, sin reenviar agentes.
$sshConfig = 'C:\Users\Jorge\.ssh\config'
ssh.exe -tt -F $sshConfig aleyacloud 'bash /home/jorge/bootstrap-docker-aleyacloud.sh'
$exitCode = $LASTEXITCODE
Write-Host "`nEl guion remoto termino con codigo $exitCode. Conserva esta ventana abierta hasta recibir la validacion final."
