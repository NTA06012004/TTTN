import { endpoints } from './js/api.js?v=2';
import { emptyState, errorState, escapeHtml, skeleton, teamMark } from './js/components.js?v=2';
import {
  dashboardPage, matchDetailPage, matchesPage, newsDetailPage, newsPage,
  notFoundPage, playerDetailPage, playersPage, standingsPage, teamDetailPage,
  teamsPage, worldCupDetailPage, worldCupsPage,
} from './js/pages.js?v=2';
import { Router } from './js/router.js?v=2';

const app = document.querySelector('#app');
const sidebar = document.querySelector('#sidebar');
let activeRender = 0;

const router = new Router(async (route, context) => {
  const renderId = ++activeRender;
  app.innerHTML = skeleton(route.meta.skeleton || 'cards', route.meta.count || 6);
  updateChrome(route.meta);
  sidebar.classList.remove('open');
  scrollTo({ top: 0, behavior: 'instant' });
  try {
    const view = await route.handler(context);
    if (renderId !== activeRender) return;
    app.innerHTML = view.html;
    view.mount?.();
    app.focus({ preventScroll: true });
  } catch (error) {
    if (renderId !== activeRender) return;
    app.innerHTML = errorState(error);
    app.querySelector('[data-action="retry"]')?.addEventListener('click', () => router.resolve());
  }
});

router
  .add('/dashboard', dashboardPage, { title: 'Dashboard', nav: 'dashboard', breadcrumb: 'TỔNG QUAN', skeleton: 'cards' })
  .add('/world-cups', worldCupsPage, { title: 'Các kỳ World Cup', nav: 'world-cups', breadcrumb: 'KỲ WORLD CUP' })
  .add('/world-cups/:year', worldCupDetailPage, { title: 'Chi tiết kỳ đấu', nav: 'world-cups', breadcrumb: 'CHI TIẾT KỲ ĐẤU', skeleton: 'rows' })
  .add('/teams', teamsPage, { title: 'Đội tuyển', nav: 'teams', breadcrumb: 'ĐỘI TUYỂN' })
  .add('/teams/:id', teamDetailPage, { title: 'Hồ sơ đội tuyển', nav: 'teams', breadcrumb: 'HỒ SƠ ĐỘI TUYỂN', skeleton: 'rows' })
  .add('/players', playersPage, { title: 'Cầu thủ', nav: 'players', breadcrumb: 'CẦU THỦ' })
  .add('/players/:id', playerDetailPage, { title: 'Hồ sơ cầu thủ', nav: 'players', breadcrumb: 'HỒ SƠ CẦU THỦ', skeleton: 'rows' })
  .add('/matches', matchesPage, { title: 'Trận đấu', nav: 'matches', breadcrumb: 'TRẬN ĐẤU', skeleton: 'rows' })
  .add('/matches/:id', matchDetailPage, { title: 'Chi tiết trận đấu', nav: 'matches', breadcrumb: 'CHI TIẾT TRẬN ĐẤU', skeleton: 'rows' })
  .add('/standings', standingsPage, { title: 'Bảng xếp hạng', nav: 'standings', breadcrumb: 'BẢNG XẾP HẠNG', skeleton: 'rows' })
  .add('/news', newsPage, { title: 'Tin tức', nav: 'news', breadcrumb: 'TIN TỨC' })
  .add('/news/:id', newsDetailPage, { title: 'Chi tiết tin tức', nav: 'news', breadcrumb: 'CHI TIẾT TIN TỨC', skeleton: 'rows' })
  .add('*', notFoundPage, { title: 'Không tìm thấy', breadcrumb: '404' });

function updateChrome(meta = {}) {
  document.title = `${meta.title || 'Atlas'} · World Cup Atlas`;
  document.querySelector('#breadcrumb').innerHTML = `<span>ATLAS</span><b>/</b><strong>${escapeHtml(meta.breadcrumb || meta.title || '')}</strong>`;
  document.querySelectorAll('[data-nav]').forEach(link => link.classList.toggle('active', link.dataset.nav === meta.nav));
}

document.querySelector('#menuButton').addEventListener('click', () => sidebar.classList.toggle('open'));
document.addEventListener('click', event => {
  if (innerWidth <= 900 && sidebar.classList.contains('open') && !sidebar.contains(event.target) && !event.target.closest('#menuButton')) sidebar.classList.remove('open');
});

const dialog = document.querySelector('#searchDialog');
const searchInput = document.querySelector('#globalSearch');
const searchResults = document.querySelector('#searchResults');

function openSearch() {
  if (!dialog.open) dialog.showModal();
  searchResults.innerHTML = `<div class="search-welcome"><span>⌕</span><h3>Tìm trong gần một thế kỷ World Cup</h3><p>Đội tuyển, cầu thủ, trận đấu, kỳ đấu và tin tức — tất cả trong một ô tìm kiếm.</p></div>`;
  setTimeout(() => searchInput.focus(), 50);
}

document.querySelector('#searchButton').addEventListener('click', openSearch);
document.querySelector('#closeSearch').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); openSearch(); }
});

let searchTimer;
searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  const q = searchInput.value.trim();
  if (q.length < 2) {
    searchResults.innerHTML = '<div class="search-welcome"><span>⌕</span><p>Nhập ít nhất 2 ký tự để bắt đầu.</p></div>';
    return;
  }
  searchResults.innerHTML = '<div class="search-loading"><i></i><span>Đang tìm trong kho dữ liệu...</span></div>';
  searchTimer = setTimeout(async () => {
    try {
      const results = await endpoints.search({ q, limit: 5 });
      searchResults.innerHTML = [
        searchGroup('ĐỘI TUYỂN', results.teams, item => `#/teams/${item.id}`, item => `${teamMark(item, 'tiny')}<span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.fifa_code)}</small></span>`),
        searchGroup('CẦU THỦ', results.players, item => `#/players/${item.id}`, item => `<span class="search-avatar">${escapeHtml(item.full_name[0])}</span><span><strong>${escapeHtml(item.full_name)}</strong><small>${escapeHtml(item.nationality?.name || 'Cầu thủ')}</small></span>`),
        searchGroup('TRẬN ĐẤU', results.matches, item => `#/matches/${item.id}`, item => `<span class="search-score">${item.home_score ?? '–'}:${item.away_score ?? '–'}</span><span><strong>${escapeHtml(item.home_team.name)} — ${escapeHtml(item.away_team.name)}</strong><small>${escapeHtml(item.stage)}</small></span>`),
        searchGroup('KỲ WORLD CUP', results.tournaments, item => `#/world-cups/${item.year}`, item => `<span class="search-year">${item.year}</span><span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.host_country || '')}</small></span>`),
        searchGroup('TIN TỨC', results.news, item => `#/news/${item.id}`, item => `<span class="search-year">${item.tournament_year || 'WC'}</span><span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.source)}</small></span>`),
      ].join('') || emptyState('Không có kết quả', 'Hãy thử tên hoặc từ khóa khác.');
      searchResults.querySelectorAll('a').forEach(link => link.addEventListener('click', () => dialog.close()));
    } catch (error) {
      searchResults.innerHTML = `<div class="search-welcome"><span>!</span><p>${escapeHtml(error.message)}</p></div>`;
    }
  }, 260);
});

function searchGroup(title, items, href, content) {
  if (!items?.length) return '';
  return `<section class="search-group"><h4>${title}<span>${items.length}</span></h4>${items.map(item => `<a href="${href(item)}">${content(item)}<b>→</b></a>`).join('')}</section>`;
}

router.start();
