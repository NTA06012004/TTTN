export class Router {
  constructor(onChange) {
    this.routes = [];
    this.onChange = onChange;
  }

  add(pattern, handler, meta = {}) {
    const keys = [];
    if (pattern === '*') {
      this.routes.push({ pattern, regex: /^.*$/, keys, handler, meta });
      return this;
    }
    const source = pattern.replace(/:[^/]+/g, token => {
      keys.push(token.slice(1));
      return '([^/]+)';
    });
    this.routes.push({ pattern, regex: new RegExp(`^${source}/?$`), keys, handler, meta });
    return this;
  }

  start() {
    addEventListener('hashchange', () => this.resolve());
    if (!location.hash) location.replace('#/dashboard');
    else this.resolve();
  }

  async resolve() {
    const raw = location.hash.slice(1) || '/dashboard';
    const [path, rawQuery = ''] = raw.split('?');
    for (const route of this.routes) {
      const match = path.match(route.regex);
      if (!match) continue;
      const params = Object.fromEntries(route.keys.map((key, index) => [key, decodeURIComponent(match[index + 1])]));
      const query = Object.fromEntries(new URLSearchParams(rawQuery));
      await this.onChange(route, { path, params, query });
      return;
    }
    const fallback = this.routes.find(route => route.pattern === '*');
    if (fallback) await this.onChange(fallback, { path, params: {}, query: {} });
  }
}

export function routeUrl(path, params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, value);
  });
  return `#${path}${search.size ? `?${search}` : ''}`;
}
