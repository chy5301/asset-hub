import { describe, expect, it, vi, beforeEach } from 'vitest';
import { uploadWithProgress } from '@/lib/upload-progress';

type EventHandler = (event: unknown) => void;

interface XhrMock {
  open: ReturnType<typeof vi.fn>;
  send: ReturnType<typeof vi.fn>;
  setRequestHeader: ReturnType<typeof vi.fn>;
  upload: { addEventListener: ReturnType<typeof vi.fn> };
  addEventListener: ReturnType<typeof vi.fn>;
  readyState: number;
  status: number;
  responseText: string;
}

function findHandler(
  mockFn: ReturnType<typeof vi.fn>,
  eventName: string,
): EventHandler {
  const call = mockFn.mock.calls.find((c) => c[0] === eventName);
  if (!call) throw new Error(`handler for ${eventName} not registered`);
  return call[1] as EventHandler;
}

describe('uploadWithProgress', () => {
  let xhrMock: XhrMock;

  beforeEach(() => {
    xhrMock = {
      open: vi.fn(),
      send: vi.fn(),
      setRequestHeader: vi.fn(),
      upload: { addEventListener: vi.fn() },
      addEventListener: vi.fn(),
      readyState: 0,
      status: 0,
      responseText: '',
    };
    vi.stubGlobal(
      'XMLHttpRequest',
      vi.fn(function () {
        return xhrMock;
      }),
    );
  });

  it('resolves with parsed JSON on success', async () => {
    const formData = new FormData();
    const onProgress = vi.fn();
    const promise = uploadWithProgress<{ id: string }>('/api/x', formData, onProgress);

    // 模拟 progress event
    const progressHandler = findHandler(xhrMock.upload.addEventListener, 'progress');
    progressHandler({ lengthComputable: true, loaded: 50, total: 100 });
    expect(onProgress).toHaveBeenCalledWith(50);

    // 模拟 load event
    const loadHandler = findHandler(xhrMock.addEventListener, 'load');
    xhrMock.status = 201;
    xhrMock.responseText = '{"id":"abc"}';
    loadHandler({});

    await expect(promise).resolves.toEqual({ id: 'abc' });
  });

  it('rejects on HTTP error status', async () => {
    const promise = uploadWithProgress('/api/x', new FormData());
    const loadHandler = findHandler(xhrMock.addEventListener, 'load');
    xhrMock.status = 422;
    xhrMock.responseText = '{"detail":"too large"}';
    loadHandler({});
    await expect(promise).rejects.toMatchObject({ status: 422, detail: 'too large' });
  });

  it('rejects on network error', async () => {
    const promise = uploadWithProgress('/api/x', new FormData());
    const errorHandler = findHandler(xhrMock.addEventListener, 'error');
    errorHandler({});
    await expect(promise).rejects.toThrow(/网络错误/);
  });
});
