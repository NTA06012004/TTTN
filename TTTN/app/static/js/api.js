const API_ROOT = '/api/v1';

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function queryString(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, value);
  });
  const result = search.toString();
  return result ? `?${result}` : '';
}

export async function api(path, params, options = {}) {
  const response = await fetch(`${API_ROOT}${path}${queryString(params)}`, {
    headers: { Accept: 'application/json' },
    signal: options.signal,
  });
  if (!response.ok) {
    let message = 'Không thể tải dữ liệu từ máy chủ.';
    try {
      const payload = await response.json();
      message = typeof payload.detail === 'string' ? payload.detail : message;
    } catch {}
    throw new ApiError(message, response.status);
  }
  return response.json();
}

export const endpoints = {
  overview: () => api('/statistics/overview'),
  tournaments: () => api('/tournaments'),
  tournament: year => api(`/tournaments/${year}`),
  tournamentOverview: year => api(`/tournaments/${year}/overview`),
  tournamentTeams: year => api(`/tournaments/${year}/teams`),
  standings: (year, snapshot = 'final') => api(`/tournaments/${year}/standings`, { snapshot }),
  teams: params => api('/teams', params),
  team: id => api(`/teams/${id}`),
  players: params => api('/players', params),
  player: id => api(`/players/${id}`),
  matches: params => api('/matches', params),
  matchStages: () => api('/matches/stages'),
  match: id => api(`/matches/${id}`),
  news: params => api('/news', params),
  article: id => api(`/news/${id}`),
  search: params => api('/search', params),
  teamStats: (metric, params) => api(`/statistics/teams/${metric}`, params),
  playerStats: (metric, params) => api(`/statistics/players/${metric}`, params),
  matchStats: (metric, params) => api(`/statistics/matches/${metric}`, params),
  goalsByYear: () => api('/statistics/tournaments/goals'),
};
