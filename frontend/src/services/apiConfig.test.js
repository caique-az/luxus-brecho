import { describe, it, expect, vi, afterEach } from 'vitest';

// O módulo resolve a base no import, então cada caso recarrega com env própria
const loadConfig = async () => {
  vi.resetModules();
  return import('./apiConfig');
};

describe('apiConfig', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('usa VITE_API_URL quando definido', async () => {
    vi.stubEnv('VITE_API_URL', 'http://192.168.0.20:5000');

    const { API_BASE_URL, API_URL } = await loadConfig();

    expect(API_BASE_URL).toBe('http://192.168.0.20:5000');
    expect(API_URL).toBe('http://192.168.0.20:5000/api');
  });

  it('não duplica /api quando a env var já traz o sufixo', async () => {
    vi.stubEnv('VITE_API_URL', 'http://192.168.0.20:5000/api');

    const { API_URL } = await loadConfig();

    expect(API_URL).toBe('http://192.168.0.20:5000/api');
  });

  it('ignora barra final na env var', async () => {
    vi.stubEnv('VITE_API_URL', 'http://192.168.0.20:5000/');

    const { API_URL } = await loadConfig();

    expect(API_URL).toBe('http://192.168.0.20:5000/api');
  });

  it('em dev, deriva a base do host que serviu a página', async () => {
    vi.stubEnv('VITE_API_URL', '');
    vi.stubEnv('DEV', true);

    const { API_BASE_URL } = await loadConfig();

    expect(API_BASE_URL).toBe(`http://${window.location.hostname}:5000`);
  });

  it('respeita VITE_API_PORT na derivação', async () => {
    vi.stubEnv('VITE_API_URL', '');
    vi.stubEnv('DEV', true);
    vi.stubEnv('VITE_API_PORT', '8000');

    const { API_URL } = await loadConfig();

    expect(API_URL).toBe(`http://${window.location.hostname}:8000/api`);
  });
});
