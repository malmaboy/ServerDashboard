import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject } from '@angular/core';

@Component({
  selector: 'app-root',
  imports: [CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  private readonly http = inject(HttpClient);

  protected apps: AppCard[] = [];
  protected loading = true;
  protected error = '';

  constructor() {
    this.loadApps();
  }

  protected trackByUrl(_: number, app: AppCard): string {
    return app.url;
  }

  private loadApps(): void {
    const apiUrl = '/api/apps';

    this.http.get<AppResponse>(apiUrl).subscribe({
      next: ({ apps }) => {
        this.apps = apps;
        this.loading = false;
      },
      error: () => {
        this.error = 'Nao foi possivel carregar as apps do backend.';
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
