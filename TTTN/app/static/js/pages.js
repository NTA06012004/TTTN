import { endpoints } from './api.js?v=2';
import {
  bindFilterForm, date, emptyState, escapeHtml, filtersForm, horizontalBars,
  metricCard, number, pageHeader, pagination, searchField, sectionTitle,
  selectField, teamMark, verticalBars,
} from './components.js?v=2';

const PAGE_SIZE = 18;
const cache = { editions: null, teams: null, stages: null };

async function lookups() {
  if (!cache.editions) cache.editions = await endpoints.tournaments();
  if (!cache.teams) cache.teams = await endpoints.teams({ limit: 100 });
  if (!cache.stages) cache.stages = await endpoints.matchStages();
  return cache;
}

const pageOf = query => Math.max(1, Number(query.page) || 1);
const statValue = response => response?.data?.[0]?.value || 0;
const yearsOptions = editions => editions.map(item => ({ value: item.year, label: `World Cup ${item.year}` })).reverse();
const teamOptions = teams => teams.map(item => ({ value: item.id, label: `${item.fifa_code} · ${item.name}` }));

function matchCard(match) {
  const played = match.home_score !== null && match.away_score !== null;
  return `<a class="match-card" href="#/matches/${match.id}">
    <div class="match-card-top"><span>${escapeHtml(match.stage)}</span><time>${date(match.kickoff_at)}</time></div>
    <div class="match-side"><div>${teamMark(match.home_team, 'small')}<strong>${escapeHtml(match.home_team.name)}</strong></div><b>${played ? match.home_score : '–'}</b></div>
    <div class="match-divider"><span>VS</span></div>
    <div class="match-side"><div>${teamMark(match.away_team, 'small')}<strong>${escapeHtml(match.away_team.name)}</strong></div><b>${played ? match.away_score : '–'}</b></div>
    <footer><span>${escapeHtml(match.venue || 'Địa điểm chưa cập nhật')}</span><em>${match.status === 'finished' ? 'ĐÃ KẾT THÚC' : escapeHtml(match.status)}</em></footer>
  </a>`;
}

function teamCard(team) {
  return `<a class="entity-card" href="#/teams/${team.id}">
    <div class="entity-card-top"><small>${escapeHtml(team.fifa_code)}</small><span>→</span></div>
    ${teamMark(team)}<h3>${escapeHtml(team.name)}</h3><p>${escapeHtml(team.confederation || 'Liên đoàn chưa cập nhật')}</p>
  </a>`;
}

function playerCard(player, index = 0) {
  return `<a class="entity-card player" href="#/players/${player.id}">
    <div class="entity-card-top"><small>${String(index + 1).padStart(2, '0')}</small><span>→</span></div>
    <span class="player-avatar">${escapeHtml(player.full_name.split(/\s+/).at(-1)?.[0] || 'P')}</span>
    <h3>${escapeHtml(player.full_name)}</h3><p>${escapeHtml(player.nationality?.name || 'Quốc tịch chưa cập nhật')}</p>
  </a>`;
}

function newsCard(article) {
  return `<a class="news-card" href="#/news/${article.id}">
    <div class="news-year">${article.tournament_year || 'WC'}</div>
    <div><small>${escapeHtml(article.source)} · ${date(article.published_at)}</small><h3>${escapeHtml(article.title)}</h3><p>${escapeHtml((article.summary || 'Đọc nội dung tóm tắt và mở bài viết tại nguồn.').slice(0, 180))}</p><span>Đọc chi tiết →</span></div>
  </a>`;
}

