import docker
from docker.errors import NotFound
from fastapi import APIRouter, HTTPException

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


@router.get("/api/game-servers")
def get_game_servers() -> dict:
    client = _client()
    result = []
    for game, cfg in GAME_CONFIGS.items():
        status = _container_status(client, cfg["container_name"])
        result.append({
            "game": game,
            "displayName": cfg["display_name"],
            "containerName": cfg["container_name"],
            "status": status,
        })
    return {"gameServers": result}


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
