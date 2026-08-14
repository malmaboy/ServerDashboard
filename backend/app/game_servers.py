import docker
from docker.errors import NotFound
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()

GAME_CONFIGS: dict[str, dict] = {
    "palworld": {
        "container_name": "palworld-server",
        "display_name": "Palworld",
        "image": "thijsvanloef/palworld-server-docker:latest",
        "ports": {"8211/udp": 8211, "27015/udp": 27015},
        "environment": {
            "PUID": "1000",
            "PGID": "1000",
            "PORT": "8211",
            "PLAYERS": "4",
            "MULTITHREADING": "true",
            "RCON_ENABLED": "false",
            "ADMIN_PASSWORD": "changeme",
            "COMMUNITY": "false",
            "SERVER_NAME": "HomeServer Palworld",
            "SERVER_DESCRIPTION": "Servidor privado",
            "TZ": "Europe/Lisbon",
        },
        "volumes": {
            "/home/docker-host-debian/stacks/GameServers/palworld/data": {
                "bind": "/palworld",
                "mode": "rw",
            }
        },
        "mem_limit": "4g",
        "nano_cpus": int(3.0 * 1e9),
    },
    "project-zomboid": {
        "container_name": "zomboid-server",
        "display_name": "Project Zomboid",
        "image": "ich777/steamcmd:pzserver",
        "ports": {"16261/udp": 16261, "16262/udp": 16262, "8766/udp": 8766},
        "environment": {
            "PUID": "1000",
            "PGID": "1000",
            "MAX_PLAYERS": "4",
            "SERVER_NAME": "HomeServer",
            "SERVER_PASSWORD": "",
            "ADMIN_PASSWORD": "changeme",
            "TZ": "Europe/Lisbon",
            "GAME_PARAMS": "-Xmx3g -Xms2g",
        },
        "volumes": {
            "/home/docker-host-debian/stacks/GameServers/project-zomboid/data": {
                "bind": "/serverdata",
                "mode": "rw",
            }
        },
        "mem_limit": "4g",
        "nano_cpus": int(3.0 * 1e9),
    },
    "project-zomboid-b42": {
        "container_name": "zomboid-b42-server",
        "display_name": "Project Zomboid B42",
        "image": "cyrale/project-zomboid",
        "ports": {"16261/udp": 16271, "16262/udp": 16272, "8766/udp": 8776},
        "environment": {
            "MAX_PLAYERS": "4",
            "SERVER_NAME": "HomeServer",
            "SERVER_PASSWORD": "",
            "ADMIN_PASSWORD": "changeme",
            "TZ": "Europe/Lisbon",
            "MEMORY": "3072m",
            "BRANCH": "unstable",
            "SERVER_BRANCH": "unstable",
        },
        "volumes": {
            "/home/docker-host-debian/stacks/GameServers/project-zomboid-b42/data/Zomboid": {
                "bind": "/home/linuxgsm/Zomboid",
                "mode": "rw",
            },
            "/home/docker-host-debian/stacks/GameServers/project-zomboid-b42/data/serverfiles": {
                "bind": "/home/linuxgsm/serverfiles",
                "mode": "rw",
            },
        },
        "mem_limit": "4g",
        "nano_cpus": int(3.0 * 1e9),
    },
}


def _client() -> docker.DockerClient:
    try:
        return docker.from_env()
    except Exception as exc:
        raise HTTPException(503, f"Docker daemon unavailable: {exc}")


def _container_status(client: docker.DockerClient, name: str) -> str:
    try:
        return client.containers.get(name).status
    except NotFound:
        return "not_found"


def list_game_servers() -> list[dict]:
    """Sync helper — safe to call from a thread pool."""
    try:
        client = docker.from_env()
    except Exception:
        return []
    return [
        {
            "game": game,
            "displayName": cfg["display_name"],
            "containerName": cfg["container_name"],
            "status": _container_status(client, cfg["container_name"]),
        }
        for game, cfg in GAME_CONFIGS.items()
    ]


@router.get("/api/game-servers")
def get_game_servers() -> dict:
    return {"gameServers": list_game_servers()}


