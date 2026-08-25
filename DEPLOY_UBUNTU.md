# Ubuntu Deployment Quick Guide

This folder is prepared to be copied to an Ubuntu server.

## 1. Install Docker

On Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git make
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
```

Log out and log back in so the Docker group is applied.

## 2. Configure Environment

```bash
cp .env.example .env
nano .env
```

At minimum change:

```env
DJANGO_SECRET_KEY=change-this-to-a-long-random-value
POSTGRES_PASSWORD=change-this-password
DJANGO_ALLOWED_HOSTS=your-server-ip,your-domain,localhost,127.0.0.1,backend
CORS_ALLOWED_ORIGINS=http://your-server-ip:3000,https://your-domain
```

## 3. Build And Start

```bash
docker compose up --build -d
```

Check logs:

```bash
docker compose logs -f backend
docker compose logs -f worker
```

## 4. Create Admin User

```bash
docker compose exec backend python manage.py createsuperuser
```

## 5. Open UI

- Frontend: `http://SERVER_IP:3000`
- Backend API: `http://SERVER_IP:8000`
- Elasticsearch: `http://SERVER_IP:9200`

## 6. Update Databases

```bash
docker compose exec backend freshclam
docker compose exec backend python manage.py seed_yara_rules
docker compose exec backend grype db update
docker compose exec backend trivy image --download-db-only
```

## Notes

- Do not copy local `.venv`, `node_modules`, `.next`, `db.sqlite3`, or `backend/var` to the server.
- Scanner data, uploads, logs, YARA rules, and ClamAV signatures are stored in Docker volumes.
- Full documentation is in `docs/README.md`.
