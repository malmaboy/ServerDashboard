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
  protected vmActionLoading: string | null = null;
  protected raspberryPi: RaspberryPiStats | null = null;
  protected raspberryPi2: RaspberryPiStats | null = null;
  protected piContainerLoading: string | null = null;
  protected pi2ContainerLoading: string | null = null;
  protected ups: UpsSummary | null = null;
  protected gpu: GpuStats | null = null;

  ngOnInit(): void { this.connectSSE(); }
  ngOnDestroy(): void { this.eventSource?.close(); }

  protected trackByUrl(_: number, a: AppCard): string { return a.url; }
  protected trackByGame(_: number, g: GameServer): string { return g.game; }
  protected trackByVmid(_: number, v: PveVM): number { return v.vmid; }
  protected trackByStorage(_: number, s: PveStorage): string { return s.name; }
  protected trackByDisk(_: number, d: PhysicalDisk): string { return d.dev; }
  protected trackByKey(_: number, a: Alert): string { return a.key; }
  protected trackByUpid(_: number, t: Task): string { return t.starttime + t.type + t.id; }

  protected onImgError(event: Event): void {
    const img = event.target as HTMLImageElement;
    img.style.display = 'none';
    img.parentElement?.classList.add('img-fallback');
  }

  protected isOnline(status: string): boolean { return status === 'Online'; }
  protected isRunning(gs: GameServer): boolean { return gs.status === 'running'; }

  protected upsStatusLabel(ups: UpsSummary): string {
    if (ups.lowBattery) return 'Low Battery';
    if (ups.onBattery) return 'On Battery';
    return 'Online';
  }

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
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    return d > 0 ? `${d}d ${h}h` : `${h}h`;
  }

  protected ramPct(vm: PveVM): number {
    return vm.ram_max_gb ? Math.round((vm.ram_used_gb / vm.ram_max_gb) * 100) : 0;
  }

  protected storageWarn(pct: number): boolean { return pct >= 80; }

  protected latencyClass(ms: number | null): string {
    if (ms === null) return '';
    if (ms < 150) return 'fast';
    if (ms < 500) return 'medium';
    return 'slow';
  }

  protected taskTimeLabel(starttime: number): string {
    const diff = Math.floor(Date.now() / 1000) - starttime;
    if (diff < 60) return `${diff}s atrás`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m atrás`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h atrás`;
    return `${Math.floor(diff / 86400)}d atrás`;
  }

  protected taskDurationLabel(duration: number | null): string {
    if (duration === null) return '';
    if (duration < 60) return `${duration}s`;
    return `${Math.floor(duration / 60)}m ${duration % 60}s`;
  }

  // ── VM control ────────────────────────────────────────────────────────────

  protected canStart(vm: PveVM): boolean { return vm.status === 'stopped'; }
  protected canStop(vm: PveVM): boolean { return vm.status === 'running'; }
  protected canReboot(vm: PveVM): boolean { return vm.status === 'running'; }
  protected isVmLoading(vmid: number): boolean {
    return this.vmActionLoading?.startsWith(`${vmid}-`) ?? false;
  }

  protected controlVm(vm: PveVM, action: 'start' | 'stop' | 'reboot'): void {
    if (this.vmActionLoading) return;
    this.vmActionLoading = `${vm.vmid}-${action}`;
    this.http.post(`/api/proxmox/vms/${vm.vmid}/${action}?vm_type=${vm.type}`, {}).subscribe({
      next: () => { this.vmActionLoading = null; },
      error: () => { this.vmActionLoading = null; }
    });
  }

  // ── Raspberry Pi containers ───────────────────────────────────────────────

  protected piPortsLabel(ports: string[]): string { return ports.join(' · '); }
  protected piImageLabel(image: string): string { return image.split(':')[0]; }

  protected controlPiContainer(name: string, action: 'start' | 'stop'): void {
    if (this.piContainerLoading) return;
    this.piContainerLoading = name;
    this.http.post(`/api/raspberry-pi/containers/${name}/${action}`, {}).subscribe({
      next: () => { this.piContainerLoading = null; },
      error: () => { this.piContainerLoading = null; }
    });
  }

  protected controlPi2Container(name: string, action: 'start' | 'stop'): void {
    if (this.pi2ContainerLoading) return;
    this.pi2ContainerLoading = name;
    this.http.post(`/api/raspberry-pi-2/containers/${name}/${action}`, {}).subscribe({
      next: () => { this.pi2ContainerLoading = null; },
      error: () => { this.pi2ContainerLoading = null; }
    });
  }

  // ── Game servers ──────────────────────────────────────────────────────────

  protected toggleGameServer(gs: GameServer): void {
    if (this.gameServerLoading) return;
    this.gameServerLoading = gs.game;
    const action = gs.status === 'running' ? 'stop' : 'start';
    this.http.post(`/api/game-servers/${gs.game}/${action}`, {}).subscribe({
      next: () => { this.gameServerLoading = null; },
      error: () => { this.gameServerLoading = null; }
    });
  }

  // ── SSE ───────────────────────────────────────────────────────────────────

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
      this.zone.run(() => { this.proxmox = JSON.parse(e.data) as ProxmoxSummary; });
    });

    this.eventSource.addEventListener('game-servers', (e: MessageEvent) => {
      this.zone.run(() => {
        this.gameServers = (JSON.parse(e.data) as GameServersResponse).gameServers;
      });
    });

    this.eventSource.addEventListener('raspberry-pi', (e: MessageEvent) => {
      this.zone.run(() => {
        this.raspberryPi = (JSON.parse(e.data) as { raspberryPi: RaspberryPiStats | null }).raspberryPi;
      });
    });

    this.eventSource.addEventListener('raspberry-pi-2', (e: MessageEvent) => {
      this.zone.run(() => {
        this.raspberryPi2 = (JSON.parse(e.data) as { raspberryPi2: RaspberryPiStats | null }).raspberryPi2;
      });
    });

    this.eventSource.addEventListener('ups', (e: MessageEvent) => {
      this.zone.run(() => {
        this.ups = (JSON.parse(e.data) as { ups: UpsSummary | null }).ups;
      });
    });

    this.eventSource.addEventListener('gpu', (e: MessageEvent) => {
      this.zone.run(() => {
        this.gpu = (JSON.parse(e.data) as { gpu: GpuStats | null }).gpu;
      });
    });

    this.eventSource.onerror = () => {
      this.zone.run(() => { if (this.loading) this.error = 'Connecting to backend...'; });
      this.eventSource?.close();
      setTimeout(() => this.connectSSE(), 5000);
    };
  }
}

