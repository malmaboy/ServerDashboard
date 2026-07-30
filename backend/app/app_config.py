from typing import TypedDict


class AppCard(TypedDict):
    name: str
    url: str
    healthUrl: str
    healthType: str  # "http" or "tcp:<port>"
    imageUrl: str
    description: str


APP_CARDS: list[AppCard] = [
    {
        "name": "Proxmox VE",
        "url": "https://192.168.0.200:8006/",
        "healthUrl": "https://192.168.0.200:8006/",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=1400&q=80",
        "description": "Main console for your virtualised infrastructure to manage VMs, LXCs, storage and networking.",
    },
    {
        "name": "Portainer",
        "url": "http://192.168.0.133:9000/#!/home",
        "healthUrl": "http://192.168.0.133:9000/api/status",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1400&q=80",
        "description": "Quick hub to manage containers, Docker stacks and homelab operations in a single panel.",
    },
    {
        "name": "Uptime Kuma",
        "url": "http://192.168.0.133:3002/",
        "healthUrl": "http://192.168.0.133:3002/",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1400&q=80",
        "description": "Uptime monitoring for all homelab services, with status history and alerting.",
    },
    {
        "name": "Nginx Proxy Manager",
        "url": "http://192.168.0.133:81/",
        "healthUrl": "http://192.168.0.133:81/",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1400&q=80",
        "description": "Reverse proxy with SSL termination and custom domain routing for all homelab services.",
    },
    {
        "name": "Garden Assistant",
        "url": "http://192.168.0.133:3001/home",
        "healthUrl": "http://192.168.0.133:3001/",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1466692476868-aef1dfb1e735?auto=format&fit=crop&w=1400&q=80",
        "description": "Dedicated garden panel with automations, sensors and daily control in one place.",
    },
    {
        "name": "Immich",
        "url": "http://192.168.0.133:2283/",
        "healthUrl": "http://192.168.0.133:2283/",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1452587925148-ce544e77e70d?auto=format&fit=crop&w=1400&q=80",
        "description": "Self-hosted photo and video backup with facial recognition and mobile sync.",
    },
    {
        "name": "odysseus",
        "url": "http://192.168.0.212:7000/",
        "healthUrl": "http://192.168.0.212:7000/",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=1400&q=80",
        "description": "Self-hosted AI workspace on ai-local — chat, agents, research, documents, email, notes and calendar.",
    },
    {
        "name": "Open WebUI",
        "url": "http://192.168.0.212:3000/",
        "healthUrl": "http://192.168.0.212:3000/",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1400&q=80",
        "description": "Chat frontend for local Ollama models running on ai-local.",
    },
    {
        "name": "Home Assistant",
        "url": "http://192.168.0.214:8123/",
        "healthUrl": "http://192.168.0.214:8123/",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1400&q=80",
        "description": "Smart home hub with quick access to automations, devices and daily routines.",
    },
    {
        "name": "NAS Dashboard",
        "url": "http://192.168.0.210:8080/",
        "healthUrl": "http://192.168.0.210:8080/",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?auto=format&fit=crop&w=1400&q=80",
        "description": "Central view for storage, disk usage and overall health of your NAS server.",
    },
    {
        "name": "Pi-hole",
        "url": "http://192.168.0.130/admin",
        "healthUrl": "http://192.168.0.130/admin",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=1400&q=80",
        "description": "Network-wide ad blocker and DNS server. Shows query statistics and block lists.",
    },
    {
        "name": "Infisical",
        "url": "http://192.168.0.211/organization/projects",
        "healthUrl": "http://192.168.0.211/",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1555949963-aa79dcee981c?auto=format&fit=crop&w=1400&q=80",
        "description": "Secret management and environment variables for your homelab projects and services.",
    },
    {
        "name": "Raspberry Pi",
        "url": "ssh://user@192.168.0.130",
        "healthUrl": "192.168.0.130:22",
        "healthType": "tcp",
        "imageUrl": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1400&q=80",
        "description": "Raspberry Pi in the garage — Arduino bridge server for IoT sensors and automations.",
    },
    {
        "name": "Raspberry Pi 2",
        "url": "ssh://user@192.168.0.183",
        "healthUrl": "192.168.0.183:22",
        "healthType": "tcp",
        "imageUrl": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1400&q=80",
        "description": "Second Raspberry Pi — 192.168.1.17.",
    },
    {
        "name": "Creality 3D Printer",
        "url": "http://192.168.0.124/#/home",
        "healthUrl": "http://192.168.0.124/",
        "healthType": "http",
        "imageUrl": "https://images.unsplash.com/photo-1642969164999-979483e21601?auto=format&fit=crop&w=1400&q=80",
        "description": "Creality 3D printer — monitoring and control panel for prints, temperatures and status.",
    },
]
