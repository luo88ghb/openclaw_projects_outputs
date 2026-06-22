let matches = [];
let teams = [];
let stagePredictions = {};

function setupSSE() {
  try {
    const evtSource = new EventSource('/update-stream');
    evtSource.addEventListener('connected', () => {
      console.log('SSE connected');
    });
    evtSource.addEventListener('update', () => {
      console.log('SSE update received, reloading data...');
      loadData();
    });
    evtSource.onerror = (err) => {
      console.error('SSE error', err);
    };
  } catch (e) {
    console.error('SSE not supported or failed', e);
  }
}

function setupFilters() {
  const stageFilter = document.getElementById('stage-filter');
  const groupFilter = document.getElementById('group-filter');
  const search = document.getElementById('search');

  const render = () => renderMatches();

  if (stageFilter) stageFilter.addEventListener('change', render);
  if (groupFilter) groupFilter.addEventListener('change', render);
  if (search) search.addEventListener('input', render);
}

function setupJumpToLatest() {
  const btn = document.getElementById('jump-to-latest');
  if (!btn) return;
  btn.addEventListener('click', () => {
    const matchId = findLatestMatchId();
    scrollToMatch(matchId);
  });
}

function setupPredictionDetailButtons() {
  const container = document.getElementById('match-table-container');
  if (!container) return;
  container.addEventListener('click', (e) => {
    // 點選場次編號或預測欄位時，開啟預測歷史 modal
    const cell = e.target.closest('td.prediction, td:first-child');
    if (cell) {
      const row = cell.closest('tr');
      if (row) {
        const matchId = Number(row.dataset.matchId);
        if (matchId) {
          showPredictionHistory(matchId);
          return;
        }
      }
    }
    // 原有的預測細節按鈕切換
    const btn = e.target.closest('.pred-detail-btn');
    if (!btn) return;
    const row = btn.closest('tr');
    const detail = row ? row.querySelector('.pred-detail') : null;
    if (detail) {
      detail.classList.toggle('hidden');
    }
  });
}

