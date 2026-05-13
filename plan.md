# ServerDashboard — Plano de Melhorias

> Criado: 2026-05-13  
> Estado: Em planeamento

---

## 1. Segurança & Configuração (Urgente)

| # | Problema | Ficheiro | Solução |
|---|----------|----------|---------|
| S1 | CORS aberto para toda a gente (`allow_origins=["*"]`) | `backend/app/main.py` | Restringir ao hostname/IP do frontend |
| S2 | SSL verification desligado (`verify=False`) | `backend/app/main.py:54` | Usar `verify=True` ou CA bundle local |
| S3 | IPs, portas e passwords hardcoded | `app_config.py`, `game_servers.py` | Mover para `.env` + `python-dotenv` |
| S4 | Backend corre como root no Docker | `backend/Dockerfile` | Adicionar `USER 1000:1000` |
| S5 | Docker socket exposto sem restrição | `docker-compose.yml` | Limitar com socket proxy (tecnologias como `socket-proxy`) |

---

## 2. Performance & Qualidade (Importante)

| # | Problema | Ficheiro | Solução |
|---|----------|----------|---------|
| P1 | Health checks sequenciais — lento | `main.py:51` | Usar `asyncio.gather()` para checks em paralelo |
| P2 | HTTP check aceita 4xx como "Online" | `main.py:31` | Considerar online apenas `status_code < 400` |
| P3 | Sem logging no backend | `main.py` | Adicionar `logging` (structlog ou stdlib) |
| P4 | Erros silenciosos — falhas não chegam ao utilizador | `app.component.ts` | Toasts/notificações de erro no Angular |
| P5 | Sem botão de refresh manual | `app.component.html` | Botão "Refresh" no header |
| P6 | Tudo num componente Angular, sem serviços | `app.component.ts` | Extrair `AppService` e `GameServerService` |
| P7 | Sem testes (specs vazias) | `*.spec.ts` | Adicionar testes unitários básicos |

---

## 3. Features Gerais (Alto Valor)

| # | Feature | Esforço | Impacto |
|---|---------|---------|---------|
| F1 | **Tempo de resposta** de cada serviço (latência em ms) | Baixo | Alto |
| F2 | **Notificações Discord** quando serviço cai (webhook) | Baixo | Alto |
| F3 | **Uptime tracking** — tempo online/offline por serviço | Médio | Alto |
| F4 | **WebSocket** em vez de polling HTTP de 30s | Médio | Médio |
| F5 | **Ver logs de container** Docker diretamente no dashboard | Médio | Médio |
| F6 | **Adicionar/editar serviços via UI** sem tocar em Python | Alto | Médio |

---

## 4. Integração Proxmox (Foco Principal)

A API REST do Proxmox (`https://192.168.1.200:8006/api2/json/`) permite ir muito além de um simples ping.
Autenticação: ticket de sessão (`/access/ticket`) ou API token.

### 4.1 Métricas do Host em Tempo Real

Endpoint Proxmox: `GET /nodes/pve/status`

O que mostrar no dashboard:
- CPU % do host físico
- RAM usada / total (ex: 11.8 GB / 15.0 GB)
- Uptime do Proxmox (ex: 38 dias)
- Load average do sistema

### 4.2 Estado de VMs e LXCs

Endpoints: `GET /nodes/pve/qemu` e `GET /nodes/pve/lxc`

Mostrar uma secção "Infraestrutura Virtual" com:
- Lista de todas as VMs e LXCs com estado (running / stopped)
- CPU % e RAM usada por cada VM/LXC
- VMID, nome e IP
- Botões Start / Stop / Reboot por VM (com confirmação)

VMs e LXCs do inventário actual:
| ID | Nome | Tipo |
|----|------|------|
| 100 | docker-host | VM |
| 101 | home-assistant | VM |
| 103 | pihole-cloud | VM |
| 200 | nas | LXC |
| 201 | infisical | LXC |

### 4.3 Uso de Armazenamento

