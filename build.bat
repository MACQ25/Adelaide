@echo off
echo Building Adelaide image with Docker Compose...
docker compose build

if errorlevel 1 exit /b %errorlevel%

echo Done!