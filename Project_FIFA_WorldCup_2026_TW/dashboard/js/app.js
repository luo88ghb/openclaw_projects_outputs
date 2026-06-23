let matches = [];
let teams = [];
let stagePredictions = {};
let activeModel = 'l1'; // 'l1' FIFA ranking model, 'l2' Elo model
let currentFeedbackMatchId = null;
let currentFeedbackMap = {};

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

function getModelPrediction(match, model = 'l1') {
  const home = getTeam(match.home_team);
  const away = getTeam(match.away_team);
  const homeRank = home.fifa_ranking ?? 999;
  const awayRank = away.fifa_ranking ?? 999;

  if (model === 'l2' && (home.elo_rating || away.elo_rating)) {
    const homeElo = home.elo_rating || 1500;
    const awayElo = away.elo_rating || 1500;
    const diff = homeElo - awayElo + 100; // home advantage
    const winProb = 1.0 / (1.0 + 10 ** (-diff / 400.0));
    const drawProb = 0.25;
    const adj = 1.0 - drawProb;
    const probs = {
      home: Math.round(winProb * adj * 100),
      draw: Math.round(drawProb * 100),
      away: Math.round((1.0 - winProb) * adj * 100)
    };
    const predicted = Object.keys(probs).reduce((a, b) => probs[a] > probs[b] ? a : b);
    return {
      predicted,
      probs,
      reason: `L2 Elo 模型 (主隊 ${homeElo} vs 客隊 ${awayElo})`,
      score: { home: 0, away: 0 } // L2 only gives outcome, not score
    };
  }

  // L1: FIFA ranking + rolling vector simplified to match backend formula
  const homeVec = { overall: 50 };
  const awayVec = { overall: 50 };
  const rankFactor = (awayRank - homeRank) * 0.3;
  const vectorFactor = (homeVec.overall - awayVec.overall) * 0.5;
  const homeAdvantage = 3.0;
  const homeExpected = Math.max(0.5, 1.2 + (rankFactor + vectorFactor + homeAdvantage) / 30);
  const awayExpected = Math.max(0.5, 1.0 + (-rankFactor - vectorFactor) / 30);
  const total = homeExpected + awayExpected + 0.5;
  const probs = {
    home: Math.round(homeExpected / total * 100),
    draw: Math.max(0, 100 - Math.round(homeExpected / total * 100) - Math.round(awayExpected / total * 100)),
    away: Math.round(awayExpected / total * 100)
  };
  const predicted = Object.keys(probs).reduce((a, b) => probs[a] > probs[b] ? a : b);
  return {
    predicted,
    probs,
    reason: `L1 FIFA 排名模型 (主隊排名 ${homeRank} vs 客隊排名 ${awayRank})`,
    score: { home: Math.round(homeExpected), away: Math.round(awayExpected) }
  };
}