export async function dashboardPage() {
  const [overview, titles, teamGoals, scorers, appearances, years, cardMatches] = await Promise.all([
    endpoints.overview(), endpoints.teamStats('titles', { limit: 7 }), endpoints.teamStats('goals', { limit: 7 }),
    endpoints.playerStats('goals', { limit: 5 }), endpoints.playerStats('matches', { limit: 5 }),
    endpoints.goalsByYear(), endpoints.matchStats('cards', { limit: 4 }),
  ]);
  const totals = overview.data;
  return { html: `
    <div class="dashboard-hero reveal">
      <div class="hero-copy"><span class="eyebrow light">WORLD CUP INTELLIGENCE</span><h1>Một thế kỷ bóng đá.<br><em>Trong từng con số.</em></h1><p>Khám phá dữ liệu trận đấu, cầu thủ, đội tuyển và những câu chuyện định hình giải đấu lớn nhất hành tinh.</p><div><a class="button light" href="#/world-cups">Khám phá lịch sử →</a><a class="text-link" href="#/matches">Xem ${number(totals.matches)} trận đấu</a></div></div>
      <div class="hero-orbit"><div class="orbit-ring one"></div><div class="orbit-ring two"></div><div class="atlas-ball"><span>FIFA</span><strong>WC</strong><small>1930—2026</small></div></div>
      <div class="hero-index">01 <span>/</span> 06</div>
    </div>
    <section class="content-section metric-grid six">${metricCard('Kỳ World Cup', totals.tournaments, 'Từ Uruguay đến Bắc Mỹ', 'lime')}${metricCard('Đội tuyển', totals.teams, 'Các quốc gia từng góp mặt')}${metricCard('Cầu thủ', totals.players, 'Tên tuổi trong kho dữ liệu')}${metricCard('Trận đấu', totals.matches, 'Mỗi trận một câu chuyện')}${metricCard('Bàn thắng', totals.goals, 'Không tính luân lưu')}${metricCard('Tin tức', totals.news, 'Metadata báo chí Việt Nam')}</section>
    <section class="content-section chart-grid">
      <article class="panel chart-panel">${sectionTitle('01 / THÀNH TÍCH', 'Những nhà vô địch', '#/teams')} ${horizontalBars(titles.data, 'team_name', 'value')}</article>
      <article class="panel chart-panel">${sectionTitle('02 / SỨC MẠNH', 'Đội tuyển ghi bàn', '#/teams')} ${horizontalBars(teamGoals.data, 'team_name', 'value', 'gold')}</article>
    </section>
    <section class="content-section panel chart-panel wide">${sectionTitle('03 / DÒNG THỜI GIAN', 'Bàn thắng qua từng kỳ World Cup', '#/world-cups')} ${verticalBars(years.data)}</section>
    <section class="content-section split-grid">
      <article class="panel leaderboard">${sectionTitle('04 / KỶ LỤC', 'Vua phá lưới', '#/players')}${scorers.data.map(row => `<a href="#/players/${row.player_id}"><span>${String(row.rank).padStart(2, '0')}</span><strong>${escapeHtml(row.player_name)}</strong><b>${row.value}<small>BÀN</small></b></a>`).join('')}</article>
      <article class="panel leaderboard">${sectionTitle('05 / BỀN BỈ', 'Ra sân nhiều nhất', '#/players')}${appearances.data.map(row => `<a href="#/players/${row.player_id}"><span>${String(row.rank).padStart(2, '0')}</span><strong>${escapeHtml(row.player_name)}</strong><b>${row.value}<small>TRẬN</small></b></a>`).join('')}</article>
      <article class="panel record-list">${sectionTitle('06 / KỊCH TÍNH', 'Những trận nhiều thẻ', '#/matches')}${cardMatches.data.map(row => `<a href="#/matches/${row.match_id}"><span>${row.tournament_year}</span><div><strong>${escapeHtml(row.home_team)} — ${escapeHtml(row.away_team)}</strong><small>${escapeHtml(row.stage)}</small></div><b>${row.value}</b></a>`).join('')}</article>
    </section>` };
}

export async function worldCupsPage({ query }) {
  const editions = await endpoints.tournaments();
  const page = pageOf(query);
  const pageSize = 9;
  const items = editions.slice((page - 1) * pageSize, page * pageSize);
  return { html: `${pageHeader('01 / KHO LƯU TRỮ', 'Các kỳ World Cup', 'Từ Montevideo 1930 đến Bắc Mỹ 2026 — mỗi kỳ đấu là một chương riêng trong lịch sử bóng đá.')}
    <section class="timeline-rule"><span>1930</span><i></i><b>${editions.length} KỲ ĐẤU</b><i></i><span>2026</span></section>
    <section class="edition-grid">${items.map((edition, index) => `<a class="edition-tile" href="#/world-cups/${edition.year}"><div class="edition-number">${String((page - 1) * pageSize + index + 1).padStart(2, '0')}</div><div class="edition-year">${edition.year}</div><span>${escapeHtml(edition.host_country || 'Đang cập nhật')}</span><footer><small>NHÀ VÔ ĐỊCH</small><strong>${escapeHtml(edition.champion?.name || 'Chưa xác định')}</strong><i>→</i></footer></a>`).join('')}</section>
    ${pagination({ page, pageSize, received: items.length, path: '/world-cups' })}` };
}

