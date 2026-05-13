$ports = 8000, 3000
foreach ($p in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $procId = $conn.OwningProcess
        Write-Host "Killing process $procId on port $p"
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}
.\scripts\paraworks-docker.ps1