function evaluateModel(model, pred, match) {
  const label = { home: '主勝', draw: '和局', away: '客勝' };
  const probs = pred.probs;
  const maxProb = Math.max(probs.home, probs.draw, probs.away);
  const runnerUp = Math.max(...Object.values(probs).filter(v => v !== maxProb));
  const margin = maxProb - runnerUp;
  const predictedOutcome = pred.predicted;

  // stability score 0-100: penalize extreme (>80), very low confidence (<40), or weird draw suppression
  let stability = 70;
  const drawProb = probs.draw;

  if (maxProb > 85) stability -= 20; // overconfident
  else if (maxProb > 75) stability -= 10;
  else if (maxProb < 40) stability -= 15; // too weak

  if (margin < 10) stability -= 15; // tossup
  else if (margin > 40) stability -= 10; // overconfident gap

  if (drawProb < 10) stability -= 15; // unrealistic draw suppression
  else if (drawProb > 40) stability -= 5; // too draw-heavy

  // score prediction sanity
  if (pred.score && (pred.score.home > 4 || pred.score.away > 4)) stability -= 10;

  stability = Math.max(0, Math.min(100, stability));

  // coach comments
  let praise = [];
  let critique = [];

  if (model === 'l1') {
    if (maxProb >= 50 && maxProb <= 75) praise.push('機率區間務實，沒有過度膨脹。');
    if (drawProb >= 15 && drawProb <= 30) praise.push('和局機率給得合理，尊重足球比賽的不確定性。');
    if (margin >= 15) praise.push('預測立場清楚，不會讓人模稜兩可。');

    if (maxProb < 40) critique.push('信心偏弱，像是在猜硬幣。');
    if (margin < 10) critique.push('勝負機率太接近，幾乎沒有判斷力。');
    if (drawProb < 12) critique.push('和局機率壓太低，容易忽略勢均力敵的比賽。');
  } else if (model === 'l2') {
    if (maxProb >= 55 && maxProb <= 80) praise.push('Elo 評分轉換成機率後，判斷果斷但不狂妄。');
    if (drawProb >= 20) praise.push('和局機率有保持，沒有過度傾向單邊。');
    if (margin >= 20 && margin <= 45) praise.push('勝負差異適度，模型差異化明顯。');

    if (maxProb > 85) critique.push('機率過高，可能過度相信 Elo 評分而忽略場上狀態。');
    if (drawProb < 15) critique.push('和局機率被壓縮，這是 Elo 常見的過擬合徵兆。');
    if (margin > 50) critique.push('勝負差距拉太大，現實足球很難這麼單純。');
  }

  // actual result feedback (if finished)
  const actual = isMatchFinished(match)
    ? (match.home_score > match.away_score ? 'home' : match.home_score === match.away_score ? 'draw' : 'away')
    : null;
  let resultComment = '';
  if (actual !== null) {
    if (predictedOutcome === actual) {
      resultComment = `✅ 結果驗證：預測「${label[predictedOutcome]}」命中實際結果。`;
      if (maxProb < 45) resultComment += ' 雖然命中，但信心偏低，帶點運氣成分。';
    } else {
      resultComment = `❌ 結果驗證：預測「${label[predictedOutcome]}」與實際「${label[actual]}」不符。`;
      if (maxProb > 75) resultComment += ' 這次太過自信，反而錯得離譜。';
    }
  }

  // grade
  let grade = 'B';
  if (stability >= 80) grade = 'A';
  else if (stability >= 65) grade = 'B';
  else if (stability >= 50) grade = 'C';
  else grade = 'D';

  return {
    name: model === 'l1' ? 'L1 FIFA 排名' : 'L2 Elo 評分',
    outcome: label[predictedOutcome],
    probs,
    reason: pred.reason,
    score: pred.score,
    stability,
    grade,
    praise,
    critique,
    resultComment,
    maxProb,
    margin
  };
}

function generateCoachVerdict(l1Eval, l2Eval, match) {
  const lines = [];
  const finished = isMatchFinished(match);

  // opening: who is better today
  if (l1Eval.grade > l2Eval.grade) {
    lines.push(`今天 L1 表現更穩，給出 ${l1Eval.grade}；L2 只有 ${l2Eval.grade}，需要檢討。`);
  } else if (l2Eval.grade > l1Eval.grade) {
    lines.push(`這場 L2 更值得期待，評分 ${l2Eval.grade}；L1 只有 ${l1Eval.grade}，略顯保守。`);
  } else {
    lines.push(`兩個模型今天都拿到 ${l1Eval.grade}，水準接近。`);
  }

  // specific model comments
  [l1Eval, l2Eval].forEach(ev => {
    const parts = [];
    if (ev.praise.length) parts.push(...ev.praise.slice(0, 2));
    if (ev.critique.length) parts.push(...ev.critique.slice(0, 2));
    if (parts.length) {
      lines.push(`▸ ${ev.name}：${parts.join(' ')}`);
    }
  });

  // result comparison if finished
  if (finished) {
    const l1Hit = l1Eval.resultComment.startsWith('✅');
    const l2Hit = l2Eval.resultComment.startsWith('✅');
    if (l1Hit && l2Hit) {
      lines.push('兩人都命中結果，但今天勝負差距誰估得更準，還要看機率分布。');
    } else if (l1Hit && !l2Hit) {
      lines.push('L1 命中、L2 失準：有時候簡單模型反而比複雜模型可靠，這就是過擬合的教訓。');
    } else if (!l1Hit && l2Hit) {
      lines.push('L2 命中、L1 失準：進階參數在這場發揮了價值。');
    } else {
      lines.push('兩人都沒命中，這場賽果確實難料，別急著全盤否定模型。');
    }
  }

  // final coaching note
  if (l1Eval.outcome === l2Eval.outcome) {
    if (l1Eval.grade === 'A' || l2Eval.grade === 'A') {
      lines.push('教練總評：兩人意見一致且品質不錯，這個預測可以拿出手。');
    } else if (l1Eval.grade === 'D' || l2Eval.grade === 'D') {
      lines.push('教練總評：雖然意見一致，但雙方品質都偏低，建議當參考就好。');
    } else {
      lines.push('教練總評：意見一致，中規中矩，可以信任但不值得重注。');
    }
  } else {
    lines.push('教練總評：兩人意見分歧，代表這場比賽本質難判，建議交叉比對近期狀態與傷停資訊。');
  }

  return lines;
}

