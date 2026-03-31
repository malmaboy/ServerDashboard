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
  private refreshInterval: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.loadApps();
    this.refreshInterval = setInterval(() => this.loadApps(), 30000);
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) clearInterval(this.refreshInterval);
  }

  protected trackByUrl(_: number, app: AppCard): string {
    return app.url;
  }

  protected isOnline(status: string): boolean {
    return status === 'Online';
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
