import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnDestroy, OnInit } from '@angular/core';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);

  protected apps: AppCard[] = [];
  protected loading = true;
  protected error = '';
  protected gameServers: GameServer[] = [];
  protected gameServerLoading: string | null = null;
  private refreshInterval: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.loadApps();
    this.loadGameServers();
    this.refreshInterval = setInterval(() => {
      this.loadApps();
      this.loadGameServers();
    }, 30000);
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) clearInterval(this.refreshInterval);
  }

  protected trackByUrl(_: number, app: AppCard): string {
    return app.url;
  }

  protected trackByGame(_: number, gs: GameServer): string {
    return gs.game;
  }

  protected isOnline(status: string): boolean {
    return status === 'Online';
  }

  protected isRunning(gs: GameServer): boolean {
    return gs.status === 'running';
  }

  protected gsLabel(gs: GameServer): string {
    if (gs.status === 'running') return 'Running';
    if (gs.status === 'not_found') return 'Not Ready';
    return 'Stopped';
  }

  protected toggleGameServer(gs: GameServer): void {
    if (this.gameServerLoading) return;
    this.gameServerLoading = gs.game;
    const action = gs.status === 'running' ? 'stop' : 'start';
    this.http.post(`/api/game-servers/${gs.game}/${action}`, {}).subscribe({
      next: () => {
        this.loadGameServers();
        this.gameServerLoading = null;
      },
      error: () => {
        this.gameServerLoading = null;
      }
    });
  }

  private loadApps(): void {
    this.http.get<AppResponse>('/api/apps').subscribe({
      next: ({ apps }) => {
        this.apps = apps;
        this.loading = false;
      },
      error: () => {
        this.error = 'Could not load apps from the backend.';
        this.loading = false;
      }
    });
  }

  private loadGameServers(): void {
    this.http.get<GameServersResponse>('/api/game-servers').subscribe({
      next: ({ gameServers }) => { this.gameServers = gameServers; },
      error: () => {}
    });
  }
}

interface AppResponse {
  apps: AppCard[];
}

interface AppCard {
  name: string;
  url: string;
  imageUrl: string;
  description: string;
  status: string;
}

interface GameServersResponse {
  gameServers: GameServer[];
}

interface GameServer {
  game: string;
  displayName: string;
  containerName: string;
  status: string;
}