function computePredictionReview(match) {
  const l1 = getModelPrediction(match, 'l1');
  const l2 = getModelPrediction(match, 'l2');
  const p = match.prediction || {};

  const activeLabel = { home: '主勝', draw: '和局', away: '客勝' };
  const agreement = l1.predicted === l2.predicted;

  const l1Eval = evaluateModel('l1', l1, match);
  const l2Eval = evaluateModel('l2', l2, match);
  const coachVerdict = generateCoachVerdict(l1Eval, l2Eval, match);

  // Overall confidence = average of stability weighted by max probability
  const confidence = Math.round((l1Eval.maxProb + l2Eval.maxProb) / 2);

  let verdict = '審查中';
  let verdictClass = 'review-neutral';
  if (!agreement) {
    verdict = '⚠️ 模型分歧';
    verdictClass = 'review-warning';
  } else if (l1Eval.grade === 'D' || l2Eval.grade === 'D') {
    verdict = '⚠️ 品質堪慮';
    verdictClass = 'review-warning';
  } else if (l1Eval.grade === 'A' || l2Eval.grade === 'A') {
    verdict = '✅ 品質優良';
    verdictClass = 'review-ok';
  } else {
    verdict = agreement ? '✅ 意見一致' : '⚠️ 意見分歧';
    verdictClass = agreement ? 'review-ok' : 'review-warning';
  }

  // backtest current saved prediction if finished
  const actual = isMatchFinished(match)
    ? (match.home_score > match.away_score ? 'home' : match.home_score === match.away_score ? 'draw' : 'away')
    : null;
  let backtest = null;
  if (actual && p.home_win_prob !== undefined) {
    const savedProbs = { home: p.home_win_prob || 0, draw: p.draw_prob || 0, away: p.away_win_prob || 0 };
    const savedPred = Object.keys(savedProbs).reduce((a, b) => savedProbs[a] > savedProbs[b] ? a : b);
    backtest = {
      predicted: activeLabel[savedPred],
      actual: activeLabel[actual],
      hit: savedPred === actual,
      prob: savedProbs[savedPred]
    };
  }

  return { l1Eval, l2Eval, agreement, confidence, verdict, verdictClass, coachVerdict, backtest, actual };
}

function renderPredictionBar(probs, activeLabel) {
  const colors = { home: '#3b82f6', draw: '#94a3b8', away: '#ef4444' };
  const total = Math.max(1, probs.home + probs.draw + probs.away);
  return `
    <div class="prediction-review-bar">
      ${['home','draw','away'].map(k => `
        <div class="review-bar-segment" style="width:${probs[k]/total*100}%;background:${colors[k]}" title="${activeLabel[k]} ${probs[k]}%"></div>
      `).join('')}
    </div>
    <div class="prediction-review-legend">
      ${['home','draw','away'].map(k => `<span><span class="review-dot" style="background:${colors[k]}"></span>${activeLabel[k]} ${probs[k]}%</span>`).join(' · ')}
    </div>
  `;
}

