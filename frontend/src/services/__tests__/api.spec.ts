import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { parseApiError } from '../api';
import type { AxiosError } from 'axios';

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      interceptors: {
        request: { use: vi.fn(), eject: vi.fn() },
        response: { use: vi.fn(), eject: vi.fn() },
      },
    })),
    isAxiosError: vi.fn(),
  },
}));

describe('parseApiError', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('extrai informação de erro axios com response', () => {
    const axiosError = new Error('Request failed') as AxiosError<{ message?: string }>;
    axiosError.response = {
      status: 404,
      data: { message: 'Not Found' },
    } as any;
    (axios.isAxiosError as ReturnType<typeof vi.fn>).mockReturnValue(true);

    const result = parseApiError(axiosError);
    expect(result.status).toBe(404);
    expect(result.message).toBe('Not Found');
    expect(result.timestamp).toBeTruthy();
  });

  it('extrai informação de erro axios sem response data', () => {
    const axiosError = new Error('Network Error') as AxiosError;
    axiosError.response = { status: 500, data: {} } as any;
    (axios.isAxiosError as ReturnType<typeof vi.fn>).mockReturnValue(true);

    const result = parseApiError(axiosError);
    expect(result.status).toBe(500);
    expect(result.message).toBe('Network Error');
  });

  it('trata erro genérico não-axios', () => {
    const genericError = new Error('Algo deu errado');
    (axios.isAxiosError as ReturnType<typeof vi.fn>).mockReturnValue(false);

    const result = parseApiError(genericError);
    expect(result.status).toBe(0);
    expect(result.message).toBe('Algo deu errado');
  });

  it('trata valor desconhecido', () => {
    (axios.isAxiosError as ReturnType<typeof vi.fn>).mockReturnValue(false);

    const result = parseApiError('string error');
    expect(result.status).toBe(0);
    expect(result.message).toBe('Erro desconhecido');
  });
});
