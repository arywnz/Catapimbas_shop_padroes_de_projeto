Write-Host "Iniciando build dos containers de teste (E-Commerce Python)..." -ForegroundColor Cyan

# Test order_service
Write-Host "Testando order_service..." -ForegroundColor Yellow
docker build -t order-service-test ./order_service
if ($LASTEXITCODE -ne 0) {
    Write-Host "Falha no build do order_service de teste!" -ForegroundColor Red
    exit 1
}
docker run --rm order-service-test python -m unittest discover -s . -p "*_test.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Falha nos testes do order_service!" -ForegroundColor Red
    exit 1
}

# Test notification_service
Write-Host "Testando notification_service..." -ForegroundColor Yellow
docker build -t notification-service-test ./notification_service
if ($LASTEXITCODE -ne 0) {
    Write-Host "Falha no build do notification-service de teste!" -ForegroundColor Red
    exit 1
}
docker run --rm notification-service-test python -m unittest discover -s . -p "*_test.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Falha nos testes do notification-service!" -ForegroundColor Red
    exit 1
}

Write-Host "Todos os testes em Python do E-Commerce passaram com sucesso dentro do Docker!" -ForegroundColor Green
