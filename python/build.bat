@echo off
echo Generating requirements.txt...
.venv\Scripts\pipreqs.exe . --force --encoding latin-1 --ignore .venv

echo Building Docker image...
docker build -t adelaide .

echo Done!