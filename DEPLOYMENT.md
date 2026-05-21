# Adelaide deployment on Windows with Docker

## 1. Prepare the host

1. Install Docker and confirm that `docker` and `docker compose` are available in PowerShell. 
2. Install [MongoDB Database Tools](https://www.mongodb.com/try/download/database-tools)
      and confirm `mongodump` is available in PowerShell; you may also use:
    ```powershell
    winget install MongoDB.DatabaseTools
    ```
3. In the project root, copy `.env.example` to `.env`. 
4. Replace the placeholder values in `.env` with the real `BOT_TOKEN` and `DB_TOKEN`.


## 2. Migrate existing data (Internal Migration)

Run from the project root:

```powershell
.\atlas_migrate.bat
```

This dumps data from Atlas into `./mongo/dump/`.
Only needs to be done once.


## 3. First deployment

Run the stack manually once from the project root:

```powershell
docker compose up -d --build
```

This build uses `compose.yaml`, injects the tokens from `.env`, and mounts `./images` into the container so generated calendars and thumbnails survive container recreation.

## 4. Register automatic startup

Open an elevated PowerShell session in the repository and run:

```powershell
.\deploy\windows\Register-AdelaideTask.ps1
```

Default behavior:

- Creates a Task Scheduler job named `Adelaide Docker Startup`
- Triggers at system startup
- Runs as `SYSTEM`
- Calls `deploy\windows\Start-Adelaide.ps1`, which waits for Docker and then runs `docker compose up -d --remove-orphans`

## 5. If Docker is tied to a user session

If the server uses Docker Desktop in a user session instead of a daemon available at startup, register the task on logon for that account:

```powershell
.\deploy\windows\Register-AdelaideTask.ps1 -TriggerMode Logon -User "YOURMACHINE\\YourUser"
```

On this Windows machine, registering or removing scheduled tasks typically requires an elevated PowerShell session.

## 6. Operations

- Rebuild after code changes: `docker compose up -d --build`
- View container state: `docker compose ps`
- View logs: `docker compose logs -f`
- Startup task log file: `deploy\logs\adelaide-startup.log`