async function showPredictionHistory(matchId) {
  const modal = document.getElementById('prediction-history-modal');
  const title = document.getElementById('prediction-history-title');
  const body = document.getElementById('prediction-history-body');
  const match = matches.find(m => m.match_id === matchId);
  if (!match) return;

  title.textContent = `場次 #${matchId} 預測歷史`;
  body.innerHTML = '<p>載入中...</p>';
  modal.classList.remove('hidden');

  // 1. 當前 matches_104.json 中的預測
  const currentRows = [];
  if (match.prediction) {
    const p = match.prediction;
    currentRows.push({
      time: match.date + ' ' + match.time_taiwan,
      source: '當前資料 (matches_104.json)',
      prediction: `${match.home_team} ${p.home_score_pred ?? '-'} - ${p.away_score_pred ?? '-'} ${match.away_team}`,
      outcome: `主 ${p.home_win_prob ?? '-'}% / 和 ${p.draw_prob ?? '-'}% / 客 ${p.away_win_prob ?? '-'}%`,
      hit: p.hit === true ? '✅ 命中' : (p.hit === false ? '❌ 未命中' : '未結束')
    });
  }

  // 2. predictions_db.json 中的歷史預測（如果存在）
  let historyRows = [];
  try {
    const res = await fetch('predictions/predictions_db.json');
    if (res.ok) {
      const db = await res.json();
      const recs = (db.match_predictions || []).filter(r => r.match_id === matchId);
      historyRows = recs.map(r => ({
        time: r.created_at ? new Date(r.created_at).toLocaleString('zh-TW') : '未知時間',
        source: r.source || '預測資料庫',
        prediction: `${match.home_team} ${r.home_score_pred ?? '-'} - ${r.away_score_pred ?? '-'} ${match.away_team}`,
        outcome: `主 ${r.home_win_prob ?? '-'}% / 和 ${r.draw_prob ?? '-'}% / 客 ${r.away_win_prob ?? '-'}%`,
        hit: r.hit === true ? '✅ 命中' : (r.hit === false ? '❌ 未命中' : '未結束')
      }));
    }
  } catch (e) {
    console.error('Failed to load predictions_db.json', e);
  }

  const rows = [...historyRows, ...currentRows];
  if (!rows.length) {
    body.innerHTML = '<p>尚無預測記錄。</p>';
    return;
  }

  body.innerHTML = `
    <table class="history-table">
      <thead>
        <tr><th>時間</th><th>來源</th><th>預測比數</th><th>預測結果機率</th><th>命中</th></tr>
      </thead>
      <tbody>
        ${rows.map(r => `
          <tr>
            <td>${r.time}</td>
            <td>${r.source}</td>
            <td>${r.prediction}</td>
            <td>${r.outcome}</td>
            <td>${r.hit}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

function setupPredictionHistoryModal() {
  const modal = document.getElementById('prediction-history-modal');
  if (!modal) return;
  modal.addEventListener('click', (e) => {
    if (e.target === modal || e.target.closest('.modal-close')) {
      modal.classList.add('hidden');
    }
  });
}

async function loadData() {
  const [matchesRes, teamsRes] = await Promise.all([
    fetch('data/matches_104.json'),
    fetch('data/teams.json')
  ]);
  const matchesData = await matchesRes.json();
  const teamsData = await teamsRes.json();
  matches = matchesData.matches;
  teams = teamsData.teams;
  renderNextMatch();
  renderPredictions('小組賽');
  renderMatches();
  renderStandings();
  setupPredictionTabs();
  setupPredictionActions();
  setupFilters();
  setupJumpToLatest();
  setupPredictionDetailButtons();
  setupPredictionHistoryModal();
}

function setupPredictionDetailButtons() {
  const container = document.getElementById('match-table-container');
  if (!container) return;
  container.addEventListener('click', (e) => {
    // 點選場次編號或預測欄位時，開啟預測歷史 modal
    const cell = e.target.closest('td.prediction, td:first-child');
    if (cell) {
      const row = cell.closest('tr');
      if (row) {
        const matchId = Number(row.dataset.matchId);
        if (matchId) {
          showPredictionHistory(matchId);
          return;
        }
      }
    }
    // 原有的預測細節按鈕切換
    const btn = e.target.closest('.pred-detail-btn');
    if (!btn) return;
    const row = btn.closest('tr');
    const detail = row ? row.querySelector('.pred-detail') : null;
    if (detail) {
      detail.classList.toggle('hidden');
    }
  });
}

function getTeam(name) {
  return teams.find(t => t.name_zh === name || t.name_en === name) || { flag_img: '', flag: '', name_zh: name };
}

function getFlagHTML(team) {
  // Dual-element structure: image preferred, emoji fallback on load error.
  const emoji = `<span class="team-flag">${team.flag || ''}</span>`;
  if (team.flag_img) {
    return `<img class="team-flag-img" src="${team.flag_img}" alt="${team.name_zh || team.name_en || ''}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='inline'">${emoji}`;
  }
  return emoji;
}

function taiwanDateTime(dateStr, timeStr) {
  // Always interpret date/time as Asia/Taipei regardless of client locale.
  return new Date(`${dateStr}T${timeStr}:00+08:00`);
}

function nowTaiwan() {
  // Get current time in Asia/Taipei explicitly.
  const d = new Date();
  const s = d.toLocaleString('en-US', { timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  return new Date(s);
}

function formatDateTime(dateStr, timeStr) {
  const d = taiwanDateTime(dateStr, timeStr);
  return d.toLocaleString('zh-TW', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    weekday: 'short'
  });
}

function isMatchFinished(m) {
  if (m.status === 'finished') return true;
  const hs = m.home_score;
  const aw = m.away_score;
  return hs != null && aw != null && hs !== '' && aw !== '' && !Number.isNaN(Number(hs)) && !Number.isNaN(Number(aw));
}

function isMatchLive(m) {
  const now = nowTaiwan();
  const kickoff = taiwanDateTime(m.date, m.time_taiwan);
  const end = new Date(kickoff.getTime() + 2 * 60 * 60 * 1000); // 約 2 小時後結束
  return now >= kickoff && now <= end && !isMatchFinished(m);
}

const FOCUS_WINDOW_SIZE = 4;

function renderMatchInfo(m, options = {}) {
  const home = getTeam(m.home_team);
  const away = getTeam(m.away_team);
  const finished = isMatchFinished(m);
  const live = isMatchLive(m);
  let score;
  let statusClass = '';
  if (finished) {
    score = `<strong>${m.home_score} - ${m.away_score}</strong>`;
    statusClass = 'finished';
  } else if (live) {
    score = `<strong class="live-score">${m.home_score ?? 0} - ${m.away_score ?? 0}</strong><span class="live-badge">● 比賽中</span>`;
    statusClass = 'live';
  } else {
    score = `<span style="color:var(--muted)">尚未開賽</span>`;
    statusClass = 'scheduled';
  }

  const compactClass = options.compact ? 'compact' : '';
  return `
    <div class="match-info-row ${statusClass} ${compactClass}">
      <div class="match-info-meta"><strong>#${m.match_id} ${m.stage} ${m.group ? m.group + '組' : ''}</strong> · ${formatDateTime(m.date, m.time_taiwan)} · ${m.city}</div>
      <div class="match-info-teams">
        <span class="team-name">${getFlagHTML(home)}${m.home_team}</span>
        <span class="match-info-score">${score}</span>
        <span class="team-name">${getFlagHTML(away)}${m.away_team}</span>
      </div>
    </div>
  `;
}

function getMatchWindowCenter() {
  const now = nowTaiwan();

  // 比賽中場次：最優先作為視窗中心
  const liveMatches = matches
    .filter(m => isMatchLive(m))
    .sort((a, b) => taiwanDateTime(a.date, a.time_taiwan) - taiwanDateTime(b.date, b.time_taiwan));
  if (liveMatches.length) return { centerMatch: liveMatches[0], mode: 'live' };

  // 下一場未賽比賽：作為視窗中心
  const upcoming = matches
    .filter(m => !isMatchFinished(m) && taiwanDateTime(m.date, m.time_taiwan) > now)
    .sort((a, b) => taiwanDateTime(a.date, a.time_taiwan) - taiwanDateTime(b.date, b.time_taiwan));
  if (upcoming.length) return { centerMatch: upcoming[0], mode: 'upcoming' };

  // 全部結束：以最後一場為中心
  const lastFinished = matches
    .filter(m => isMatchFinished(m))
    .sort((a, b) => taiwanDateTime(b.date, b.time_taiwan) - taiwanDateTime(a.date, a.time_taiwan))[0];
  if (lastFinished) return { centerMatch: lastFinished, mode: 'all-finished' };

  return { centerMatch: null, mode: 'empty' };
}

function getMatchByOffset(centerId, offset) {
  const idx = matches.findIndex(m => m.match_id === centerId);
  if (idx === -1) return null;
  const targetIdx = idx + offset;
  if (targetIdx < 0 || targetIdx >= matches.length) return null;
  return matches[targetIdx];
}

function renderNextMatch() {
  const container = document.getElementById('next-match');
  const { centerMatch, mode } = getMatchWindowCenter();

  if (!centerMatch) {
    container.innerHTML = '所有賽事已結束';
    return;
  }

  const centerId = centerMatch.match_id;

  // 已結束區塊：中心場次往前數 FOCUS_WINDOW_SIZE 場
  const finishedHtmlRows = [];
  for (let offset = -1; offset >= -FOCUS_WINDOW_SIZE; offset--) {
    const m = getMatchByOffset(centerId, offset);
    if (m && isMatchFinished(m)) {
      finishedHtmlRows.unshift(renderMatchInfo(m, { compact: true }));
    }
  }

  // 下一場區塊：中心場次往後數，跳過比賽中（因為比賽中單獨顯示）
  const nextHtmlRows = [];
  for (let offset = (mode === 'live' ? 1 : 0); offset < FOCUS_WINDOW_SIZE + (mode === 'live' ? 0 : 1); offset++) {
    const m = getMatchByOffset(centerId, offset);
    if (m) {
      nextHtmlRows.push(renderMatchInfo(m, { compact: true }));
    }
  }

  let html = '';

  if (finishedHtmlRows.length) {
    html += `<div class="match-info last">
      <div class="match-info-section-title">📅 已結束比賽</div>
      ${finishedHtmlRows.join('')}
    </div>`;
  }

  if (mode === 'live') {
    html += `<div class="match-info live">
      <div class="match-info-section-title">🔴 比賽中</div>
      ${renderMatchInfo(centerMatch)}
    </div>`;
  }

  if (nextHtmlRows.length) {
    html += `<div class="match-info next">
      <div class="match-info-section-title">⏰ 下一場比賽</div>
      ${nextHtmlRows.join('')}
    </div>`;
  }

  container.innerHTML = html || '所有賽事已結束';
}

function setupPredictionTabs() {
  const tabs = document.querySelectorAll('.stage-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      renderPredictions(tab.dataset.stage);
    });
  });
}