export async function worldCupDetailPage({ params }) {
  const year = Number(params.year);
  const [edition, overview, teams, matches, standings, news] = await Promise.all([
    endpoints.tournament(year), endpoints.tournamentOverview(year), endpoints.tournamentTeams(year),
    endpoints.matches({ year, limit: 6 }), endpoints.standings(year), endpoints.news({ tournament_year: year, limit: 4 }),
  ]);
  return { html: `<div class="edition-hero reveal"><div><a href="#/world-cups">← TẤT CẢ KỲ ĐẤU</a><span>${escapeHtml(edition.host_country || 'FIFA WORLD CUP')}</span><h1>${year}</h1><p>${escapeHtml(edition.name)}</p></div><aside><small>NHÀ VÔ ĐỊCH</small><strong>${escapeHtml(edition.champion?.name || 'Chưa xác định')}</strong><small>Á QUÂN</small><strong>${escapeHtml(edition.runner_up?.name || 'Chưa cập nhật')}</strong></aside></div>
    <section class="content-section metric-grid">${metricCard('Đội tuyển', overview.teams_count, `World Cup ${year}`)}${metricCard('Trận đấu', overview.matches_count, 'Toàn bộ vòng đấu')}${metricCard('Cầu thủ', overview.players_count, 'Có tên trong đội hình')}${metricCard('Bàn thắng', overview.goals_count, 'Trong thời gian thi đấu')}${metricCard('Bài viết', overview.news_count, 'Từ báo chí Việt Nam')}</section>
    <section class="content-section detail-copy"><span>VỀ KỲ ĐẤU</span><p>${escapeHtml(edition.overview || `Kho dữ liệu World Cup ${year} đang được tổng hợp từ các nguồn lịch sử có dẫn chứng. Khám phá đội tuyển, trận đấu và các con số đáng nhớ bên dưới.`)}</p></section>
    <section class="content-section">${sectionTitle('ĐỘI TUYỂN', `${teams.length} quốc gia góp mặt`, `#/teams?year=${year}`)}<div class="compact-team-grid">${teams.slice(0, 12).map(item => `<a href="#/teams/${item.team.id}">${teamMark(item.team, 'tiny')}<strong>${escapeHtml(item.team.name)}</strong><span>${item.final_position ? `#${item.final_position}` : '→'}</span></a>`).join('')}</div></section>
    <section class="content-section">${sectionTitle('TRẬN ĐẤU', 'Những cuộc đối đầu', `#/matches?year=${year}`)}${matches.length ? `<div class="match-grid">${matches.map(matchCard).join('')}</div>` : emptyState('Chưa có trận đấu', `Dữ liệu trận đấu ${year} chưa sẵn sàng.`)}</section>
    <section class="content-section">${sectionTitle('BẢNG XẾP HẠNG', 'Thứ hạng theo bảng', `#/standings?year=${year}`)}${standings.length ? standingsTable(standings) : `<div class="inline-empty">Ảnh chụp bảng xếp hạng của kỳ này đang được cập nhật.</div>`}</section>
    <section class="content-section">${sectionTitle('BÁO CHÍ', `World Cup ${year} qua các trang tin`, `#/news?year=${year}`)}${news.length ? `<div class="news-grid">${news.map(newsCard).join('')}</div>` : `<div class="inline-empty">Chưa có bài viết cho kỳ đấu này.</div>`}</section>` };
}

export async function teamsPage({ query }) {
  const { editions } = await lookups();
  const page = pageOf(query);
  let teams;
  if (query.year) {
    const entries = await endpoints.tournamentTeams(query.year);
    teams = entries.map(entry => entry.team).filter(team => !query.q || `${team.name} ${team.fifa_code}`.toLowerCase().includes(query.q.toLowerCase()));
    teams = teams.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  } else {
    teams = await endpoints.teams({ q: query.q, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE });
  }
  const form = filtersForm([searchField('q', 'Tìm đội tuyển', query.q, 'Brazil, Việt Nam...'), selectField('year', 'Kỳ World Cup', yearsOptions(editions), query.year)]);
  return { html: `${pageHeader('02 / QUỐC GIA', 'Đội tuyển', 'Hồ sơ thành tích và hành trình của những đội tuyển từng bước lên sân khấu World Cup.')}${form}
    ${teams.length ? `<section class="entity-grid">${teams.map(teamCard).join('')}</section>${pagination({ page, pageSize: PAGE_SIZE, received: teams.length, path: '/teams', query: { q: query.q, year: query.year } })}` : emptyState('Không tìm thấy đội tuyển', 'Thử thay đổi tên hoặc kỳ World Cup trong bộ lọc.', '#/teams', 'Xóa bộ lọc')}`, mount: () => bindFilterForm('/teams') };
}

export async function teamDetailPage({ params }) {
  const id = Number(params.id);
  const [team, titles, tournaments, goals, wins, matches, players] = await Promise.all([
    endpoints.team(id), endpoints.teamStats('titles', { team_id: id }), endpoints.teamStats('tournaments', { team_id: id }),
    endpoints.teamStats('goals', { team_id: id }), endpoints.teamStats('wins', { team_id: id }),
    endpoints.matches({ team_id: id, limit: 6 }), endpoints.players({ team_id: id, limit: 8 }),
  ]);
  return { html: `<div class="entity-hero reveal">${teamMark(team, 'hero')}<div><a href="#/teams">← ĐỘI TUYỂN</a><span>${escapeHtml(team.fifa_code)} · ${escapeHtml(team.confederation || 'FIFA')}</span><h1>${escapeHtml(team.name)}</h1><p>Hành trình, con người và những con số của ${escapeHtml(team.name)} tại FIFA World Cup.</p></div></div>
    <section class="content-section metric-grid">${metricCard('Vô địch', statValue(titles), 'Danh hiệu World Cup', 'lime')}${metricCard('Tham dự', statValue(tournaments), 'Kỳ World Cup')}${metricCard('Bàn thắng', statValue(goals), 'Được ghi nhận')}${metricCard('Chiến thắng', statValue(wins), 'Bao gồm luân lưu')}</section>
    <section class="content-section">${sectionTitle('TRẬN ĐẤU', 'Các trận gần nhất trong dữ liệu', `#/matches?team=${id}`)}${matches.length ? `<div class="match-grid">${matches.map(matchCard).join('')}</div>` : `<div class="inline-empty">Chưa có trận đấu.</div>`}</section>
    <section class="content-section">${sectionTitle('CẦU THỦ', 'Những gương mặt trong đội hình', `#/players?team=${id}`)}${players.length ? `<div class="entity-grid compact">${players.map(playerCard).join('')}</div>` : `<div class="inline-empty">Chưa có cầu thủ.</div>`}</section>` };
}

export async function playersPage({ query }) {
  const { editions, teams } = await lookups();
  const page = pageOf(query);
  const players = await endpoints.players({ q: query.q, tournament_year: query.year, team_id: query.team, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE });
  const form = filtersForm([searchField('q', 'Tìm cầu thủ', query.q, 'Messi, Pelé, Klose...'), selectField('year', 'Kỳ World Cup', yearsOptions(editions), query.year), selectField('team', 'Đội tuyển', teamOptions(teams), query.team)]);
  return { html: `${pageHeader('03 / NHÂN VẬT', 'Cầu thủ', 'Những con người đã tạo nên ký ức, kỷ lục và cảm xúc của ngày hội bóng đá lớn nhất.')}${form}
    ${players.length ? `<section class="entity-grid">${players.map(playerCard).join('')}</section>${pagination({ page, pageSize: PAGE_SIZE, received: players.length, path: '/players', query: { q: query.q, year: query.year, team: query.team } })}` : emptyState('Không tìm thấy cầu thủ', 'Hãy thử một tên, đội tuyển hoặc kỳ đấu khác.', '#/players', 'Xóa bộ lọc')}`, mount: () => bindFilterForm('/players') };
}

export async function playerDetailPage({ params }) {
  const id = Number(params.id);
  const [player, goals, games, tournaments, matches] = await Promise.all([
    endpoints.player(id), endpoints.playerStats('goals', { player_id: id }), endpoints.playerStats('matches', { player_id: id }),
    endpoints.playerStats('tournaments', { player_id: id }), endpoints.matches({ player_id: id, limit: 8 }),
  ]);
  return { html: `<div class="entity-hero player-hero reveal"><span class="player-avatar hero">${escapeHtml(player.full_name.split(/\s+/).at(-1)?.[0] || 'P')}</span><div><a href="#/players">← CẦU THỦ</a><span>${escapeHtml(player.nationality?.fifa_code || 'FIFA')} · ${escapeHtml(player.nationality?.name || 'Chưa rõ đội tuyển')}</span><h1>${escapeHtml(player.full_name)}</h1><p>Hồ sơ World Cup và những dấu ấn được lưu trong kho dữ liệu lịch sử.</p></div></div>
    <section class="content-section metric-grid">${metricCard('Bàn thắng', statValue(goals), 'Không tính phản lưới', 'lime')}${metricCard('Ra sân', statValue(games), 'Trận đấu')}${metricCard('Tham dự', statValue(tournaments), 'Kỳ World Cup')}</section>
    <section class="content-section">${sectionTitle('HÀNH TRÌNH', 'Các trận đấu đã tham gia', '#/matches')}${matches.length ? `<div class="match-grid">${matches.map(matchCard).join('')}</div>` : `<div class="inline-empty">Chưa có dữ liệu ra sân.</div>`}</section>` };
}

export async function matchesPage({ query }) {
  const { editions, teams, stages } = await lookups();
  const page = pageOf(query);
  const matches = await endpoints.matches({ year: query.year, team_id: query.team, stage: query.stage, limit: 12, offset: (page - 1) * 12 });
  const form = filtersForm([selectField('year', 'Kỳ World Cup', yearsOptions(editions), query.year), selectField('team', 'Đội tuyển', teamOptions(teams), query.team), selectField('stage', 'Vòng đấu', stages.map(stage => ({ value: stage, label: stage })), query.stage)]);
  return { html: `${pageHeader('04 / TỪNG PHÚT', 'Trận đấu', 'Tỷ số, địa điểm, vòng đấu và toàn bộ diễn biến quan trọng trong lịch sử World Cup.')}${form}
    ${matches.length ? `<section class="match-grid">${matches.map(matchCard).join('')}</section>${pagination({ page, pageSize: 12, received: matches.length, path: '/matches', query: { year: query.year, team: query.team, stage: query.stage } })}` : emptyState('Không tìm thấy trận đấu', 'Không có trận đấu phù hợp với bộ lọc hiện tại.', '#/matches', 'Xóa bộ lọc')}`, mount: () => bindFilterForm('/matches') };
}

export async function matchDetailPage({ params }) {
  const detail = await endpoints.match(params.id);
  const match = detail.match;
  const eventLabel = { goal: 'Bàn thắng', penalty_goal: 'Phạt đền', own_goal: 'Phản lưới', yellow_card: 'Thẻ vàng', second_yellow: 'Thẻ vàng thứ hai', red_card: 'Thẻ đỏ', substitution_in: 'Vào sân', substitution_out: 'Rời sân', penalty_shootout_goal: 'Luân lưu thành công', penalty_shootout_miss: 'Luân lưu hỏng' };
  return { html: `<div class="match-detail-hero reveal"><a href="#/matches">← TRẬN ĐẤU</a><div class="match-detail-meta"><span>${escapeHtml(match.stage)}</span><time>${date(match.kickoff_at)}</time><span>${escapeHtml(match.venue || 'Địa điểm chưa cập nhật')}</span></div><div class="scoreboard"><div>${teamMark(match.home_team, 'hero')}<h2>${escapeHtml(match.home_team.name)}</h2></div><strong><span>${match.home_score ?? '–'}</span><i>:</i><span>${match.away_score ?? '–'}</span></strong><div>${teamMark(match.away_team, 'hero')}<h2>${escapeHtml(match.away_team.name)}</h2></div></div><p>${match.status === 'finished' ? 'TRẬN ĐẤU ĐÃ KẾT THÚC' : escapeHtml(match.status)}</p></div>
    <section class="content-section event-section">${sectionTitle('DIỄN BIẾN', `${detail.events.length} sự kiện được ghi nhận`)}${detail.events.length ? `<div class="event-timeline">${detail.events.map(event => `<div class="event-item ${event.event_type.includes('card') || event.event_type.includes('yellow') ? 'card-event' : ''}"><time>${event.minute ?? 0}${event.stoppage_minute ? `+${event.stoppage_minute}` : ''}'</time><i></i><div><strong>${escapeHtml(eventLabel[event.event_type] || event.event_type)}</strong><span>${escapeHtml(event.player_name || event.team_name)}</span><small>${escapeHtml(event.team_name)}</small></div></div>`).join('')}</div>` : `<div class="inline-empty">Chưa có diễn biến chi tiết.</div>`}</section>` };
}

function standingsTable(items) {
  return `<div class="table-wrap"><table><thead><tr><th>#</th><th>Đội tuyển</th><th>Trận</th><th>T</th><th>H</th><th>B</th><th>BT</th><th>BB</th><th>Điểm</th></tr></thead><tbody>${items.map(item => `<tr><td><b>${item.rank}</b></td><td><a href="#/teams/${item.team_id}">${escapeHtml(item.team_name)}</a><small>Bảng ${escapeHtml(item.group_name)}</small></td><td>${item.played}</td><td>${item.won}</td><td>${item.drawn}</td><td>${item.lost}</td><td>${item.goals_for}</td><td>${item.goals_against}</td><td><strong>${item.points}</strong></td></tr>`).join('')}</tbody></table></div>`;
}

export async function standingsPage({ query }) {
  const { editions } = await lookups();
  const year = Number(query.year || editions.filter(item => item.year <= 2022).at(-1)?.year || 2022);
  const standings = await endpoints.standings(year);
  const form = filtersForm([selectField('year', 'Kỳ World Cup', yearsOptions(editions), year)], 'Xem bảng');
  return { html: `${pageHeader('05 / THỨ HẠNG', `Bảng xếp hạng ${year}`, 'Theo dõi vị trí, điểm số và hiệu suất của từng đội tuyển tại mỗi kỳ World Cup.')}${form}${standings.length ? `<section class="content-section">${standingsTable(standings)}</section>` : emptyState('Chưa có bảng xếp hạng', `Ảnh chụp bảng đấu World Cup ${year} chưa được nhập vào hệ thống.`, '#/standings?year=2022', 'Chọn kỳ khác')}`, mount: () => bindFilterForm('/standings') };
}

export async function newsPage({ query }) {
  const { editions } = await lookups();
  const page = pageOf(query);
  const articles = await endpoints.news({ q: query.q, tournament_year: query.year, limit: 12, offset: (page - 1) * 12 });
  const form = filtersForm([searchField('q', 'Tìm trong tin tức', query.q, 'Chung kết, Brazil, Messi...'), selectField('year', 'Kỳ World Cup', yearsOptions(editions), query.year)]);
  return { html: `${pageHeader('06 / GÓC NHÌN', 'Tin tức World Cup', 'Dòng thời gian báo chí Việt Nam kể lại các kỳ World Cup qua tiêu đề, sự kiện và ký ức.')}${form}
    ${articles.length ? `<section class="news-grid">${articles.map(newsCard).join('')}</section>${pagination({ page, pageSize: 12, received: articles.length, path: '/news', query: { q: query.q, year: query.year } })}` : emptyState('Không tìm thấy bài viết', 'Thử từ khóa hoặc kỳ World Cup khác.', '#/news', 'Xóa bộ lọc')}`, mount: () => bindFilterForm('/news') };
}

export async function newsDetailPage({ params }) {
  const article = await endpoints.article(params.id);
  let safeUrl = '#';
  try { const parsed = new URL(article.url); if (['http:', 'https:'].includes(parsed.protocol)) safeUrl = parsed.href; } catch {}
  return { html: `<article class="article-detail reveal"><a href="#/news">← TIN TỨC</a><div class="article-meta"><span>${escapeHtml(article.source)}</span><time>${date(article.published_at)}</time><span>WORLD CUP ${article.tournament_year || ''}</span></div><h1>${escapeHtml(article.title)}</h1><p class="article-lead">${escapeHtml(article.summary || 'Nguồn tin không cung cấp phần mô tả. Bạn có thể mở bài viết gốc để đọc nội dung đầy đủ.')}</p><div class="source-notice"><span>↗</span><div><strong>Nội dung thuộc về tòa soạn gốc</strong><p>World Cup Atlas chỉ lưu metadata, tiêu đề và liên kết nhằm phục vụ tra cứu.</p></div><a class="button primary" href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer">Đọc tại ${escapeHtml(article.source)} →</a></div></article>` };
}

export function notFoundPage() {
  return { html: emptyState('Trang không tồn tại', 'Đường dẫn bạn vừa mở không có trong World Cup Atlas.', '#/dashboard', 'Về dashboard') };
}
