import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, NgZone, OnDestroy, OnInit } from '@angular/core';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly zone = inject(NgZone);
  private eventSource: EventSource | null = null;

  protected apps: AppCard[] = [];
  protected loading = true;
  protected error = '';
  protected gameServers: GameServer[] = [];
  protected gameServerLoading: string | null = null;
  protected proxmox: ProxmoxSummary | null = null;

  ngOnInit(): void {
    this.connectSSE();
  }

  ngOnDestroy(): void {
    this.eventSource?.close();
  }

  protected trackByUrl(_: number, app: AppCard): string { return app.url; }
  protected trackByGame(_: number, gs: GameServer): string { return gs.game; }
  protected trackByVmid(_: number, vm: PveVM): number { return vm.vmid; }
  protected trackByStorage(_: number, s: PveStorage): string { return s.name; }

  protected isOnline(status: string): boolean { return status === 'Online'; }
  protected isRunning(gs: GameServer): boolean { return gs.status === 'running'; }

  protected gsLabel(gs: GameServer): string {
    if (gs.status === 'running') return 'Running';
    if (gs.status === 'not_found') return 'Not Ready';
    return 'Stopped';
  }

  protected allVms(): PveVM[] {
    if (!this.proxmox) return [];
    return [...this.proxmox.vms, ...this.proxmox.lxcs].sort((a, b) => a.vmid - b.vmid);
  }

  protected uptimeLabel(seconds: number): string {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    return days > 0 ? `${days}d ${hours}h` : `${hours}h`;
  }

  protected ramPct(vm: PveVM): number {
    if (!vm.ram_max_gb) return 0;
    return Math.round((vm.ram_used_gb / vm.ram_max_gb) * 100);
  }

  protected storageWarn(pct: number): boolean { return pct >= 80; }

  protected toggleGameServer(gs: GameServer): void {
    if (this.gameServerLoading) return;
    this.gameServerLoading = gs.game;
    const action = gs.status === 'running' ? 'stop' : 'start';
    this.http.post(`/api/game-servers/${gs.game}/${action}`, {}).subscribe({
      next: () => { this.gameServerLoading = null; },
      error: () => { this.gameServerLoading = null; }
    });
  }

  private connectSSE(): void {
    this.eventSource = new EventSource('/api/events');

    this.eventSource.addEventListener('apps', (e: MessageEvent) => {
      this.zone.run(() => {
        const data = JSON.parse(e.data) as AppResponse;
        this.apps = data.apps;
        this.loading = false;
        this.error = '';
      });
    });

    this.eventSource.addEventListener('proxmox', (e: MessageEvent) => {
      this.zone.run(() => {
        this.proxmox = JSON.parse(e.data) as ProxmoxSummary;
      });
    });

    this.eventSource.addEventListener('game-servers', (e: MessageEvent) => {
      this.zone.run(() => {
        const data = JSON.parse(e.data) as GameServersResponse;
        this.gameServers = data.gameServers;
      });
    });

    this.eventSource.onerror = () => {
      this.zone.run(() => {
        if (this.loading) this.error = 'Connecting to backend...';
      });
      this.eventSource?.close();
      setTimeout(() => this.connectSSE(), 5000);
    };
  }
}

interface AppResponse { apps: AppCard[]; }
interface AppCard { name: string; url: string; imageUrl: string; description: string; status: string; }
interface GameServersResponse { gameServers: GameServer[]; }
interface GameServer { game: string; displayName: string; containerName: string; status: string; }

interface PveVM {
  vmid: number;
  name: string;
  status: string;
  cpu: number;
  ram_used_gb: number;
  ram_max_gb: number;
  type: 'qemu' | 'lxc';
}

interface PveStorage {
  name: string;
  type: string;
  total_gb: number;
  used_gb: number;
  avail_gb: number;
  pct: number;
}

interface ProxmoxSummary {
  host: { cpu: number; ram_used_gb: number; ram_total_gb: number; uptime_seconds: number; };
  vms: PveVM[];
  lxcs: PveVM[];
  storage: PveStorage[];
}
