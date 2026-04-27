/**
 * XHR 封装，支持 upload progress 事件（fetch 不支持）。
 *
 * @param url - 目标 URL
 * @param formData - multipart/form-data body
 * @param onProgress - progress 回调，传入 0-100 整数百分比
 * @returns 解析后的 JSON body（成功 2xx）；失败抛 { status, detail } 形态错误
 */
export interface UploadError {
  status: number;
  detail: string;
}

export function uploadWithProgress<T>(
  url: string,
  formData: FormData,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);

    if (onProgress) {
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      });
    }

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as T);
        } catch {
          resolve(xhr.responseText as unknown as T);
        }
      } else {
        let detail = 'unknown';
        try {
          detail = JSON.parse(xhr.responseText).detail ?? xhr.responseText;
        } catch {
          detail = xhr.responseText || `HTTP ${xhr.status}`;
        }
        const err: UploadError = { status: xhr.status, detail };
        reject(err);
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('网络错误：上传失败'));
    });

    xhr.send(formData);
  });
}
