@echo off
REM Docker Development Helper Script for ProScrape (Windows)
REM This script provides convenient commands for Docker-based development

setlocal enabledelayedexpansion

REM Script configuration
set PROJECT_NAME=proscrape
set COMPOSE_FILE=docker-compose.dev.yml
set ENV_FILE=.env.docker

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker and try again.
    exit /b 1
)

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] docker-compose is not installed. Please install it and try again.
    exit /b 1
)

REM Check if environment file exists
if not exist "%ENV_FILE%" (
    echo [WARNING] Environment file %ENV_FILE% not found.
    if exist "%ENV_FILE%.example" (
        echo [INFO] Copying from %ENV_FILE%.example...
        copy "%ENV_FILE%.example" "%ENV_FILE%" >nul
        echo [SUCCESS] Created %ENV_FILE% from example file.
        echo [WARNING] Please review and customize the environment variables in %ENV_FILE%
    ) else (
        echo [ERROR] No environment file found. Please create %ENV_FILE%
        exit /b 1
    )
)

REM Parse command
if "%1"=="" goto show_help
if "%1"=="help" goto show_help
if "%1"=="--help" goto show_help
if "%1"=="-h" goto show_help
if "%1"=="setup" goto setup
if "%1"=="start" goto start_services
if "%1"=="stop" goto stop_services
if "%1"=="restart" goto restart_services
if "%1"=="status" goto show_status
if "%1"=="logs" goto show_logs
if "%1"=="shell" goto open_shell
if "%1"=="build" goto build_images
if "%1"=="rebuild" goto rebuild_images
if "%1"=="clean" goto clean_up
if "%1"=="reset" goto full_reset
if "%1"=="health" goto health_check
if "%1"=="backup" goto backup_db
if "%1"=="restore" goto restore_db
if "%1"=="update" goto update_images

echo [ERROR] Unknown command: %1
echo.
goto show_help

:show_help
echo ProScrape Docker Development Helper (Windows)
echo.
echo Usage: %0 ^<command^> [options]
echo.
echo Commands:
echo   setup           - Initial setup (create env file, pull images)
echo   start           - Start all services
echo   stop            - Stop all services
echo   restart         - Restart all services
echo   status          - Show status of all services
echo   logs [service]  - Show logs (optionally for specific service)
echo   shell [service] - Open shell in service container
echo   build           - Build all Docker images
echo   rebuild         - Force rebuild all images
echo   clean           - Clean up containers and volumes
echo   reset           - Full reset (clean + rebuild + start)
echo   health          - Check health of all services
echo   backup          - Backup database data
echo   restore [file]  - Restore database from backup
echo   update          - Update all images and restart
echo.
echo Services:
echo   api       - FastAPI application
echo   worker    - Celery worker
echo   beat      - Celery beat scheduler
echo   flower    - Celery monitoring
echo   frontend  - Svelte frontend
echo   mongodb   - MongoDB database
echo   redis     - Redis cache/queue
echo   postgres  - PostgreSQL metadata database
echo   nginx     - Nginx reverse proxy
echo.
echo Examples:
echo   %0 setup                    # Initial setup
echo   %0 start                    # Start all services
echo   %0 logs api                 # Show API logs
echo   %0 shell worker             # Open shell in worker container
echo   %0 restart api worker       # Restart specific services
goto end

:setup
echo [INFO] Setting up ProScrape development environment...

echo [INFO] Pulling Docker images...
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" pull

echo [INFO] Creating Docker volumes...
docker volume create proscrape_mongodb_data
docker volume create proscrape_postgres_data
docker volume create proscrape_redis_data

echo [SUCCESS] Setup completed!
echo [INFO] Run '%0 start' to start the development environment.
goto end

:start_services
echo [INFO] Starting ProScrape services...

if "%2"=="" (
    docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" up -d
    echo [SUCCESS] All services started!
) else (
    shift
    docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" up -d %1 %2 %3 %4 %5 %6 %7 %8 %9
    echo [SUCCESS] Services started!
)

echo [INFO] Waiting for services to be ready...
timeout /t 5 >nul

goto show_status

:stop_services
echo [INFO] Stopping ProScrape services...

if "%2"=="" (
    docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" stop
    echo [SUCCESS] All services stopped!
) else (
    shift
    docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" stop %1 %2 %3 %4 %5 %6 %7 %8 %9
    echo [SUCCESS] Services stopped!
)
goto end

:restart_services
echo [INFO] Restarting ProScrape services...

if "%2"=="" (
    docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" restart
    echo [SUCCESS] All services restarted!
) else (
    shift
    docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" restart %1 %2 %3 %4 %5 %6 %7 %8 %9
    echo [SUCCESS] Services restarted!
)

goto show_status

:show_status
echo [INFO] ProScrape service status:
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" ps

echo.
echo [INFO] Service URLs:
echo   API:           http://localhost:8000
echo   Frontend:      http://localhost:3000
echo   Flower:        http://localhost:5555
echo   API Docs:      http://localhost:8000/docs
echo   MongoDB:       mongodb://localhost:27017
echo   Redis:         redis://localhost:6379
echo   PostgreSQL:    postgresql://localhost:5432
goto end

:show_logs
if "%2"=="" (
    echo [INFO] Showing logs for all services...
    docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" logs -f --tail=100
) else (
    echo [INFO] Showing logs for: %2
    docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" logs -f --tail=100 %2
)
goto end