// ── Interfaces ────────────────────────────────────────────────────────────────

interface AppResponse { apps: AppCard[]; }
interface AppCard { name: string; url: string; imageUrl: string; description: string; status: string; latencyMs: number | null; }
interface GameServersResponse { gameServers: GameServer[]; }
interface GameServer { game: string; displayName: string; containerName: string; status: string; }

interface PveVM {
  vmid: number; name: string; status: string;
  cpu: number; ram_used_gb: number; ram_max_gb: number;
  type: 'qemu' | 'lxc';
}

interface PveStorage {
  name: string; type: string;
  total_gb: number; used_gb: number; avail_gb: number; pct: number;
}

interface Alert { key: string; level: 'critical' | 'warning'; message: string; }

interface Task {
  type: string; type_label: string; id: string; user: string;
  status: 'ok' | 'failed' | 'running';
  starttime: number; duration_secs: number | null;
}

interface DiskPartition {
  name: string; service: string;
  total_gb: number; used_gb: number; pct: number;
  source: 'proxmox' | 'mount';
  error?: string;
}

interface PhysicalDisk {
  dev: string; label: string; model: string; size_gb: number;
  type: string; health: string;
  partitions: DiskPartition[];
}

interface ProxmoxSummary {
  host: { cpu: number; ram_used_gb: number; ram_total_gb: number; uptime_seconds: number; };
  vms: PveVM[]; lxcs: PveVM[]; storage: PveStorage[];
  disks: PhysicalDisk[];
  alerts: Alert[]; tasks: Task[];
}

interface PiContainer { name: string; status: string; image: string; ports: string[]; }

interface RaspberryPiStats {
  cpu: number;
  ram_used_gb: number;
  ram_total_gb: number;
  uptime_seconds: number;
  containers: PiContainer[];
}

interface UpsSummary {
  name: string;
  status: string;
  onBattery: boolean;
  lowBattery: boolean;
  batteryCharge: number | null;
  batteryVoltage: number | null;
  inputVoltage: number | null;
  outputVoltage: number | null;
  load: number | null;
  temperature: number | null;
  beeperStatus: string | null;
  firmware: string | null;
}

interface GpuStats {
  name: string;
  gpuUtilPercent: number;
  memUtilPercent: number;
  vramUsedMb: number;
  vramTotalMb: number;
  temperatureC: number;
  powerW: number;
}
