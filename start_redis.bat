@echo off
echo Starting Redis server with Docker...
echo.

REM Check if Redis container already exists
docker ps -a | findstr redis-server >nul
if %errorlevel% == 0 (
    echo Redis container exists. Starting...
    docker start redis-server
) else (
    echo Creating new Redis container...
    docker run -d --name redis-server -p 6379:6379 redis:7-alpine redis-server --save 20 1 --loglevel warning
)

echo.
echo Redis server started successfully!
echo Connection: redis://localhost:6379/0
echo.
echo To check status: docker ps | findstr redis
echo To stop: docker stop redis-server
echo To view logs: docker logs redis-server
echo.
pause