# Proxmox Apps Dashboard

Dashboard simples com:

- Backend em Python (`FastAPI`)
- Frontend em Angular
- Deploy com Docker Compose

## Configurar as apps

Edita a lista `APP_CARDS` em `backend/app/app_config.py`.

Cada entrada suporta:

- `name`
- `url`
- `imageUrl`
- `description`
- `status`

## Correr com Docker

```bash
docker compose up --build
```

Frontend:

```text
http://localhost:8081
```

Backend:

```text
http://localhost:8000/api/apps
```

## Mudar as portas

Podes trocar as portas do host sem partir a comunicacao entre frontend e backend:

```bash
$env:FRONTEND_PORT=9595
$env:BACKEND_PORT=8090
docker compose up --build
```

Frontend:

```text
http://localhost:9595
```

Backend:

```text
http://localhost:8090/api/apps
```