function renderModelEvalCard(ev, activeLabel) {
  const gradeClass = ev.grade === 'A' ? 'grade-a' : ev.grade === 'B' ? 'grade-b' : ev.grade === 'C' ? 'grade-c' : 'grade-d';
  const comments = [...ev.praise, ...ev.critique].slice(0, 3);
  return `
    <div class="review-model-card">
      <div class="review-model-header">
        <strong>${ev.name}</strong>
        <span class="review-grade ${gradeClass}">${ev.grade}</span>
      </div>
      <div class="review-outcome">${ev.outcome}</div>
      ${renderPredictionBar(ev.probs, activeLabel)}
      <div class="review-note">${ev.reason}</div>
      ${ev.score && (ev.score.home || ev.score.away) ? `<div class="review-note">比數預測 ${ev.score.home}-${ev.score.away}</div>` : ''}
      <div class="review-stability">穩定度 ${ev.stability}/100 · 領先幅度 ${ev.margin}%</div>
      ${comments.length ? `<ul class="model-comments">${comments.map(c => `<li>${c}</li>`).join('')}</ul>` : ''}
      ${ev.resultComment ? `<div class="model-result ${ev.resultComment.startsWith('✅') ? 'hit' : 'miss'}">${ev.resultComment}</div>` : ''}
    </div>
  `;
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

  // 3. Coach-style strict reviewer
  const review = computePredictionReview(match);
  const activeLabel = { home: '主勝', draw: '和局', away: '客勝' };

  const rows = [...historyRows, ...currentRows];

  let html = '';

  // Reviewer panel
  html += `
    <div class="prediction-review-panel">
      <h4>🔍 預測審查評語（L1 FIFA vs L2 Elo）</h4>
      <div class="review-verdict ${review.verdictClass}">${review.verdict}</div>
      <div class="review-coach-box">
        ${review.coachVerdict.map(line => `<p>${line}</p>`).join('')}
      </div>
      <div class="review-summary">
        ${renderModelEvalCard(review.l1Eval, activeLabel)}
        ${renderModelEvalCard(review.l2Eval, activeLabel)}
      </div>
      ${review.backtest ? `
        <div class="review-backtest ${review.backtest.hit ? 'hit' : 'miss'}">
          <strong>實際結果驗證：</strong>
          預測 ${review.backtest.predicted}（${review.backtest.prob}%）
          vs 實際 ${review.backtest.actual} → ${review.backtest.hit ? '✅ 命中' : '❌ 未命中'}
        </div>
      ` : (isMatchFinished(match) ? '<div class="review-note">此場已結束但沒有機率預測資料，無法驗證。</div>' : '<div class="review-note">比賽尚未結束，賽後將顯示實際結果驗證。</div>')}
    </div>
  `;

  if (!rows.length) {
    html += '<p>尚無預測記錄。</p>';
  } else {
    html += `
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

  body.innerHTML = html;

  // 載入並顯示用戶反饋面板
  const feedbackMap = await loadFeedbackForMatch(matchId);
  renderFeedbackPanel(matchId, feedbackMap);
}

function setupPredictionHistoryModal() {
  const modal = document.getElementById('prediction-history-modal');
  if (!modal) return;
  modal.addEventListener('click', (e) => {
    if (e.target === modal || e.target.closest('.modal-close')) {
      modal.classList.add('hidden');
    }
  });

  // 用戶反饋送出按鈕
  const feedbackPanel = document.getElementById('user-feedback-panel');
  if (!feedbackPanel) return;
  feedbackPanel.addEventListener('click', async (e) => {
    const btn = e.target.closest('.feedback-submit');
    if (!btn) return;
    const model = btn.dataset.model;
    const row = btn.closest('.feedback-row');
    const select = row ? row.querySelector('.feedback-select') : null;
    const status = row ? row.querySelector('.feedback-status') : null;
    if (!select || !status || !currentFeedbackMatchId) return;
    const value = parseFloat(select.value);
    if (Number.isNaN(value)) {
      status.textContent = '請先選擇獎懲分數';
      status.className = 'feedback-status err';
      return;
    }
    btn.disabled = true;
    status.textContent = '送出中...';
    status.className = 'feedback-status';
    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ match_id: currentFeedbackMatchId, model, feedback: value })
      });
      const result = await res.json();
      if (res.ok && result.ok) {
        status.textContent = `已記錄 ${value > 0 ? '+' : ''}${value}`;
        status.className = 'feedback-status ok';
        currentFeedbackMap[model] = value;
      } else {
        status.textContent = `失敗：${result.error || 'unknown'}`;
        status.className = 'feedback-status err';
      }
    } catch (err) {
      status.textContent = `網路錯誤：${err.message}`;
      status.className = 'feedback-status err';
    } finally {
      btn.disabled = false;
    }
  });
}

let currentFeedbackMatchId = null;
let currentFeedbackMap = {};

async function loadFeedbackForMatch(matchId) {
  try {
    const res = await fetch(`/api/feedback?match_id=${encodeURIComponent(matchId)}`);
    if (!res.ok) return {};
    return await res.json();
  } catch (e) {
    console.error('loadFeedbackForMatch failed', e);
    return {};
  }
}

function renderFeedbackPanel(matchId, feedbackMap) {
  currentFeedbackMatchId = matchId;
  currentFeedbackMap = feedbackMap || {};
  const panel = document.getElementById('user-feedback-panel');
  if (!panel) return;
  panel.classList.remove('hidden');
  ['l1', 'l2'].forEach(model => {
    const row = panel.querySelector(`#feedback-row-${model}`);
    if (!row) return;
    const select = row.querySelector('.feedback-select');
    const status = row.querySelector('.feedback-status');
    const existing = currentFeedbackMap[model];
    if (select) select.value = existing !== undefined ? String(existing) : '';
    if (status) {
      if (existing !== undefined) {
        status.textContent = `已記錄 ${existing > 0 ? '+' : ''}${existing}`;
        status.className = 'feedback-status ok';
      } else {
        status.textContent = '';
        status.className = 'feedback-status';
      }
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
  // 載入 Elo 評分並合併到 teams
  try {
    const eloRes = await fetch('/api/elo_ratings');
    if (eloRes.ok) {
      const eloData = await eloRes.json();
      teams.forEach(t => {
        const rating = eloData[t.name_zh] || eloData[t.name_en];
        if (rating) t.elo_rating = rating;
      });
    }
  } catch (e) {
    console.error('Failed to load Elo ratings', e);
  }
  renderNextMatch();
  renderPredictions('小組賽');
  renderMatches();
  renderStandings();
  setupPredictionTabs();
  setupModelTabs();
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

function setupModelTabs() {
  const tabs = document.querySelectorAll('.model-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      activeModel = tab.dataset.model;
      // refresh visible predictions
      const activeStageTab = document.querySelector('.stage-tab.active');
      const stage = activeStageTab ? activeStageTab.dataset.stage : '小組賽';
      renderPredictions(stage);
    });
  });
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
    const activeModelTab = document.querySelector('.model-tab.active');
    const modelLabel = activeModelTab ? activeModelTab.textContent.trim() : activeModel.toUpperCase();
    const version = document.getElementById('version')?.textContent?.trim() || '';
    const lastUpdate = document.getElementById('last-update')?.textContent?.trim() || '';
    const nowStr = new Date().toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' }).replace(/\//g, '-');
    const header = `下載時間: ${nowStr} Asia/Taipei | 版本: ${version} | 模型: ${modelLabel} | 最後更新: ${lastUpdate}\n`;
    const content = document.getElementById('prediction-content').innerText;
    const blob = new Blob([header + '\n' + content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `WorldCup2026_預測_${stage}_${activeModel.toUpperCase()}.txt`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 0);
  });
}

