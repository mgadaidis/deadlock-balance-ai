// Single axios instance with a tiny in-memory GET cache.
//
// Refresh still clears the cache, but ordinary page switches can reuse already
// loaded data instantly instead of waiting a few seconds for the same endpoints.
import axios from 'axios';

const client = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: { 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
});

const getCache = new Map();

function cacheKey(url, config = {}) {
  return `${url}::${JSON.stringify(config.params || {})}`;
}

function cachedGet(url, config = {}) {
  const key = cacheKey(url, config);
  if (getCache.has(key)) {
    return Promise.resolve(getCache.get(key));
  }
  return client.get(url, config).then((r) => {
    getCache.set(key, r.data);
    return r.data;
  });
}

function clearApiCache() {
  getCache.clear();
}

export const api = {
  // ---- heroes ----
  listHeroes:   () => cachedGet('/heroes'),
  latestStats:  () => cachedGet('/heroes/stats'),
  heroHistory:  (id) => cachedGet(`/heroes/${id}/stats`),
  heroAbilities:(id) => cachedGet(`/heroes/${id}/abilities`),

  // ---- balance / recommendations ----
  balanceFlags:   (verdict) =>
    cachedGet('/balance/flags', { params: verdict ? { verdict } : {} }),
  balanceSummary: () => cachedGet('/balance/summary'),
  metaShift:      () => cachedGet('/balance/meta-shift'),

  // ---- items ----
  items:    (params) => cachedGet('/items', { params }),
  tierList: () => cachedGet('/items/tier-list'),
  itemRecommendations: () => cachedGet('/items/recommendations'),

  // ---- simulator ----
  simulate: (payload) => client.post('/predict', payload).then((r) => r.data),
  modelStatus: () => cachedGet('/predict/model-status'),

  // ---- pipeline ----
  refresh: () => client.post('/refresh').then((r) => {
    clearApiCache();
    return r.data;
  }),
};

export { clearApiCache };