:open_shell
if "%2"=="" (
    echo [ERROR] Please specify a service name
    echo Available services: api, worker, beat, flower, frontend, mongodb, redis, postgres
    exit /b 1
)

set service=%2
echo [INFO] Opening shell in %service% container...

if "%service%"=="api" goto shell_bash
if "%service%"=="worker" goto shell_bash
if "%service%"=="beat" goto shell_bash
if "%service%"=="flower" goto shell_bash
if "%service%"=="frontend" goto shell_sh
if "%service%"=="mongodb" goto shell_mongo
if "%service%"=="redis" goto shell_redis
if "%service%"=="postgres" goto shell_postgres
goto shell_bash

:shell_bash
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" exec %service% /bin/bash
goto end

:shell_sh
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" exec %service% /bin/sh
goto end

:shell_mongo
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" exec %service% mongosh
goto end

:shell_redis
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" exec %service% redis-cli
goto end

:shell_postgres
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" exec %service% psql -U proscrape_user -d proscrape_db
goto end

:build_images
echo [INFO] Building Docker images...
shift
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" build %1 %2 %3 %4 %5 %6 %7 %8 %9
echo [SUCCESS] Images built successfully!
goto end

:rebuild_images
echo [INFO] Force rebuilding Docker images...
shift
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" build --no-cache %1 %2 %3 %4 %5 %6 %7 %8 %9
echo [SUCCESS] Images rebuilt successfully!
goto end

:clean_up
echo [WARNING] This will remove all containers, networks, and volumes!
set /p answer=Are you sure? (y/N): 

if /i "%answer%"=="y" (
    echo [INFO] Cleaning up...
    docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" down -v --remove-orphans
    docker system prune -f
    echo [SUCCESS] Cleanup completed!
) else (
    echo [INFO] Cleanup cancelled.
)
goto end

:full_reset
echo [WARNING] This will perform a full reset: clean + rebuild + start
set /p answer=Are you sure? (y/N): 

if /i "%answer%"=="y" (
    call :clean_up
    call :rebuild_images
    call :start_services
    echo [SUCCESS] Full reset completed!
) else (
    echo [INFO] Reset cancelled.
)
goto end

:health_check
echo [INFO] Checking service health...

REM API health
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [ERROR] API is not responding
) else (
    echo [SUCCESS] API is healthy
)

REM Frontend health
curl -s http://localhost:3000 >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Frontend is not responding
) else (
    echo [SUCCESS] Frontend is healthy
)

REM Flower health
curl -s http://localhost:5555 >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Flower is not responding
) else (
    echo [SUCCESS] Flower is healthy
)

REM Database connections
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" exec -T mongodb mongosh --eval "db.adminCommand('ping')" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] MongoDB is not responding
) else (
    echo [SUCCESS] MongoDB is healthy
)

docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" exec -T redis redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Redis is not responding
) else (
    echo [SUCCESS] Redis is healthy
)

docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" exec -T postgres pg_isready -U proscrape_user >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL is not responding
) else (
    echo [SUCCESS] PostgreSQL is healthy
)
goto end

:backup_db
for /f "tokens=1-3 delims=/" %%a in ("%date%") do set timestamp=%%c%%a%%b
for /f "tokens=1-3 delims=:" %%a in ("%time%") do set timestamp=%timestamp%_%%a%%b%%c
set timestamp=%timestamp: =0%

if not exist "backups" mkdir backups

echo [INFO] Creating database backup...

REM MongoDB backup
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" exec -T mongodb mongodump --db proscrape --archive > "backups\mongodb_backup_%timestamp%.archive"
echo [SUCCESS] MongoDB backup created: backups\mongodb_backup_%timestamp%.archive

REM PostgreSQL backup
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" exec -T postgres pg_dump -U proscrape_user -d proscrape_db > "backups\postgres_backup_%timestamp%.sql"
echo [SUCCESS] PostgreSQL backup created: backups\postgres_backup_%timestamp%.sql
goto end

:restore_db
if "%2"=="" (
    echo [ERROR] Please specify backup file
    exit /b 1
)

set backup_file=%2

if not exist "%backup_file%" (
    echo [ERROR] Backup file not found: %backup_file%
    exit /b 1
)

echo [WARNING] This will overwrite existing database data!
set /p answer=Are you sure? (y/N): 

if /i "%answer%"=="y" (
    echo [INFO] Restoring database from %backup_file%...
    
    echo %backup_file% | findstr ".archive" >nul
    if not errorlevel 1 (
        REM MongoDB restore
        docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" exec -T mongodb mongorestore --db proscrape --archive < "%backup_file%"
        echo [SUCCESS] MongoDB restored successfully!
    ) else (
        echo %backup_file% | findstr ".sql" >nul
        if not errorlevel 1 (
            REM PostgreSQL restore
            docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" exec -T postgres psql -U proscrape_user -d proscrape_db < "%backup_file%"
            echo [SUCCESS] PostgreSQL restored successfully!
        ) else (
            echo [ERROR] Unknown backup file format. Expected .archive (MongoDB) or .sql (PostgreSQL)
        )
    )
) else (
    echo [INFO] Restore cancelled.
)
goto end

:update_images
echo [INFO] Updating Docker images...
docker-compose -f "%COMPOSE_FILE%" --env-file "%ENV_FILE%" pull
call :restart_services
echo [SUCCESS] Images updated and services restarted!
goto end

:end
endlocal