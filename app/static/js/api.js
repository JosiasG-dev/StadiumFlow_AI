/**
 * api.js — wrapper de fetch con manejo uniforme de errores.
 * Usa textContent en todos los lugares donde se muestran datos del servidor.
 */

export const api = {
  async _request(method, url, body) {
    const options = {
      method,
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    };
    if (body !== undefined) options.body = JSON.stringify(body);
    const res = await fetch(url, options);
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data?.error?.message ?? data?.detail ?? `Error ${res.status}`;
      throw new Error(msg);
    }
    return data;
  },

  get(url)            { return this._request('GET',    url);       },
  post(url, body)     { return this._request('POST',   url, body); },
  put(url, body)      { return this._request('PUT',    url, body); },
  delete(url)         { return this._request('DELETE', url);       },
};
