const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

async function request(path, options) {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) throw new Error((await response.text()) || `Request failed (${response.status})`);
  return response.json();
}

function uploadWithProgress(path, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}${path}`);
    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable || !onProgress) return;
      const percent = Math.round((event.loaded / event.total) * 100);
      // Once the bytes are fully sent, there's no further percentage to report --
      // transcription itself can still take a while server-side with no progress signal
      // for it, so report that as indeterminate (null) rather than getting stuck at a
      // stale "100%" for however long the server takes to actually respond.
      onProgress(percent < 100 ? percent : null);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try { resolve(JSON.parse(xhr.responseText)); }
        catch { reject(new Error('Received an invalid response from the server.')); }
      } else {
        reject(new Error(xhr.responseText || `Request failed (${xhr.status})`));
      }
    };
    xhr.onerror = () => reject(new Error('Network error during upload.'));
    xhr.send(formData);
  });
}

export const api = {
  list: () => request('/transcriptions'),
  search: (filename) => request(`/search?filename=${encodeURIComponent(filename)}`),
  transcribe: (files, onProgress) => {
    const body = new FormData();
    files.forEach((file) => body.append('file', file));
    return uploadWithProgress('/transcribe', body, onProgress);
  },
};
