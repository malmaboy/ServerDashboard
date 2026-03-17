from typing import TypedDict


class AppCard(TypedDict):
    name: str
    url: str
    imageUrl: str
    description: str
    status: str


# Edita esta lista com as tuas apps deployed no Proxmox.
APP_CARDS: list[AppCard] = [
    {
        "name": "Portainer",
        "url": "http://192.168.1.117:9000/#!/home",
        "imageUrl": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1400&q=80",
        "description": "Centro rapido para gerir containers, stacks Docker e operacoes do teu homelab num unico painel.",
        "status": "Online",
    },
    {
        "name": "Garden Assistant",
        "url": "http://192.168.1.117:3001/home",
        "imageUrl": "https://images.unsplash.com/photo-1466692476868-aef1dfb1e735?auto=format&fit=crop&w=1400&q=80",
        "description": "Painel dedicado ao jardim com automacoes, sensores e controlo diario mais claro e acessivel.",
        "status": "Online",
    },
    {
        "name": "Proxmox VE",
        "url": "https://192.168.1.200:8006/",
        "imageUrl": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=1400&q=80",
        "description": "Consola principal da tua infraestrutura virtualizada para gerir VMs, LXCs, storage e rede.",
        "status": "Online",
    },
    {
        "name": "NAS Dashboard",
        "url": "http://192.168.1.210:8080/",
        "imageUrl": "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?auto=format&fit=crop&w=1400&q=80",
        "description": "Vista central para armazenamento, utilizacao de discos e saude geral do teu servidor NAS.",
        "status": "Online",
    },
    {
        "name": "Home Assistant",
        "url": "http://192.168.1.121:8123/",
        "imageUrl": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1400&q=80",
        "description": "Hub da casa inteligente com acesso rapido a automacoes, dispositivos e rotinas do dia a dia.",
        "status": "Online",
    },
]
