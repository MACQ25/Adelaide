@echo off

:: Load .env file
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="ATLAS_URI" set ATLAS_URI=%%b
)

echo Dumping from Atlas...

mongodump --uri="%ATLAS_URI%" --out=./mongo/dump
if errorlevel 1 (
    echo Dump failed!
    exit /b %errorlevel%
)

echo Dump complete! Now run docker-compose up to restore.