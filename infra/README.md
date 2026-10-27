# Docker Compose – Data Safety

## Quick reference

- **Start services**: `docker compose up -d`
- **Stop services while keeping database data**: `docker compose down`  *(do **not** add `-v`)*
- **Stop services and wipe the database** (use only for a fresh dev environment): `docker compose down -v`

## Backing up the PostgreSQL database
```powershell
# Run while the containers are up
docker exec medazone_postgres pg_dump -U medazone medazone > backup_$(Get-Date -Format yyyyMMdd).sql
```

## Restoring a backup
```powershell
cat backup_20260525.sql | docker exec -i medazone_postgres psql -U medazone medazone
```

## Optional: bind‑mount the DB files (visible on host)
Add the following under the `postgres` service in `infra/docker-compose.yml`:
```yaml
    volumes:
      - ./postgres_data:/var/lib/postgresql/data
```
This creates a `postgres_data` folder next to the compose file and stores the DB files there, making them easy to back up manually.

---
**Note:** The PostgreSQL data lives in the Docker named volume `postgres_data`. Deleting the volume (`docker compose down -v`) permanently erases all tables and rows. Avoid that command unless you truly intend to start from scratch.
