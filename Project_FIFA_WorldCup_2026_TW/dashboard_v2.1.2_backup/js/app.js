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
  return new Date(`${dateStr}T${timeStr}:00+08:00`);
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
  return m.status === 'finished' || (m.home_score !== null && m.away_score !== null);
}

function isMatchLive(m) {
  const now = new Date();
  const kickoff = taiwanDateTime(m.date, m.time_taiwan);
  const end = new Date(kickoff.getTime() + 2 * 60 * 60 * 1000); // 約 2 小時後結束
  return now >= kickoff && now <= end && !isMatchFinished(m);
}

function renderNextMatch() {
  const now = new Date();
  const upcoming = matches
    .filter(m => !isMatchFinished(m) && taiwanDateTime(m.date, m.time_taiwan) > now)
    .sort((a, b) => taiwanDateTime(a.date, a.time_taiwan) - taiwanDateTime(b.date, b.time_taiwan));

  const container = document.getElementById('next-match');
  if (!upcoming.length) {
    container.innerHTML = '所有賽事已結束';
    return;
  }
  const m = upcoming[0];
  const home = getTeam(m.home_team);
  const away = getTeam(m.away_team);
  container.innerHTML = `
    <div><strong>#${m.match_id} ${m.stage} ${m.group ? m.group + '組' : ''}</strong></div>
    <div style="font-size:1.4rem;margin:.5rem 0;">
      <span class="team-name">${getFlagHTML(home)}${m.home_team}</span>
      vs
      <span class="team-name">${getFlagHTML(away)}${m.away_team}</span>
    </div>
    <div>${formatDateTime(m.date, m.time_taiwan)}</div>
    <div style="color:var(--muted)">${m.city}</div>
  `;
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
  if (m.status === 'finished') {
    return p.hit
      ? `<span class="pred-hit">✅ 命中</span>`
      : `<span class="pred-miss">❌ 未命中</span>`;
  }

  // Pre-match: predict winner with probability
  const { home_win_prob, draw_prob, away_win_prob } = p;
  const probs = {
    home: home_win_prob || 0,
    draw: draw_prob || 0,
    away: away_win_prob || 0,
  };
  const winner = Object.keys(probs).reduce((a, b) => probs[a] > probs[b] ? a : b);
  let label = '';
  let cls = '';
  if (winner === 'home') {
    label = `${m.home_team} 勝`;
    cls = 'pred-pre-home';
  } else if (winner === 'away') {
    label = `${m.away_team} 勝`;
    cls = 'pred-pre-away';
  } else {
    label = '和局';
    cls = 'pred-pre-draw';
  }
  return `<span class="pred-pre ${cls}">預測 ${label} ${probs[winner]}%</span>`;
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
      <tr class="${rowClass}">
        <td>${m.match_id}</td>
        <td>${m.date}</td>
        <td>${m.time_taiwan}</td>
        <td>${m.stage}</td>
        <td>${m.group || '-'}</td>
        <td><span class="team-name">${getFlagHTML(home)}${m.home_team}</span></td>
        <td class="score ${live ? 'live' : ''}">${score}</td>
        <td><span class="team-name">${getFlagHTML(away)}${m.away_team}</span></td>
        <td>${m.city}</td>
        <td class="prediction">${pred}</td>
      </tr>
    `;
  }).join('');
}

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