function setupPredictionActions() {
  document.getElementById('print-prediction').addEventListener('click', () => {
    window.print();
  });

  document.getElementById('download-prediction').addEventListener('click', () => {
    const activeTab = document.querySelector('.stage-tab.active');
    const stage = activeTab ? activeTab.dataset.stage : '預測';
    const content = document.getElementById('prediction-content').innerText;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `WorldCup2026_預測_${stage}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
}

function computeGroupPredictions() {
  // 簡單版：根據 FIFA 排名 + 已賽成績預測小組晉級機率
  const groups = {};
  matches.filter(m => m.group).forEach(m => {
    if (!groups[m.group]) groups[m.group] = [];
    groups[m.group].push(m);
  });

  return Object.keys(groups).sort().map(g => {
    const standings = {};
    groups[g].forEach(m => {
      [m.home_team, m.away_team].forEach(t => {
        if (!standings[t]) {
          const teamInfo = getTeam(t);
          standings[t] = {
            team: t,
            flag: teamInfo.flag || '',
            rank: teamInfo.fifa_ranking || 999,
            p: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, pts: 0
          };
        }
      });
      if (isMatchFinished(m)) {
        standings[m.home_team].p += 1;
        standings[m.away_team].p += 1;
        standings[m.home_team].gf += m.home_score;
        standings[m.home_team].ga += m.away_score;
        standings[m.away_team].gf += m.away_score;
        standings[m.away_team].ga += m.home_score;
        if (m.home_score > m.away_score) {
          standings[m.home_team].w += 1; standings[m.home_team].pts += 3;
          standings[m.away_team].l += 1;
        } else if (m.home_score === m.away_score) {
          standings[m.home_team].d += 1; standings[m.away_team].d += 1;
          standings[m.home_team].pts += 1; standings[m.away_team].pts += 1;
        } else {
          standings[m.away_team].w += 1; standings[m.away_team].pts += 3;
          standings[m.home_team].l += 1;
        }
      }
    });

    // 剩餘場次模擬：排名越高贏面越大
    groups[g].filter(m => !isMatchFinished(m)).forEach(m => {
      const home = standings[m.home_team];
      const away = standings[m.away_team];
      const homeStrength = 100 - home.rank;
      const awayStrength = 100 - away.rank;
      const total = homeStrength + awayStrength;
      const homeWinProb = homeStrength / total;
      const awayWinProb = awayStrength / total;
      const drawProb = 0.25;
      const normalizedHome = homeWinProb * (1 - drawProb);
      const normalizedAway = awayWinProb * (1 - drawProb);

      // 預期積分
      home.pts += normalizedHome * 3 + drawProb * 1;
      away.pts += normalizedAway * 3 + drawProb * 1;
      home.p += 1;
      away.p += 1;
    });

    const rows = Object.values(standings).sort((a, b) => b.pts - a.pts || (b.gf - b.ga) - (a.gf - a.ga));
    // 前兩名晉級機率標記
    rows.forEach((r, idx) => {
      r.qualified = idx < 2;
      r.prob = r.qualified ? Math.round(50 + (2 - idx) * 25) : Math.round(30 - idx * 5);
    });

    return { group: g, rows };
  });
}

async function renderPredictions(stage) {
  const container = document.getElementById('prediction-content');
  // API server at :8766 is no longer required; use local computation only.

  if (stage === '小組賽') {
    const groups = computeGroupPredictions();
    container.innerHTML = `
      <div class="prediction-stage-title">🔮 小組賽晉級預測（前 2 名晉級 32 強）</div>
      <div class="prediction-list">
        ${groups.map(g => `
          <div style="margin-bottom:1rem;">
            <strong>${g.group} 組</strong>
            ${g.rows.map((r, idx) => `
              <div class="prediction-row ${r.qualified ? '' : ''}" style="${r.qualified ? 'border-left:3px solid var(--accent2);' : 'opacity:0.75;'}">
                <div class="prediction-team">${getFlagHTML({flag_img: '', flag: r.flag, name_zh: r.team})}${idx + 1}. ${r.team}</div>
                <div class="prediction-prob">${r.prob}% 晉級</div>
              </div>
            `).join('')}
          </div>
        `).join('')}
      </div>
    `;
  } else {
    container.innerHTML = generateBracketPrediction(stage);
  }
}

function generateBracketPrediction(stage) {
  const titles = {
    '32強': '32 強對戰預測',
    '16強': '16 強對戰預測',
    '8強': '8 強對戰預測',
    '4強': '4 強對戰預測',
    '冠亞季軍': '冠軍 / 亞軍 / 季軍預測'
  };

  // 簡單邏輯：取各組前兩名，依 FIFA 排名晉級
  const groups = computeGroupPredictions();
  const qualified = groups.flatMap(g => g.rows.slice(0, 2).map((r, idx) => ({
    ...r,
    seed: idx === 0 ? `${g.group}1` : `${g.group}2`
  })));

  const pickByRank = (list, count) => list.sort((a, b) => a.rank - b.rank).slice(0, count);

  let content = `<div class="prediction-stage-title">🔮 ${titles[stage]}</div>`;

  if (stage === '32強') {
    content += renderMatchList(qualified);
  } else if (stage === '16強') {
    content += renderMatchList(pickByRank(qualified, 16));
  } else if (stage === '8強') {
    content += renderMatchList(pickByRank(qualified, 8));
  } else if (stage === '4強') {
    content += renderMatchList(pickByRank(qualified, 4));
  } else if (stage === '冠亞季軍') {
    const top4 = pickByRank(qualified, 4);
    const champion = top4[0];
    const runnerUp = top4[1];
    const third = top4[2];
    content += `
      <div class="prediction-bracket">
        <div class="prediction-row" style="border-left:4px solid gold;">
          <div class="prediction-team">${getFlagHTML({flag_img: '', flag: champion.flag, name_zh: champion.team})}🏆 冠軍：${champion.team}</div>
          <div class="prediction-prob">${Math.round(100 - champion.rank)}%</div>
        </div>
        <div class="prediction-row" style="border-left:4px solid silver;">
          <div class="prediction-team">${getFlagHTML({flag_img: '', flag: runnerUp.flag, name_zh: runnerUp.team})}🥈 亞軍：${runnerUp.team}</div>
          <div class="prediction-prob">${Math.round(90 - runnerUp.rank)}%</div>
        </div>
        <div class="prediction-row" style="border-left:4px solid #cd7f32;">
          <div class="prediction-team">${getFlagHTML({flag_img: '', flag: third.flag, name_zh: third.team})}🥉 季軍：${third.team}</div>
          <div class="prediction-prob">${Math.round(80 - third.rank)}%</div>
        </div>
      </div>
    `;
  }

  return content;
}

function renderMatchList(teamsList) {
  if (!teamsList.length) return '<p>尚無資料</p>';
  return `
    <div class="prediction-list">
      ${teamsList.map((t, i) => `
        <div class="prediction-row">
          <div class="prediction-team">${getFlagHTML({flag_img: '', flag: t.flag, name_zh: t.team})}${i + 1}. ${t.team} <span style="color:var(--muted);font-size:0.8rem;">(FIFA ${t.rank})</span></div>
          <div class="prediction-prob">${Math.max(10, Math.round(100 - t.rank))}%</div>
        </div>
      `).join('')}
    </div>
  `;
}

function formatPredictionCell(m) {
  const p = m.prediction;
  if (!p) return '-';
  // 先嘗試多種可能的欄位名稱
  const homePred = p.home_score_pred !== undefined ? p.home_score_pred : p.predicted_home_score;
  const awayPred = p.away_score_pred !== undefined ? p.away_score_pred : p.predicted_away_score;
  // Use probability-based outcome instead of score-based.
  const probs = {
    home: p.home_win_prob || 0,
    draw: p.draw_prob || 0,
    away: p.away_win_prob || 0
  };
  const predicted = Object.keys(probs).reduce((a, b) => probs[a] > probs[b] ? a : b);
  const predictedLabel = { home: '主勝', draw: '和局', away: '客勝' }[predicted];
  const probValue = probs[predicted];

  let summary = '';
  if (m.status === 'finished') {
    const isHit = p.hit === true || m.hit === true;
    summary = isHit ? `✅ 命中 (${predictedLabel} ${probValue}%)` : `❌ 未命中`;
  } else {
    summary = `🔮 ${predictedLabel} ${probValue}%`;
  }

  const scoreText = p.score !== undefined ? `(${p.score > 0 ? '+' : ''}${p.score}分)` : '';
  const preHtml = `<span class="pred-pre">${summary} ${scoreText}</span>`;
  const details = [];
  if (p.home_win_prob !== undefined && p.away_win_prob !== undefined && p.draw_prob !== undefined) {
    details.push(`主 ${p.home_win_prob}% / 和 ${p.draw_prob}% / 客 ${p.away_win_prob}%`);
    details.push(`比數預測 ${homePred ?? '-'} - ${awayPred ?? '-'}`);
  } else if (homePred != null && awayPred != null) {
    details.push(`比數預測 ${homePred} - ${awayPred}`);
  }
  if (p.reason) details.push(p.reason);
  return `<button class="pred-detail-btn" data-match-id="${m.match_id}">${preHtml}</button>` +
    (details.length ? `<div class="pred-detail hidden">${details.join('<br>')}</div>` : '');
}

function renderMatches() {
  const tbody = document.getElementById('match-tbody');
  const stageFilter = document.getElementById('stage-filter').value;
  const groupFilter = document.getElementById('group-filter').value;
  const search = document.getElementById('search').value.toLowerCase();

  const filtered = matches.filter(m => {
    if (stageFilter && m.stage !== stageFilter) return false;
    if (groupFilter && m.group !== groupFilter) return false;
    if (search) {
      const text = `${m.home_team} ${m.away_team} ${m.city} ${m.group || ''}`.toLowerCase();
      return text.includes(search);
    }
    return true;
  });

  tbody.innerHTML = filtered.map((m, index) => {
    const finished = isMatchFinished(m);
    const live = isMatchLive(m);
    const score = finished || live
      ? `${m.home_score ?? 0} - ${m.away_score ?? 0}`
      : '-';
    const pred = m.prediction
      ? formatPredictionCell(m)
      : '-';
    const home = getTeam(m.home_team);
    const away = getTeam(m.away_team);
    const rowClass = (index % 2 === 0 ? 'odd' : 'even') + (finished ? ' finished' : '') + (live ? ' live' : '');

    return `
      <tr class="${rowClass}" data-match-id="${m.match_id}" id="match-row-${m.match_id}">
        <td title="點擊查看預測歷史">${m.match_id}</td>
        <td>${m.date}</td>
        <td>${m.time_taiwan}</td>
        <td>${m.stage}</td>
        <td>${m.group || '-'}</td>
        <td><span class="team-name">${getFlagHTML(home)}${m.home_team}</span></td>
        <td class="score ${live ? 'live' : ''}">${score}</td>
        <td><span class="team-name">${getFlagHTML(away)}${m.away_team}</span></td>
        <td>${m.city}</td>
        <td class="prediction" title="點擊查看預測歷史">${pred}</td>
      </tr>
    `;
  }).join('');
}

function findLatestMatchId() {
  const now = nowTaiwan();
  // 找到最接近目前時間的一場：若已結束取最後一場已結束，否則取下一場即將開賽
  const sorted = [...matches].sort((a, b) => {
    const da = taiwanDateTime(a.date, a.time_taiwan);
    const db = taiwanDateTime(b.date, b.time_taiwan);
    return da - db;
  });
  let closest = null;
  let minDiff = Infinity;
  for (const m of sorted) {
    const dt = taiwanDateTime(m.date, m.time_taiwan);
    const diff = Math.abs(dt - now);
    if (diff < minDiff) {
      minDiff = diff;
      closest = m;
    }
  }
  return closest ? closest.match_id : null;
}

function scrollToMatch(matchId) {
  if (!matchId) return;
  const row = document.getElementById(`match-row-${matchId}`);
  if (!row) return;
  row.scrollIntoView({ behavior: 'smooth', block: 'center' });
  row.classList.add('highlight-row');
  setTimeout(() => row.classList.remove('highlight-row'), 2500);
}

document.addEventListener('click', (e) => {
  if (e.target && e.target.id === 'jump-to-latest') {
    const matchId = findLatestMatchId();
    scrollToMatch(matchId);
  }
});

function renderStandings() {
  const groups = {};
  matches.filter(m => m.group).forEach(m => {
    if (!groups[m.group]) groups[m.group] = [];
    groups[m.group].push(m);
  });

  const container = document.getElementById('standings');
  container.innerHTML = Object.keys(groups).sort().map(g => {
    const standings = {};
    groups[g].forEach(m => {
      [m.home_team, m.away_team].forEach(t => {
        if (!standings[t]) {
          const info = getTeam(t);
          standings[t] = { team: t, flag: info.flag || '', flag_img: info.flag_img || '', p: 0, w: 0, d: 0, l: 0, gf: 0, ga: 0, pts: 0 };
        }
      });
      if (isMatchFinished(m)) {
        standings[m.home_team].p += 1;
        standings[m.away_team].p += 1;
        standings[m.home_team].gf += m.home_score;
        standings[m.home_team].ga += m.away_score;
        standings[m.away_team].gf += m.away_score;
        standings[m.away_team].ga += m.home_score;
        if (m.home_score > m.away_score) {
          standings[m.home_team].w += 1;
          standings[m.home_team].pts += 3;
          standings[m.away_team].l += 1;
        } else if (m.home_score === m.away_score) {
          standings[m.home_team].d += 1;
          standings[m.away_team].d += 1;
          standings[m.home_team].pts += 1;
          standings[m.away_team].pts += 1;
        } else {
          standings[m.away_team].w += 1;
          standings[m.away_team].pts += 3;
          standings[m.home_team].l += 1;
        }
      }
    });
    const rows = Object.values(standings).sort((a, b) => b.pts - a.pts || (b.gf - b.ga) - (a.gf - a.ga));
    return `
      <div class="group-card">
        <h3>${g} 組</h3>
        <table>
          <thead>
            <tr><th>球隊</th><th>賽</th><th>勝</th><th>和</th><th>負</th><th>進球</th><th>積分</th></tr>
          </thead>
          <tbody>
            ${rows.map(r => `
              <tr>
                <td><span class="team-name">${getFlagHTML({flag_img: r.flag_img, flag: r.flag, name_zh: r.team})}${r.team}</span></td>
                <td>${r.p}</td>
                <td>${r.w}</td>
                <td>${r.d}</td>
                <td>${r.l}</td>
                <td>${r.gf}-${r.ga}</td>
                <td><strong>${r.pts}</strong></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }).join('');
}

setupSSE();
loadData();

