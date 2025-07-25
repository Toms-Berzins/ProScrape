@echo off
echo Stopping Redis server...
echo.

docker stop redis-server
if %errorlevel% == 0 (
    echo Redis server stopped successfully!
) else (
    echo Redis server was not running or error occurred.
)

echo.
echo To restart: run start_redis.bat
echo To remove container: docker rm redis-server
echo.
pause