Endpoint: `GET /nodes/pve/storage`

Mostrar barras de progresso para:
- `local` — 9.8% (6.6 GB / 67.7 GB)
- `local-lvm` — 52.4% (74 GB / 141.2 GB) — **alerta se > 80%**
- `hdd4tb` — <1% (1.7 GB / 1.68 TB)

### 4.4 Tarefas Recentes

Endpoint: `GET /nodes/pve/tasks`

Mostrar uma lista das últimas 5-10 tarefas Proxmox:
- Tipo (backup, migration, start, stop)
- Estado (running, OK, FAILED)
- Data/hora
- Duração

### 4.5 Backups

Endpoint: `GET /nodes/pve/storage/local/content?content=backup`

Mostrar:
- Último backup de cada VM/LXC
- Tamanho do backup
- Data de criação
- Alerta se backup com mais de X dias

### 4.6 Alertas de Recursos

Lógica no backend que alerta quando:
- RAM do host > 85% (`11.8 / 15.0 = 78%` — já próximo)
- Disco `local-lvm` > 80% (52% agora — margem estreita)
- VM parada inesperadamente
- Tarefa Proxmox com estado FAILED

Alertas entregues via:
- Banner no dashboard
- Webhook Discord

### 4.7 Gráficos de Histórico (RRD)

Endpoint: `GET /nodes/pve/rrddata?timeframe=hour`

Proxmox guarda dados RRD de CPU/RAM/rede.  
Mostrar gráficos simples (Chart.js ou ngx-charts) com:
- CPU % do host nas últimas 1h / 24h
- RAM ao longo do tempo
- Tráfego de rede

---

## 5. Arquitectura Proposta (Backend Proxmox)

```
backend/app/
├── main.py               # FastAPI entry point
├── app_config.py         # Configuração de apps (via .env)
├── game_servers.py       # Gestão de game servers
├── proxmox/
│   ├── __init__.py
│   ├── client.py         # Wrapper da API Proxmox (auth + requests)
│   ├── nodes.py          # Endpoints: status, VMs, LXCs, storage
│   ├── tasks.py          # Histórico de tarefas
│   └── alerts.py         # Lógica de alertas de recursos
└── health/
    ├── __init__.py
    └── checker.py        # Health checks paralelos (asyncio.gather)
```

Novo endpoint sugerido: `GET /api/proxmox/summary`
```json
{
  "host": { "cpu": 1.6, "ram_used": 11.8, "ram_total": 15.0, "uptime_days": 38 },
  "vms": [...],
  "lxcs": [...],
  "storage": [...],
  "alerts": [...]
}
```

---

## 6. Ordem de Implementação Sugerida

```
Fase 1 — Base (1-2 sessões)
  S3  → Mover configuração para .env
  P1  → Paralelizar health checks com asyncio.gather
  P2  → Corrigir threshold do HTTP check para < 400
  P3  → Adicionar logging ao backend

Fase 2 — Proxmox Core (2-3 sessões)
  4.1 → Métricas do host (CPU, RAM, uptime)
  4.2 → Lista de VMs e LXCs com estado
  4.3 → Barras de uso de armazenamento

Fase 3 — Features & Alertas (2-3 sessões)
  F1  → Latência de resposta por serviço
  F2  → Notificações Discord (webhook)
  4.6 → Alertas de recursos (RAM, disco)
  4.4 → Tarefas recentes Proxmox

Fase 4 — Polimento (1-2 sessões)
  P4  → Toasts de erro no Angular
  P6  → Extrair serviços Angular
  4.5 → Estado de backups
  4.7 → Gráficos histórico RRD
```

---

## Referências

- [Proxmox API Docs](https://pve.proxmox.com/pve-docs/api-viewer/)
- [Proxmox API Token Setup](https://pve.proxmox.com/wiki/Proxmox_VE_API#API_Tokens)
- [asyncio.gather Python docs](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather)
- Inventário actual: `../proxmox-inventory.md`