@router.post("/api/game-servers/{game}/start")
def start_game_server(game: str) -> dict:
    if game not in GAME_CONFIGS:
        raise HTTPException(404, "Unknown game server")
    client = _client()

    for other, other_cfg in GAME_CONFIGS.items():
        if other != game:
            try:
                c = client.containers.get(other_cfg["container_name"])
                if c.status == "running":
                    c.stop(timeout=30)
            except NotFound:
                pass

    cfg = GAME_CONFIGS[game]
    try:
        container = client.containers.get(cfg["container_name"])
        if container.status != "running":
            container.start()
    except NotFound:
        client.containers.run(
            cfg["image"],
            name=cfg["container_name"],
            detach=True,
            restart_policy={"Name": "unless-stopped"},
            ports=cfg["ports"],
            environment=cfg["environment"],
            volumes=cfg["volumes"],
            mem_limit=cfg["mem_limit"],
            nano_cpus=cfg["nano_cpus"],
        )

    return {"status": "started", "game": game}


@router.post("/api/game-servers/{game}/stop")
def stop_game_server(game: str) -> dict:
    if game not in GAME_CONFIGS:
        raise HTTPException(404, "Unknown game server")
    client = _client()
    try:
        client.containers.get(GAME_CONFIGS[game]["container_name"]).stop(timeout=30)
        return {"status": "stopped", "game": game}
    except NotFound:
        raise HTTPException(404, "Container not found")


_CONTROL_PAGE = """<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Game Servers</title>
<style>
  :root { color-scheme: dark; }
  body { font-family: system-ui, sans-serif; background: #111; color: #eee; margin: 0; padding: 1.5rem; }
  h1 { font-size: 1.1rem; font-weight: 600; margin: 0 0 1rem; }
  .card { display: flex; align-items: center; justify-content: space-between; gap: 1rem;
          background: #1c1c1c; border: 1px solid #2a2a2a; border-radius: 8px;
          padding: 0.9rem 1.1rem; margin-bottom: 0.7rem; }
  .name { font-weight: 500; }
  .status { font-size: 0.8rem; opacity: 0.7; }
  .status.running { color: #4ade80; }
  .status.exited { color: #f87171; }
  .actions button { border: none; border-radius: 6px; padding: 0.45rem 0.9rem; font-size: 0.85rem;
                     cursor: pointer; margin-left: 0.4rem; }
  .start { background: #22c55e; color: #06210f; }
  .stop { background: #ef4444; color: #2a0a0a; }
  button:disabled { opacity: 0.35; cursor: default; }
  .note { font-size: 0.75rem; opacity: 0.6; margin-top: 1rem; }
</style>
</head>
<body>
<h1>Game Servers</h1>
<div id="list">A carregar…</div>
<p class="note">Só um servidor corre de cada vez — iniciar um pára os outros.</p>
<script>
async function fetchServers() {
  const res = await fetch('/api/game-servers');
  const data = await res.json();
  render(data.gameServers || []);
}

function render(servers) {
  const list = document.getElementById('list');
  list.innerHTML = '';
  for (const s of servers) {
    const running = s.status === 'running';
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div>
        <div class="name">${s.displayName}</div>
        <div class="status ${s.status}">${s.status}</div>
      </div>
      <div class="actions">
        <button class="start" ${running ? 'disabled' : ''} data-game="${s.game}" data-action="start">Iniciar</button>
        <button class="stop" ${running ? '' : 'disabled'} data-game="${s.game}" data-action="stop">Parar</button>
      </div>`;
    list.appendChild(card);
  }
  list.querySelectorAll('button').forEach((btn) => {
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      try {
        await fetch(`/api/game-servers/${btn.dataset.game}/${btn.dataset.action}`, { method: 'POST' });
      } finally {
        await fetchServers();
      }
    });
  });
}

fetchServers();
setInterval(fetchServers, 5000);
</script>
</body>
</html>
"""


@router.get("/control", response_class=HTMLResponse)
def control_page() -> str:
    return _CONTROL_PAGE
