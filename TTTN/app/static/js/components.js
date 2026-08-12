import { routeUrl } from './router.js?v=2';

export const escapeHtml = (value = '') => String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
export const number = value => Number(value || 0).toLocaleString('vi-VN');
export const date = value => value ? new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(value)) : 'Chưa rõ ngày';
export const monogram = name => String(name || 'WC').split(/\s+/).filter(Boolean).slice(0, 2).map(word => word[0]).join('').toUpperCase();

export function pageHeader(eyebrow, title, description, actions = '') {
  return `<section class="page-heading reveal"><div><span class="eyebrow">${escapeHtml(eyebrow)}</span><h1>${escapeHtml(title)}</h1><p>${escapeHtml(description)}</p></div>${actions ? `<div class="heading-actions">${actions}</div>` : ''}</section>`;
}

export function metricCard(label, value, note, accent = '') {
  return `<article class="metric-card ${accent}"><div class="metric-label"><span>${escapeHtml(label)}</span><i></i></div><strong>${number(value)}</strong><p>${escapeHtml(note)}</p></article>`;
}

export function teamMark(team, size = '') {
  return `<span class="team-mark ${size}" aria-hidden="true">${escapeHtml(monogram(team?.name))}</span>`;
}

export function skeleton(kind = 'cards', count = 6) {
  return `<section class="loading-page"><div class="skeleton heading-skeleton"></div><div class="${kind === 'rows' ? 'skeleton-rows' : 'card-grid'}">${Array.from({ length: count }, () => `<div class="skeleton ${kind === 'rows' ? 'row-skeleton' : 'card-skeleton'}"></div>`).join('')}</div></section>`;
}

export function emptyState(title, message, href = '#/dashboard', action = 'Về dashboard') {
  return `<section class="state-card"><span class="state-orbit">○</span><h2>${escapeHtml(title)}</h2><p>${escapeHtml(message)}</p><a class="button primary" href="${href}">${escapeHtml(action)} <span>→</span></a></section>`;
}

export function errorState(error) {
  return `<section class="state-card error"><span class="state-orbit">!</span><h2>Không thể tải dữ liệu</h2><p>${escapeHtml(error?.message || 'Máy chủ đang bận. Vui lòng thử lại.')}</p><button class="button primary" data-action="retry">Thử lại <span>↻</span></button></section>`;
}

export function pagination({ page, pageSize, received, path, query = {} }) {
  const previous = Math.max(1, page - 1);
  const next = page + 1;
  return `<nav class="pagination" aria-label="Phân trang">
    <a class="page-button ${page <= 1 ? 'disabled' : ''}" href="${routeUrl(path, { ...query, page: previous })}" aria-disabled="${page <= 1}">← Trước</a>
    <span>TRANG <strong>${page}</strong></span>
    <a class="page-button ${received < pageSize ? 'disabled' : ''}" href="${routeUrl(path, { ...query, page: next })}" aria-disabled="${received < pageSize}">Sau →</a>
  </nav>`;
}

export function horizontalBars(items, labelKey, valueKey, color = 'lime') {
  if (!items?.length) return '<p class="muted">Chưa có dữ liệu biểu đồ.</p>';
  const max = Math.max(...items.map(item => Number(item[valueKey]) || 0), 1);
  return `<div class="horizontal-chart ${color}">${items.map((item, index) => `<div class="bar-row">
    <span class="bar-rank">${String(index + 1).padStart(2, '0')}</span>
    <span class="bar-label">${escapeHtml(item[labelKey])}</span>
    <span class="bar-track"><i style="--bar:${Math.max(3, (Number(item[valueKey]) / max) * 100)}%"></i></span>
    <strong>${number(item[valueKey])}</strong>
  </div>`).join('')}</div>`;
}

export function verticalBars(items) {
  if (!items?.length) return '<p class="muted">Chưa có dữ liệu theo năm.</p>';
  const max = Math.max(...items.map(item => Number(item.value) || 0), 1);
  return `<div class="vertical-chart">${items.map((item, index) => `<div class="year-column" title="${item.tournament_year}: ${item.value} bàn">
    <strong>${number(item.value)}</strong><i style="--height:${Math.max(4, item.value / max * 100)}%"></i><span>${index % 3 === 0 || index === items.length - 1 ? item.tournament_year : '·'}</span>
  </div>`).join('')}</div>`;
}

export function sectionTitle(kicker, title, link = '') {
  return `<div class="section-title"><div><span>${escapeHtml(kicker)}</span><h2>${escapeHtml(title)}</h2></div>${link ? `<a href="${link}">Xem tất cả →</a>` : ''}</div>`;
}

export function filtersForm(fields, submitLabel = 'Áp dụng') {
  return `<form class="filter-bar" id="filterForm">${fields.join('')}<button class="button primary" type="submit">${escapeHtml(submitLabel)}</button><a class="button ghost" href="${location.hash.split('?')[0]}">Đặt lại</a></form>`;
}

export const selectField = (name, label, options, value = '') => `<label><span>${escapeHtml(label)}</span><select name="${name}"><option value="">Tất cả</option>${options.map(option => `<option value="${escapeHtml(option.value)}" ${String(option.value) === String(value) ? 'selected' : ''}>${escapeHtml(option.label)}</option>`).join('')}</select></label>`;
export const searchField = (name, label, value = '', placeholder = '') => `<label class="grow"><span>${escapeHtml(label)}</span><input name="${name}" value="${escapeHtml(value)}" placeholder="${escapeHtml(placeholder)}"></label>`;

export function bindFilterForm(path) {
  const form = document.querySelector('#filterForm');
  if (!form) return;
  form.addEventListener('submit', event => {
    event.preventDefault();
    const params = Object.fromEntries(new FormData(form));
    location.hash = routeUrl(path, { ...params, page: 1 }).slice(1);
  });
}