function computeGroupPredictions() {
  // 根據活躍模型計算球隊強度
  const strengthFor = (teamName) => {
    const team = getTeam(teamName);
    const rankStrength = 100 - (team.fifa_ranking || 999);
    if (activeModel !== 'l2') return rankStrength;
    // L2: 混合 Elo 強度（透過 server endpoint 取得預測強度）
    const rating = team.elo_rating || team.fifa_ranking || 999;
    return Math.max(0, 2400 - rating) / 6; // normalize roughly 0-100
  };

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

    // 剩餘場次模擬：依活躍模型強度
    groups[g].filter(m => !isMatchFinished(m)).forEach(m => {
      const homeStrength = strengthFor(m.home_team);
      const awayStrength = strengthFor(m.away_team);
      const total = homeStrength + awayStrength;
      const homeWinProb = total ? homeStrength / total : 0.5;
      const awayWinProb = total ? awayStrength / total : 0.5;
      const drawProb = 0.25;
      const normalizedHome = homeWinProb * (1 - drawProb);
      const normalizedAway = awayWinProb * (1 - drawProb);

      const home = standings[m.home_team];
      const away = standings[m.away_team];
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
  const modelLabel = activeModel === 'l2' ? 'L2 Elo' : 'L1 FIFA';
  const rankField = activeModel === 'l2' ? 'elo_rating' : 'fifa_ranking';

  // 簡單邏輯：取各組前兩名，依模型排名晉級
  const groups = computeGroupPredictions();
  const qualified = groups.flatMap(g => g.rows.slice(0, 2).map((r, idx) => ({
    ...r,
    seed: idx === 0 ? `${g.group}1` : `${g.group}2`,
    modelRank: r[rankField] || 999
  })));

  const pickByRank = (list, count) => list.sort((a, b) => a.modelRank - b.modelRank).slice(0, count);

  let content = `<div class="prediction-stage-title">🔮 ${titles[stage]} <span style="color:var(--muted);font-size:0.85rem;">(${modelLabel})</span></div>`;

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
    const rankField = activeModel === 'l2' ? 'elo_rating' : 'fifa_ranking';
    const baseProb = activeModel === 'l2' ? 100 : 100;
    content += `
      <div class="prediction-bracket">
        <div class="prediction-row" style="border-left:4px solid gold;">
          <div class="prediction-team">${getFlagHTML({flag_img: '', flag: champion.flag, name_zh: champion.team})}🏆 冠軍：${champion.team} <span style="color:var(--muted);font-size:0.8rem;">(${rankField === 'elo_rating' ? 'Elo' : 'FIFA'} ${champion[rankField] || champion.rank})</span></div>
          <div class="prediction-prob">${Math.round(baseProb - (champion[rankField] || champion.rank) * 0.25)}%</div>
        </div>
        <div class="prediction-row" style="border-left:4px solid silver;">
          <div class="prediction-team">${getFlagHTML({flag_img: '', flag: runnerUp.flag, name_zh: runnerUp.team})}🥈 亞軍：${runnerUp.team} <span style="color:var(--muted);font-size:0.8rem;">(${rankField === 'elo_rating' ? 'Elo' : 'FIFA'} ${runnerUp[rankField] || runnerUp.rank})</span></div>
          <div class="prediction-prob">${Math.round((baseProb - 10) - (runnerUp[rankField] || runnerUp.rank) * 0.25)}%</div>
        </div>
        <div class="prediction-row" style="border-left:4px solid #cd7f32;">
          <div class="prediction-team">${getFlagHTML({flag_img: '', flag: third.flag, name_zh: third.team})}🥉 季軍：${third.team} <span style="color:var(--muted);font-size:0.8rem;">(${rankField === 'elo_rating' ? 'Elo' : 'FIFA'} ${third[rankField] || third.rank})</span></div>
          <div class="prediction-prob">${Math.round((baseProb - 20) - (third[rankField] || third.rank) * 0.25)}%</div>
        </div>
      </div>
    `;
  }

  return content;
}

function renderMatchList(teamsList) {
  if (!teamsList.length) return '<p>尚無資料</p>';
  const rankField = activeModel === 'l2' ? 'elo_rating' : 'fifa_ranking';
  const rankLabel = activeModel === 'l2' ? 'Elo' : 'FIFA';
  return `
    <div class="prediction-list">
      ${teamsList.map((t, i) => `
        <div class="prediction-row">
          <div class="prediction-team">${getFlagHTML({flag_img: '', flag: t.flag, name_zh: t.team})}${i + 1}. ${t.team} <span style="color:var(--muted);font-size:0.8rem;">(${rankLabel} ${t[rankField] || t.rank})</span></div>
          <div class="prediction-prob">${Math.max(10, Math.round(100 - (t[rankField] || t.rank)))}%</div>
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
  let spanClass = 'pred-pre';
  if (m.status === 'finished') {
    const isHit = p.hit === true || m.hit === true;
    summary = isHit ? `✅ 命中 (${predictedLabel} ${probValue}%)` : `❌ 未命中`;
    spanClass = isHit ? 'pred-hit' : 'pred-miss';
  } else {
    summary = `🔮 ${predictedLabel} ${probValue}%`;
  }

  const scoreText = p.score !== undefined ? `(${p.score > 0 ? '+' : ''}${p.score}分)` : '';
  const preHtml = `<span class="${spanClass}">${summary} ${scoreText}</span>`;
  const btnHtml = `<button class="pred-detail-btn" data-match-id="${m.match_id}">${preHtml}</button>`;
  const details = [];
  if (p.home_win_prob !== undefined && p.away_win_prob !== undefined && p.draw_prob !== undefined) {
    details.push(`主 ${p.home_win_prob}% / 和 ${p.draw_prob}% / 客 ${p.away_win_prob}%`);
    details.push(`比數預測 ${homePred ?? '-'} - ${awayPred ?? '-'}`);
  } else if (homePred != null && awayPred != null) {
    details.push(`比數預測 ${homePred} - ${awayPred}`);
  }
  if (p.reason) details.push(p.reason);
  return btnHtml +
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

