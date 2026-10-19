import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { AppComponent } from './app.component';

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  private listeners: Record<string, (e: MessageEvent) => void> = {};
  onerror: (() => void) | null = null;

  constructor(public url: string) { FakeEventSource.instances.push(this); }
  addEventListener(type: string, fn: (e: MessageEvent) => void): void { this.listeners[type] = fn; }
  close(): void {}
  emit(type: string, data: unknown): void {
    this.listeners[type]({ data: JSON.stringify(data) } as MessageEvent);
  }
}

const PI_STATS = { cpu: 1, ram_used_gb: 1, ram_total_gb: 4, uptime_seconds: 3600, containers: [] };

function bridge(overrides: Record<string, unknown> = {}) {
  return {
    supported: true, state: 'active', socatRunning: true, serialPresent: true,
    serialDevices: ['/dev/ttyACM0'], port: 5555, baud: 9600, desired: true, managed: true,
    ...overrides
  };
}

describe('AppComponent', () => {
  let originalEventSource: typeof EventSource;

  beforeEach(async () => {
    FakeEventSource.instances = [];
    originalEventSource = window.EventSource;
    (window as unknown as { EventSource: unknown }).EventSource = FakeEventSource;

    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();
  });

  afterEach(() => {
    (window as unknown as { EventSource: unknown }).EventSource = originalEventSource;
  });

  function render(bridgeStatus: unknown) {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const es = FakeEventSource.instances[0];
    es.emit('raspberry-pi', { raspberryPi: PI_STATS });
    es.emit('arduino-bridge', { arduinoBridge: bridgeStatus });
    fixture.detectChanges();
    return fixture;
  }

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows the socat bridge as active with the Arduino detected', () => {
    const el = render(bridge()).nativeElement as HTMLElement;
    const text = el.querySelector('.bridge-row')?.textContent ?? '';
    expect(text).toContain('socat ativo');
    expect(text).toContain('Arduino detetado');
    expect(el.querySelector('.bridge-row .vm-btn--stop')).toBeTruthy();
    expect(el.querySelector('.bridge-row .vm-btn--start')).toBeNull();
  });

  it('shows socat stopped and Arduino not detected, with start disabled', () => {
    const el = render(bridge({
      state: 'no_device', socatRunning: false, serialPresent: false, serialDevices: []
    })).nativeElement as HTMLElement;
    const text = el.querySelector('.bridge-row')?.textContent ?? '';
    expect(text).toContain('socat parado');
    expect(text).toContain('Arduino não detetado');
    const start = el.querySelector('.bridge-row .vm-btn--start') as HTMLButtonElement;
    expect(start.disabled).toBeTrue();
  });

  it('shows socat stopped with the Arduino present and allows starting it', () => {
    const fixture = render(bridge({ state: 'stopped', socatRunning: false }));
    const el = fixture.nativeElement as HTMLElement;
    const http = TestBed.inject(HttpTestingController);
    const start = el.querySelector('.bridge-row .vm-btn--start') as HTMLButtonElement;
    expect(start.disabled).toBeFalse();

    start.click();
    const req = http.expectOne('/api/raspberry-pi/bridge/start');
    expect(req.request.method).toBe('POST');
    req.flush({ arduinoBridge: bridge() });
    fixture.detectChanges();

    expect(el.querySelector('.bridge-row')?.textContent).toContain('socat ativo');
    http.verify();
  });

  it('stops the bridge and surfaces agent errors', () => {
    const fixture = render(bridge());
    const el = fixture.nativeElement as HTMLElement;
    const http = TestBed.inject(HttpTestingController);

    (el.querySelector('.bridge-row .vm-btn--stop') as HTMLButtonElement).click();
    http.expectOne('/api/raspberry-pi/bridge/stop')
      .flush({ detail: 'Agente do Raspberry Pi 1 inacessível' }, { status: 502, statusText: 'Bad Gateway' });
    fixture.detectChanges();

    expect(el.querySelector('.bridge-error')?.textContent).toContain('inacessível');
    expect(el.querySelector('.bridge-row')?.textContent).toContain('socat ativo');
    http.verify();
  });

  it('explains that the agent needs updating when bridge management is unsupported', () => {
    const el = render({ supported: false }).nativeElement as HTMLElement;
    expect(el.querySelector('.bridge-row')?.textContent).toContain('atualizar o pi-agent');
    expect(el.querySelector('.bridge-row button')).toBeNull();
  });
});
