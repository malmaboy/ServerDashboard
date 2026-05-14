# ServerDashboard

Dashboard para monitorização do servidor doméstico, com integração Proxmox VE, alertas Discord e atualizações em tempo real via SSE.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.12, FastAPI, sse-starlette |
| Frontend | Angular 19 (standalone), nginx |
| Infraestrutura | Docker Compose |
| CI/CD | GitHub Actions (self-hosted runner) |

## Funcionalidades

- **Apps** — monitorização de serviços HTTP com badge de latência (rápido / médio / lento)
- **Proxmox VE** — estado do host (CPU, RAM, uptime), lista de VMs e LXCs com controlo (start / stop / reboot), storage, tarefas recentes
- **Alertas de recursos** — notificação Discord quando RAM ≥ 85% ou storage ≥ 80%
- **Alertas de serviço** — notificação Discord quando um serviço passa de Online → Offline ou vice-versa
- **Game servers** — listagem de servidores de jogos ativos
- **Real-time** — todos os dados atualizados via SSE (Server-Sent Events) a cada 15 segundos, sem polling manual

## Configuração

### Apps monitorizadas

Edita `backend/app/app_config.py`:

```python
APP_CARDS = [
    {"name": "Jellyfin", "url": "http://...", "imageUrl": "...", "description": "Media server"},
]
```

### Variáveis de ambiente

Cria `backend/.env` com base em `backend/.env.example`:

```env
PROXMOX_HOST=192.168.x.x
PROXMOX_PORT=8006
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=...
PROXMOX_NODE=pve
ALLOWED_ORIGIN=http://192.168.x.x:8081
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

> O ficheiro `.env` **nunca deve ser commitado** — está incluído no `.gitignore`.

## Correr localmente

```bash
docker compose up --build
```

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:8081 |
| Backend | http://localhost:8000/api/health |

## Deploy (CI/CD)

O deploy é feito automaticamente por GitHub Actions ao fazer push para `main`.

O workflow:
1. Faz checkout do código para o self-hosted runner
2. Sincroniza para `~/deploy/serverdashboard/` via rsync (exclui `.env`)
3. Injeta o `.env` a partir dos GitHub Secrets
4. Faz build e deploy com `docker compose up -d`
5. Verifica health checks em `/api/health` e na porta 8081

### Configurar secrets no GitHub (uma vez)

```bash
gh secret set --env-file backend/.env --repo malmaboy/ServerDashboard
```

Secrets necessários: `PROXMOX_HOST`, `PROXMOX_PORT`, `PROXMOX_USER`, `PROXMOX_PASSWORD`, `PROXMOX_NODE`, `ALLOWED_ORIGIN`, `DISCORD_WEBHOOK_URL`.
