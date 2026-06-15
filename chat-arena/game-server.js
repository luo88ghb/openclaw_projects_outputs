/**
 * 推論猜謎對決 - 遊戲引擎 v4.0
 * 
 * 遊戲流程：
 * 1. 🐢 傑尼 (主控/裁判) 派遣任務
 * 2. 🎨 迪尼出題 → 🦐 蝦蝦回答
 * 3. 傑尼裁決 → 更新分數 → 換邊
 * 4. 🦐 蝦蝦出題 → 🎨 迪尼回答
 * 5. 重複直到 10 回合結束
 *
 * 傑尼韌性連線：
 * - 首選: Cloud (minimax-m2.7:cloud)
 * - 備援: Local (gemma4:e2b) 不受網路限制
 * - 連線受限時傑尼主動提示用戶做決策
 */

const express = require('express');
const cors = require('cors');
const { spawn, execFile } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');
const http = require('http');

const app = express();
const PORT = 3001;

// Detect if running in Docker
const isDocker = fs.existsSync('/.dockerenv');

// Gateway 設定
let GATEWAY_HOST = process.env.GATEWAY_HOST || (isDocker ? 'host.docker.internal' : '127.0.0.1');
const GATEWAY_PORT = process.env.GATEWAY_PORT || '18789';

// Token 讀取函數
function getGatewayToken() {
    // 優先使用環境變數
    if (process.env.OPENCLAW_TOKEN) {
        console.log('[Game] 使用環境變數中的 OPENCLAW_TOKEN');
        return process.env.OPENCLAW_TOKEN;
    }

    // 嘗試從 OpenClaw 配置讀取
    // 支援 Docker (Linux) 和 Windows 環境的路徑
    const configPaths = [
        // Windows 配置文件（主要）
        'C:\\Users\\danny\\.openclaw\\openclaw.json',
        process.env.USERPROFILE + '\\.openclaw\\openclaw.json',
        // Docker/Linux 環境
        '/.openclaw/openclaw.json',
        '/workspace/.openclaw/openclaw.json'
    ];

    for (const configPath of configPaths) {
        try {
            if (fs.existsSync(configPath)) {
                const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
                console.log(`[Game] 找到配置文件：${configPath}`);

                // 檢查巢狀結構：gateway.auth.token
                if (config.gateway?.auth?.token) {
                    console.log('[Game] 從 gateway.auth.token 讀取到 Token');
                    return config.gateway.auth.token;
                }

                // 檢查常見的 token 欄位名稱（扁平結構）
                const tokenFields = ['gatewayToken', 'token', 'apiKey', 'OPENCLAW_TOKEN', 'gateway.token'];
                for (const field of tokenFields) {
                    if (config[field]) {
                        console.log(`[Game] 從 ${field} 欄位讀取到 Token`);
                        return config[field];
                    }
                }

                // 如果配置文件存在但找不到 token 欄位，顯示預覽（不含敏感資料）
                const availableFields = Object.keys(config).filter(k => !k.includes('token') && !k.includes('key') && !k.includes('secret'));
                console.log(`[Game] 配置檔案存在但未找到標準 Token 欄位，可用的非敏感欄位：${availableFields.join(', ')}`);
            }
        } catch (e) {
            console.log(`[Game] 嘗試讀取 ${configPath} 失敗：${e.message}`);
        }
    }

    // 最後使用預設值
    console.log('[Game] ⚠️ 無法找到有效 Token，使用預設值');
    return 'b2b74e244db78d9dc7f3711476f78236f367279cf968124e';
}
const GATEWAY_TOKEN = getGatewayToken();
console.log(`[Game] Gateway 設定：${GATEWAY_HOST}:${GATEWAY_PORT}`);

// ============= Model Configuration =============
// 各角色的專屬多模型分配（依照用戶建議實驗新配置）
const MODEL_CONFIG = {
    zeni: 'ollama/gemma4:31b-cloud,ollama/gemma4:e4b-it-q4_K_M',    // 傑尼：裁判
    designer: 'ollama/glm-5:cloud,ollama/gemma4:e4b-it-q4_K_M',     // 迪尼：出題
    xiaxia: 'ollama/gpt-oss:120b-cloud,ollama/gemma4:e4b-it-q4_K_M', // 蝦蝦：答題

    // 為了相容性保留舊版參數
    cloud: 'ollama/gemma4:31b-cloud',
    local: 'ollama/gemma4:e4b-it-q4_K_M',
};

// 目前連線模式（用來判斷是否處於降級狀態）
let connectionMode = 'cloud'; // 新增：定義全域變數避免 ReferenceError
let rateLimitHitAt = null;   // 最後一次遇到 Rate Limit 的時間
let rateLimitCooldown = 60;  // 冷卻時間（秒），超過後自動嘗試切換回雲端
let retryTimer = null;       // 等待重試的 Timer

/**
 * 核心診斷：測試 Gateway 是否連線成功
 */
async function testGateway(host) {
    return new Promise((resolve) => {
        const options = {
            hostname: host,
            port: GATEWAY_PORT,
            path: '/gateway',
            method: 'GET',
            timeout: 5000,
            headers: { 'Authorization': 'Bearer ' + GATEWAY_TOKEN }
        };
        const req = http.request(options, (res) => {
            if (res.statusCode < 500) {
                resolve(true);
            } else {
                console.log(`[🐢 傑尼] Gateway @ ${host} 回傳錯誤狀態碼: ${res.statusCode}`);
                resolve(false);
            }
        });
        req.on('error', (err) => {
            // 不顯示連線失敗的詳細報錯，避免洗版，除非是 127.0.0.1
            if (host === '127.0.0.1') {
                console.log(`[🐢 傑尼] 連線 127.0.0.1 失敗: ${err.message}`);
            }
            resolve(false);
        });
        req.on('timeout', () => { req.destroy(); resolve(false); });
        req.end();
    });
}

/**
 * 自動尋找正確的 Gateway 地址（含啟動重試邏輯）
 */
async function autoDetectGateway() {
    const candidates = ['127.0.0.1', 'localhost', 'host.docker.internal', '172.17.0.1', '192.168.65.2'];
    const maxAttempts = 5;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        console.log(`[🐢 傑尼] 嘗試連線 Gateway (${attempt}/${maxAttempts})...`);
        for (const host of candidates) {
            if (await testGateway(host)) {
                GATEWAY_HOST = host;
                console.log(`[🐢 傑尼] ✨ 成功連線至 Gateway: ${host}`);
                connectionMode = 'cloud';
                updateConnectionStatus('cloud');
                return true;
            }
        }
        if (attempt < maxAttempts) await delay(3000); // 增加等待時間
    }

    console.log(`[🐢 傑尼] ❌ 所有候選地址均連線失敗。傑尼將進入降級模式。`);
    connectionMode = 'degraded';
    updateConnectionStatus('degraded', 'NETWORK_DISCONNECTED');
    return false;
}

console.log(`[Game] Running on ${isDocker ? 'Docker' : 'Windows'}, Initial Host: ${GATEWAY_HOST}`);
console.log(`[Game] 🐢 傑尼主控模式啟動。首選模型: ${MODEL_CONFIG.cloud}`);

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Player workspace paths
const PLAYERS = {
    'designer': {
        name: '迪尼',
        emoji: '🎨',
        cwd: '/workspace/.openclaw/agents/agent-designer-lab'
    },
    'xiaxia': {
        name: '蝦蝦',
        emoji: '🦐',
        cwd: '/workspace/.openclaw/agents/agent-xiaxia'
    },
    'zeni': {
        name: '傑尼',
        emoji: '🐢',
        cwd: '/workspace/.openclaw/agents/agent-zeni'
    }
};

// Game phases enum
const PHASE = {
    IDLE: 'idle',                       // 等待開始
    DESIGNER_ASKING: 'designer_asking',  // 迪尼構思題目中
    XIAXIA_ANSWERING: 'xiaxia_answering',// 蝦蝦回答中
    JUDGE_PENDING: 'judge_pending',      // 等待裁決
    XIAXIA_ASKING: 'xiaxia_asking',      // 蝦蝦構思題目中
    DESIGNER_ANSWERING: 'designer_answering', // 迪尼回答中
    GAME_OVER: 'game_over',             // 比賽結束
    PAUSED_BY_ZENI: 'paused_by_zeni',   // 傑尼暫停 - 等待用戶決策
};

// Game State
let game = {
    round: 1,
    maxRounds: 10,
    phase: PHASE.IDLE,
    scores: {
        designer: 0,
        xiaxia: 0
    },
    players: {
        designer: { status: 'offline', lastSeen: null },
        xiaxia: { status: 'offline', lastSeen: null }
    },
    currentQuestion: null,
    currentAnswer: null,
    currentStandardAnswer: null,
    questioner: null,
    answerer: null,
    questions: [],
    timeLeft: 0,
    gameOver: false,
    lastUpdated: new Date().toISOString(),
    history: [],
    manualMode: false,
    // 傑尼監控系統
    zeniMessage: null,          // 傑尼當前訊息
    zeniActions: [],            // 傑尼提供的決策選項
    zeniLog: [],                // 傑尼完整監控日誌
    connectionStatus: {
        mode: 'cloud',          // 'cloud' | 'local' | 'degraded'
        model: MODEL_CONFIG.cloud,
        lastError: null,
        rateLimitAt: null,
        retryIn: null           // 倒數幾秒後自動重試
    }
};

// Timer
let gameTimer = null;
let clients = [];
let isProcessing = false;
let pausedPhaseBeforeZeni = null; // 傑尼暫停前的狀態，用於恢復

// ============= Helper Functions =============

function saveState() {
    game.lastUpdated = new Date().toISOString();
    try {
        fs.writeFileSync('game-state.json', JSON.stringify(game, null, 2));
    } catch (e) {
        console.log('[Game] Warning: Could not save state file');
    }
}

function broadcastSSE() {
    const data = JSON.stringify({ game, timeLeft: game.timeLeft });
    clients.forEach(client => {
        try {
            client.write(`data: ${data}\n\n`);
        } catch (e) {
            clients = clients.filter(c => c !== client);
        }
    });
}

function resetTimer(seconds) {
    game.timeLeft = seconds;
    if (gameTimer) clearInterval(gameTimer);

    gameTimer = setInterval(() => {
        game.timeLeft--;
        broadcastSSE();

        if (game.timeLeft <= 0) {
            clearInterval(gameTimer);
            handleTimeout();
        }
    }, 1000);
}

function handleTimeout() {
    console.log('[Game] Timer expired!');

    if (game.phase === PHASE.XIAXIA_ANSWERING || game.phase === PHASE.DESIGNER_ANSWERING) {
        // 答題超時 - 給分給問答的人
        const questioner = game.questioner;
        game.scores[questioner]++;

        game.history.push({
            round: game.round,
            questioner: game.questioner,
            answerer: game.answerer,
            question: game.currentQuestion,
            answer: '（超時未回答）',
            result: 'timeout',
            pointsTo: questioner
        });

        console.log(`[Game] ${PLAYERS[questioner].emoji} ${PLAYERS[questioner].name} scores! (timeout)`);

        // 進入裁決階段
        game.phase = PHASE.JUDGE_PENDING;
        game.currentAnswer = '（超時未回答）';
        saveState();
        broadcastSSE();
    }
}

function updatePlayerStatus(player, status) {
    if (PLAYERS[player]) {
        game.players[player] = {
            status: status,
            lastSeen: new Date().toISOString()
        };
        broadcastSSE();
    }
}

// ============= 傑尼主控系統 =============

/**
 * 傑尼警告系統：向用戶發出警告並提供決策選項
 * @param {string} message - 傑尼的警告訊息
 * @param {string} errorType - 'rate_limit' | 'timeout' | 'connection' | 'info'
 * @param {string[]} actions - 可選的用戶動作
 */
function zeniAlert(message, errorType = 'info', actions = ['manual', 'pause', 'stop', 'wait']) {
    const logEntry = {
        time: new Date().toISOString(),
        message,
        errorType,
        actions
    };

    console.log(`[🐢 傑尼] ${errorType.toUpperCase()}: ${message}`);

    game.zeniMessage = { ...logEntry };
    game.zeniActions = actions;
    game.zeniLog.push(logEntry);

    // 最多保留 50 則日誌
    if (game.zeniLog.length > 50) game.zeniLog.shift();

    saveState();
    broadcastSSE();
}

/**
 * 更新連線狀態
 */
function updateConnectionStatus(mode, error = null, retryIn = null) {
    connectionMode = mode;
    activeModel = mode === 'local' ? MODEL_CONFIG.local : MODEL_CONFIG.cloud;

    game.connectionStatus = {
        mode,
        model: activeModel,
        lastError: error,
        rateLimitAt: rateLimitHitAt ? rateLimitHitAt.toISOString() : null,
        retryIn
    };

    console.log(`[🐢 傑尼] 連線模式切換：${mode}，使用模型：${activeModel}`);
    broadcastSSE();
}

/**
 * 傑尼偵測到 Rate Limit，切換至本地模型並暫停遊戲
 */
function handleRateLimit(player) {
    rateLimitHitAt = new Date();

    // 切換至本地模型
    updateConnectionStatus('local', 'rate_limit_429');

    // 暫停遊戲，等待用戶決策
    pausedPhaseBeforeZeni = game.phase;
    game.phase = PHASE.PAUSED_BY_ZENI;

    const playerName = player ? `${PLAYERS[player].emoji} ${PLAYERS[player].name}` : '代理人';

    zeniAlert(
        `⚠️ 偵測到外部 API 連線受限 (Rate Limit 429)！${playerName} 目前無法取得雲端 AI 資源。傑尼已切換至本地備援模型 (gemma4:e2b)。請選擇如何繼續：`,
        'rate_limit',
        ['manual', 'pause', 'stop', 'wait']
    );

    isProcessing = false;
}

/**
 * 啟動等待重試計時器（傑尼自動等待再試）
 */
function startRetryCountdown(seconds, onComplete) {
    let remaining = seconds;

    if (retryTimer) clearInterval(retryTimer);

    retryTimer = setInterval(() => {
        remaining--;
        game.connectionStatus.retryIn = remaining;
        broadcastSSE();

        if (remaining <= 0) {
            clearInterval(retryTimer);
            retryTimer = null;
            game.connectionStatus.retryIn = null;
            zeniAlert('⏱️ 等待時間結束，傑尼正在嘗試恢復雲端連線...', 'info', []);

            // 嘗試切回雲端
            updateConnectionStatus('cloud');
            onComplete();
        }
    }, 1000);
}

// Spawn subagent via OpenClaw CLI (v5 - 修復 API 路徑問題)
/**
 * 子代理人啟動函數 v5
 * - 使用 openclaw agent CLI 而非 HTTP API
 * - 具備重試機制（最多 3 次）
 * - 自動偵測 429 Rate Limit
 * - 失敗時觸發傑尼警告系統
 */
function spawnSubagentTask(task, player, timeoutMs = 300000, retryCount = 0) {
    return new Promise((resolve, reject) => {
        const label = `${player}-game-${Date.now()}`;
        const sessionId = `game-${player}-${Date.now()}`;
        // 依據玩家角色決定模型字串（如果網路中斷強制為 local，則取本地模型，否則取專屬串）
        let modelToUse = MODEL_CONFIG[player] || MODEL_CONFIG.zeni;
        // 注意：如果在 handleRateLimit 階段被強制切換為 local，為避免影響所有流程，這裡不再單一強制覆蓋，而是讓 OpenClaw 自動 fallback 到最後一個本地模型。

        const timeoutSeconds = Math.floor(timeoutMs / 1000);

        console.log(`[🐢 傑尼] 派遣 ${PLAYERS[player]?.emoji || '🐢'} ${PLAYERS[player]?.name || '裁判'}... (模型: ${modelToUse.split(',')[0]} 等, 第 ${retryCount + 1} 次嘗動)`);
        if (PLAYERS[player]) updatePlayerStatus(player, 'thinking');

        // 更新連線狀態顯示
        game.connectionStatus.model = modelToUse;
        game.connectionStatus.mode = connectionMode;
        broadcastSSE();

        // 建構 openclaw agent 命令
        const args = [
            'agent',
            '--message', task,
            '--session-id', sessionId,
            '--json',
            '--timeout', String(timeoutSeconds)
        ];

        // Windows 上 spawn 不能直接執行 .cmd 檔（EINVAL），
        // 但 shell=true 會拆解多行參數。
        // 解決方案：直接用 node.exe 執行 openclaw 的 JS 入口檔
        const nodeExe = process.execPath; // 當前 node.exe 的完整路徑
        const openclawEntry = path.join(
            process.env.APPDATA || '', 'npm', 'node_modules', 'openclaw', 'dist', 'index.js'
        );

        console.log(`[🐢 傑尼] 執行命令: node ${openclawEntry} agent --session-id ${sessionId}`);

        const proc = spawn(nodeExe, [openclawEntry, ...args], {
            cwd: process.cwd(),
            timeout: timeoutMs + 60000,
            env: {
                ...process.env,
                OPENCLAW_TOKEN: GATEWAY_TOKEN,
                // 修正：確保包含 http:// 前綴，解決子代理人找不到 Gateway 的問題
                OPENCLAW_GATEWAY: `http://${GATEWAY_HOST}:${GATEWAY_PORT}`,
                OPENCLAW_MODEL: modelToUse
            }
        });

        let output = '';
        let stderr = '';

        proc.stdout.on('data', (d) => { output += d.toString(); });
        proc.stderr.on('data', (d) => { stderr += d.toString(); });

        proc.on('close', (code) => {
            const playerLabel = `${PLAYERS[player].emoji} ${PLAYERS[player].name}`;
            console.log(`[🐢 傑尼] ${playerLabel} 子代理人結束，exit code: ${code}`);
            console.log(`[🐢 傑尼] stdout 長度: ${output.length}, stderr 長度: ${stderr.length}`);
            if (output) console.log(`[🐢 傑尼] stdout 預覽: ${output.substring(0, 300)}...`);
            if (stderr) console.log(`[🐢 傑尼] stderr 預覽: ${stderr.substring(0, 300)}...`);

            // ============= 第一優先：嘗試解析 JSON 輸出 =============
            // 重要：openclaw agent --json 即使成功也可能回傳 exit code 1
            // 因此必須先嘗試解析輸出，有效 JSON 視為成功
            let parsed = null;
            let assistantText = null;
            let executionTrace = null;

            try {
                const jsonStart = output.indexOf('{');
                if (jsonStart !== -1) {
                    const jsonStr = output.substring(jsonStart);
                    parsed = JSON.parse(jsonStr);
                    // executionTrace 可能在頂層或 result.meta 中
                    executionTrace = parsed.executionTrace ||
                        parsed.result?.meta?.executionTrace ||
                        null;
                    // assistantText 的多種可能路徑（依 OpenClaw 版本而異）
                    assistantText = parsed.result?.payloads?.[0]?.text ||        // v2026: result.payloads[0].text
                        parsed.payloads?.[0]?.text ||                // 備用: payloads[0].text
                        parsed.payloads?.[0]?.content?.[0]?.text ||   // 舊版: payloads[0].content[0].text
                        parsed.finalAssistantVisibleText ||           // 備用: finalAssistantVisibleText
                        parsed.finalAssistantRawText ||              // 備用: finalAssistantRawText
                        null;

                    if (!assistantText && parsed.result?.payloads) {
                        console.log(`[🐢 傑尼] payload 結構預覽:`, JSON.stringify(parsed.result.payloads[0]).substring(0, 200));
                    }
                }
            } catch (e) {
                console.log(`[🐢 傑尼] JSON 解析失敗: ${e.message}`);
            }

            // ============= 診斷摘要（寫入監控日誌） =============
            const diagInfo = {
                exitCode: code,
                hasOutput: !!output,
                hasStderr: !!stderr,
                hasParsedJson: !!parsed,
                hasAssistantText: !!assistantText,
                model: executionTrace?.winnerModel || modelToUse,
                provider: executionTrace?.winnerProvider || '未知',
                runner: executionTrace?.runner || '未知',
                fallbackUsed: executionTrace?.fallbackUsed || false,
                attempts: executionTrace?.attempts || [],
                stopReason: parsed?.stopReason || parsed?.completion?.stopReason || null,
            };

            console.log(`[🐢 傑尼] 診斷摘要:`, JSON.stringify(diagInfo, null, 2));

            // ============= 成功判定：有有效 JSON 且含 assistantText =============
            if (parsed && assistantText) {
                // 更新實際使用的模型資訊
                game.connectionStatus.model = diagInfo.model;
                game.connectionStatus.actualProvider = diagInfo.provider;
                game.connectionStatus.runner = diagInfo.runner;

                updatePlayerStatus(player, 'waiting');

                const modelInfo = `${diagInfo.provider}/${diagInfo.model} (${diagInfo.runner})`;
                console.log(`[🐢 傑尼] ✅ ${playerLabel} 成功回應！模型: ${modelInfo}, 輸出: ${assistantText.length} 字`);

                // 記錄成功的執行追蹤到監控日誌
                zeniAlert(
                    `✅ ${playerLabel} 回應成功｜模型: ${diagInfo.model}｜提供者: ${diagInfo.provider}｜執行器: ${diagInfo.runner}`,
                    'info', []
                );

                if (connectionMode === 'local' && modelToUse === MODEL_CONFIG.local) {
                    zeniAlert(`✅ 備援模型成功響應！如需切換回雲端模型，請按「等待重試」。`, 'info', ['switch_cloud']);
                }

                resolve({ output: assistantText, sessionId, fullOutput: parsed });
                return;
            }

            // ============= 以下為失敗處理 =============
            // 到這裡表示沒有有效的 JSON 輸出，或缺少 assistantText

            const combined = output + '\n' + stderr;

            // 檢查 Rate Limit
            if (combined.includes('429') || combined.includes('rate_limit') || combined.includes('Rate limit')) {
                console.log(`[🐢 傑尼] 偵測到 429 Rate Limit！`);
                updatePlayerStatus(player, 'rate_limited');

                // 從執行追蹤中提取失敗的模型資訊
                const failedAttempts = diagInfo.attempts.filter(a => a.result !== 'success');
                const failedModels = failedAttempts.map(a => `${a.provider}/${a.model}`).join(', ') || '未知模型';

                if (connectionMode === 'cloud') {
                    console.log(`[🐢 傑尼] 切換至本地備援模型重試...`);
                    updateConnectionStatus('local', 'rate_limit_429');
                    zeniAlert(
                        `⚠️ 雲端 API 連線受限 (429)！受限模型: ${failedModels}。傑尼已切換至本地備援模型重試...`,
                        'rate_limit', []
                    );
                    spawnSubagentTask(task, player, timeoutMs, retryCount + 1)
                        .then(resolve)
                        .catch(reject);
                    return;
                } else {
                    handleRateLimit(player);
                    reject(new Error('RATE_LIMIT: 本地與雲端模型均受限'));
                    return;
                }
            }

            // 檢查伺服器錯誤
            if (code === 3 || combined.includes('SERVER_ERROR') || combined.includes('Server error') || combined.includes('Internal Server Error')) {
                console.log(`[🐢 傑尼] Gateway 伺服器錯誤！`);
                updatePlayerStatus(player, 'error');
                const serverErrSnippet = (stderr || output).substring(0, 150).replace(/\n/g, ' ');
                zeniAlert(
                    `❌ Gateway 伺服器錯誤！\n詳情: ${serverErrSnippet}`,
                    'connection', ['manual', 'pause', 'stop']
                );
                game.phase = PHASE.PAUSED_BY_ZENI;
                saveState();
                reject(new Error('SERVER_ERROR: Gateway 錯誤'));
                return;
            }

            // ============= 精確錯誤分類 =============
            let errorDetail = '';
            let errorType = 'connection';
            let errorHint = '';

            // 嘗試從輸出中提取具體錯誤
            if (!output && !stderr) {
                errorDetail = 'CLI_NO_OUTPUT';
                errorHint = '（openclaw 命令無任何輸出，可能 CLI 未正確安裝或 PATH 設定有誤）';
            } else if (combined.includes('ECONNREFUSED')) {
                errorDetail = 'ECONNREFUSED';
                errorType = 'connection_refused';
                errorHint = '（Gateway 連線被拒絕，請確認 Gateway 服務是否啟動）';
            } else if (combined.includes('ETIMEDOUT') || combined.includes('timeout') || combined.includes('Timeout')) {
                errorDetail = 'MODEL_TIMEOUT';
                errorType = 'timeout';
                errorHint = '（模型 API 回應逾時，可能是模型載入中或 API 服務繁忙）';
            } else if (combined.includes('ENOTFOUND')) {
                errorDetail = 'DNS_ENOTFOUND';
                errorType = 'dns_error';
                errorHint = '（DNS 解析失敗，請檢查網路連線）';
            } else if (
                combined.includes('Unauthorized') || combined.includes('Forbidden') ||
                combined.includes('HTTP 401') || combined.includes('HTTP 403') ||
                combined.includes('status: 401') || combined.includes('status: 403') ||
                combined.includes('"statusCode":401') || combined.includes('"statusCode":403') ||
                stderr.includes('401') || stderr.includes('403')  // stderr 中出現更可信
            ) {
                errorDetail = 'AUTH_FAILED';
                errorType = 'auth_failed';
                errorHint = '（認證失敗，Token 可能已過期或無效）';
            } else if (combined.includes('SPAWN_ERROR')) {
                const errorMatch = combined.match(/SPAWN_ERROR:(.+)/);
                errorDetail = errorMatch ? `SPAWN_ERROR: ${errorMatch[1].trim()}` : 'SPAWN_ERROR';
                errorHint = '（代理人生成失敗）';
            } else if (combined.includes('SPAWN_TIMEOUT')) {
                errorDetail = 'SPAWN_TIMEOUT';
                errorHint = '（代理人生成逾時）';
            } else if (combined.includes('model') && combined.includes('not found')) {
                errorDetail = 'MODEL_NOT_FOUND';
                errorHint = `（模型 ${modelToUse} 未在 Gateway 中註冊或不可用）`;
            } else if (parsed && !assistantText) {
                // JSON 解析成功但沒有 assistantText
                errorDetail = 'EMPTY_RESPONSE';
                errorHint = '（模型回應為空，可能是 prompt 過長或模型錯誤）';
                // 嘗試從執行追蹤找更多資訊
                const failedAttempts = diagInfo.attempts.filter(a => a.result !== 'success');
                if (failedAttempts.length > 0) {
                    const failInfo = failedAttempts.map(a => `${a.provider}/${a.model}: ${a.result}`).join('; ');
                    errorHint = `（模型嘗試失敗: ${failInfo}）`;
                    errorDetail = 'MODEL_ATTEMPTS_FAILED';
                }
            } else {
                // 從 stderr 截取最有意義的一段作為錯誤描述
                const stderrLines = stderr.split('\n').filter(l => l.trim()).slice(-3);
                const stderrSnippet = stderrLines.join(' | ').substring(0, 150);
                errorDetail = `EXIT_CODE_${code}`;
                if (stderrSnippet) {
                    errorHint = `（stderr: ${stderrSnippet}）`;
                } else {
                    const outputSnippet = output.split('\n').filter(l => l.trim()).slice(-2).join(' | ').substring(0, 120);
                    errorHint = outputSnippet ? `（輸出: ${outputSnippet}）` : '（無額外診斷資訊）';
                }
            }

            updatePlayerStatus(player, 'offline');
            console.log(`[🐢 傑尼] ${playerLabel} 啟動失敗 (exit code: ${code}, 原因: ${errorDetail})`);

            if (retryCount < 2) {
                console.log(`[🐢 傑尼] 嘗試重試 (${retryCount + 2}/3)...`);
                zeniAlert(
                    `🔄 ${playerLabel} 連線嘗試中 (${retryCount + 2}/3)...\n錯誤: ${errorDetail} ${errorHint}\nexit code: ${code}｜模型: ${diagInfo.model}｜提供者: ${diagInfo.provider}`,
                    'info', []
                );
                setTimeout(() => {
                    spawnSubagentTask(task, player, timeoutMs, retryCount + 1)
                        .then(resolve)
                        .catch(reject);
                }, 3000 * (retryCount + 1));
            } else {
                zeniAlert(
                    `❌ ${playerLabel} 無法完成任務（重試 3 次均失敗）\n` +
                    `錯誤代碼: ${errorDetail}\n` +
                    `${errorHint}\n` +
                    `exit code: ${code}｜目標模型: ${modelToUse}｜實際模型: ${diagInfo.model}｜提供者: ${diagInfo.provider}｜執行器: ${diagInfo.runner}\n` +
                    `Gateway: ${GATEWAY_HOST}:${GATEWAY_PORT}`,
                    errorType,
                    ['manual', 'pause', 'stop', 'wait']
                );
                pausedPhaseBeforeZeni = game.phase;
                game.phase = PHASE.PAUSED_BY_ZENI;
                saveState();
                isProcessing = false;
                reject(new Error(`${playerLabel} 失敗: ${errorDetail} ${errorHint}`));
            }
        });

        proc.on('error', (err) => {
            console.log(`[🐢 傑尼] 程序錯誤: ${err.message} (code: ${err.code})`);
            updatePlayerStatus(player, 'offline');

            if (err.code === 'ENOENT') {
                zeniAlert(
                    `❌ 找不到 openclaw CLI 可執行檔！請確認已安裝 openclaw 並加入系統 PATH。\n執行 npm install -g openclaw 安裝後再試。`,
                    'connection',
                    ['manual', 'stop']
                );
                pausedPhaseBeforeZeni = game.phase;
                game.phase = PHASE.PAUSED_BY_ZENI;
                saveState();
                isProcessing = false;
            }

            reject(new Error(`CLI_ERROR: ${err.code || err.message}`));
        });
    });
}

// ============= Game Flow Functions =============

async function startDesignerAsking() {
    if (isProcessing || game.gameOver) return;
    isProcessing = true;

    console.log('[Game] ===== ROUND ' + game.round + ' =====');
    console.log('[Game] Phase: Designer (迪尼) Asking');

    // Phase 1: 迪尼構思題目
    game.phase = PHASE.DESIGNER_ASKING;
    game.questioner = 'designer';
    game.answerer = 'xiaxia';
    game.currentQuestion = null;
    game.currentAnswer = null;
    updatePlayerStatus('designer', 'asking');
    saveState();
    broadcastSSE();

    try {
        const task = `你是 🎨 迪尼，正在參加「推論猜謎對決」！

【遊戲規則】
- 你和 🦐 蝦蝦輪流出題給對方回答。
- 本回合由你出題，讓 🦐 蝦蝦 回答。
- 必須有一個唯一、明確且客觀的「標準答案」。禁止提出會產生模稜兩可答案的問題。

【出題範圍限制】
✅ 只能從以下三個領域選擇：
1. 數學運算
2. 物理科學
3. 中國文字文學

❌ 絕對禁止使用以下領域：
- 哲學
- 思想
- 假設性情境

格式要求（請嚴格遵守）：
【題目】
...（你的題目）
【標準答案】
...（答案）`;

        const result = await spawnSubagentTask(task, 'designer', 120000);

        // 從輸出中解析題目與標準答案
        const question = extractQuestion(result.output);
        const standardAnswer = extractStandardAnswer(result.output);

        if (question && standardAnswer) {
            game.currentQuestion = question;
            game.currentStandardAnswer = standardAnswer;
            saveState();
            broadcastSSE();

            console.log('[Game] Question from 迪尼: ' + question.substring(0, 50) + '...');
            console.log('[Game] Standard Answer from 迪尼 (Hidden): ' + standardAnswer);

            // 自動進入下一階段：蝦蝦回答
            await delay(2000);
            await startXiaxiaAnswering();
        } else {
            console.log('[Game] Failed to get question or standard answer from 迪尼');
            game.currentQuestion = '（迪尼未能完整出題或未提供標準答案）';
            saveState();
            broadcastSSE();
        }

    } catch (err) {
        console.log('[Game] Error: ' + err.message);
        // 自動失敗，切換到手動模式
        game.currentQuestion = '（系統自動功能失敗，請手動輸入題目）';
        game.manualMode = true;
        saveState();
        broadcastSSE();
    }

    isProcessing = false;
}

async function startXiaxiaAnswering() {
    if (game.gameOver) return;

    console.log('[Game] Phase: Xiaxia (蝦蝦) Answering');

    game.phase = PHASE.XIAXIA_ANSWERING;
    updatePlayerStatus('xiaxia', 'thinking');
    resetTimer(180); // 3 分鐘答題時間
    saveState();
    broadcastSSE();

    try {
        const task = `你是 🦐 蝦蝦，正在參加「推論猜謎對決」！

【當前題目】(由 🎨 迪尼 提問)
${game.currentQuestion}

請回答這個問題。
如果你知道答案就直接說，如果不知道就說「我不知道」。
不要拒絕回答。`;

        const result = await spawnSubagentTask(task, 'xiaxia', 180000);

        if (gameTimer) clearInterval(gameTimer);

        // 從輸出中解析答案
        const answer = extractAnswer(result.output);
        game.currentAnswer = answer;

        console.log('[Game] Answer from 蝦蝦: ' + answer.substring(0, 50) + '...');

        // 進入傑尼自動裁決階段
        game.phase = PHASE.JUDGE_PENDING;
        game.timeLeft = 0;
        updatePlayerStatus('xiaxia', 'waiting');
        saveState();
        broadcastSSE();

        console.log('[Game] Ready for judge decision! Auto judging...');
        await delay(2000);
        await startZeniJudging();

    } catch (err) {
        console.log('[Game] Error: ' + err.message);
        if (gameTimer) clearInterval(gameTimer);

        // 自動失敗，切換到手動模式
        game.currentAnswer = '（系統自動功能失敗，請手動輸入答案）';
        game.manualMode = true;
        game.phase = PHASE.JUDGE_PENDING;
        game.timeLeft = 0;
        updatePlayerStatus('xiaxia', 'waiting');
        saveState();
        broadcastSSE();
    }
}

async function startXiaxiaAsking() {
    if (isProcessing || game.gameOver) return;
    isProcessing = true;

    console.log('[Game] Phase: Xiaxia (蝦蝦) Asking');

    // Phase 3: 蝦蝦構思題目
    game.phase = PHASE.XIAXIA_ASKING;
    game.questioner = 'xiaxia';
    game.answerer = 'designer';
    game.currentQuestion = null;
    game.currentAnswer = null;
    updatePlayerStatus('xiaxia', 'asking');
    saveState();
    broadcastSSE();

    try {
        const task = `你是 🦐 蝦蝦，正在參加「推論猜謎對決」！

【遊戲規則】
- 你和 🎨 迪尼輪流出題給對方回答。
- 本回合由你出題，讓 🎨 迪尼 回答。
- 必須有一個唯一、明確且客觀的「標準答案」。禁止提出會產生模稜兩可答案的問題。

【出題範圍限制】
✅ 只能從以下三個領域選擇：
1. 數學運算
2. 物理科學
3. 中國文字文學

❌ 絕對禁止使用以下領域：
- 哲學
- 思想
- 假設性情境

格式要求（請嚴格遵守）：
【題目】
...（你的題目）
【標準答案】
...（答案）`;

        const result = await spawnSubagentTask(task, 'xiaxia', 180000);

        // 從輸出中解析題目與標準答案
        const question = extractQuestion(result.output);
        const standardAnswer = extractStandardAnswer(result.output);

        if (question && standardAnswer) {
            game.currentQuestion = question;
            game.currentStandardAnswer = standardAnswer;
            saveState();
            broadcastSSE();

            console.log('[Game] Question from 蝦蝦: ' + question.substring(0, 50) + '...');
            console.log('[Game] Standard Answer from 蝦蝦 (Hidden): ' + standardAnswer);

            // 自動進入下一階段：迪尼回答
            await delay(2000);
            await startDesignerAnswering();
        } else {
            console.log('[Game] Failed to get question or standard answer from 蝦蝦');
            game.currentQuestion = '（蝦蝦未能完整出題或未提供標準答案）';
            saveState();
            broadcastSSE();
        }

    } catch (err) {
        console.log('[Game] Error: ' + err.message);
        // 自動失敗，切換到手動模式
        game.currentQuestion = '（系統自動功能失敗，請手動輸入題目）';
        game.manualMode = true;
        saveState();
        broadcastSSE();
    }

    isProcessing = false;
}

async function startDesignerAnswering() {
    if (game.gameOver) return;

    console.log('[Game] Phase: Designer (迪尼) Answering');

    game.phase = PHASE.DESIGNER_ANSWERING;
    updatePlayerStatus('designer', 'thinking');
    resetTimer(180); // 3 分鐘答題時間
    saveState();
    broadcastSSE();

    try {
        const task = `你是 🎨 迪尼，正在參加「推論猜謎對決」！

【當前題目】(由 🦐 蝦蝦 提問)
${game.currentQuestion}

請回答這個問題。
如果你知道答案就直接說，如果不知道就說「我不知道」。
不要拒絕回答。`;

        const result = await spawnSubagentTask(task, 'designer', 300000);

        if (gameTimer) clearInterval(gameTimer);

        // 從輸出中解析答案
        const answer = extractAnswer(result.output);
        game.currentAnswer = answer;

        console.log('[Game] Answer from 迪尼: ' + answer.substring(0, 50) + '...');

        // 進入傑尼自動裁決階段
        game.phase = PHASE.JUDGE_PENDING;
        game.timeLeft = 0;
        updatePlayerStatus('designer', 'waiting');
        saveState();
        broadcastSSE();

        console.log('[Game] Ready for judge decision! Auto judging...');
        await delay(2000);
        await startZeniJudging();

    } catch (err) {
        console.log('[Game] Error: ' + err.message);
        if (gameTimer) clearInterval(gameTimer);

        // 自動失敗，切換到手動模式
        game.currentAnswer = '（系統自動功能失敗，請手動輸入答案）';
        game.manualMode = true;
        game.phase = PHASE.JUDGE_PENDING;
        game.timeLeft = 0;
        updatePlayerStatus('designer', 'waiting');
        saveState();
        broadcastSSE();
    }

    isProcessing = false;
}

async function startZeniJudging() {
    if (game.gameOver) return;

    console.log('[Game] Phase: Zeni (傑尼) Judging');

    const task = `你是裁判 🐢 傑尼。
請判斷玩家的回答是否正確。

【題目】
${game.currentQuestion}

【標準答案】
${game.currentStandardAnswer}

【玩家回答】
${game.currentAnswer}

請比對「玩家回答」與「標準答案」的核心概念是否一致。
如果意思相符，請只輸出「正確」。
如果意思不符或答非所問，請只輸出「錯誤」。
不要輸出任何其他解釋。`;

    try {
        const result = await spawnSubagentTask(task, 'zeni', 300000);
        const output = result.output.trim();

        let isCorrect = output.includes('正確') && !output.includes('錯誤');
        if (!isCorrect && output.includes('錯誤')) {
            isCorrect = false;
        } else if (output.includes('正確')) {
            isCorrect = true; // Fallback
        } else {
            // 如果傑尼亂回，嘗試模糊比對
            isCorrect = game.currentAnswer.includes(game.currentStandardAnswer) || game.currentStandardAnswer.includes(game.currentAnswer);
            console.log(`[Game] Zeni response ambiguous ("${output}"), fallback fuzzy match: ${isCorrect}`);
        }

        const answerer = game.answerer;
        const questioner = game.questioner;
        let resultLabel, pointsTo;

        if (isCorrect) {
            game.scores[answerer]++;
            resultLabel = 'correct';
            pointsTo = answerer;
        } else {
            game.scores[questioner]++;
            resultLabel = 'wrong';
            pointsTo = questioner;
        }

        // Record in history (including standard answer)
        game.history.push({
            round: game.round,
            questioner: questioner,
            answerer: answerer,
            question: game.currentQuestion,
            answer: game.currentAnswer,
            standardAnswer: game.currentStandardAnswer,
            result: resultLabel,
            pointsTo: pointsTo
        });

        console.log(`[Game] Judge decision: ${resultLabel}! Point to ${PLAYERS[pointsTo].emoji} ${PLAYERS[pointsTo].name}`);
        console.log(`[Game] Score: 迪尼 ${game.scores.designer} - ${game.scores.xiaxia} 蝦蝦`);

        saveState();
        broadcastSSE();

        // 進入下一個回合
        await delay(5000); // 讓前端觀眾看一下結果

        // 這裡不要用 await，使用 setTimeout 讓當前回合的堆疊徹底結束並釋放 isProcessing 鎖定
        setTimeout(startNextRound, 1000);

    } catch (err) {
        console.log('[Game] Error in Zeni judging: ' + err.message);
        // 如果傑尼掛了，交給手動模式或者自動算錯
        game.phase = PHASE.PAUSED_BY_ZENI;
        zeniAlert('❌ 傑尼裁決時發生錯誤，請以手動模式繼續。', 'error', ['manual', 'stop']);
        saveState();
        broadcastSSE();
    }
}

async function startNextRound() {
    if (game.gameOver) return;

    // Check if game over (10 rounds complete)
    if (game.round >= game.maxRounds) {
        game.gameOver = true;
        game.phase = PHASE.GAME_OVER;
        console.log('[Game] ===== GAME OVER =====');
        console.log(`[Game] Final Score: 迪尼 ${game.scores.designer} - ${game.scores.xiaxia} 蝦蝦`);
        saveState();
        broadcastSSE();
        return;
    }

    // Update round
    game.round++;

    // Reset for next round
    game.currentQuestion = null;
    game.currentAnswer = null;
    game.currentStandardAnswer = null;
    game.questioner = null;
    game.answerer = null;

    console.log(`[Game] ===== ROUND ${game.round} =====`);

    // Alternating turns logic
    // 單數回合 (1, 3, 5, 7, 9): Designer asks, Xiaxia answers
    // 雙數回合 (2, 4, 6, 8, 10): Xiaxia asks, Designer answers
    if (game.round % 2 !== 0) {
        await startDesignerAsking();
    } else {
        await startXiaxiaAsking();
    }
}

// ============= Utility Functions =============

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function extractQuestion(output) {
    // Try to extract question between 【題目】 and 【答案】
    const patterns = [
        /【題目】\s*\n?(.+?)(?=【答案】|$)/is,
        /題目[:：]\s*\n?(.+?)(?=答案[:：]|$)/is,
        /Q[:：]\s*\n?(.+?)(?=A[:：]|$)/is
    ];

    for (const pattern of patterns) {
        const match = output.match(pattern);
        if (match && match[1]) {
            let q = match[1].trim();
            // Remove the answer part if it's there
            q = q.replace(/【答案】.*$/is, '').trim();
            if (q.length > 5) return q;
        }
    }

    // Fallback: return last substantial text block
    const lines = output.split('\n')
        .filter(l => l.trim().length > 10)
        .slice(-5);
    return lines.join('\n').trim() || null;
}

function extractStandardAnswer(output) {
    // Try to extract standard answer
    const patterns = [
        /【標準答案】\s*\n?(.+?)$/is,
        /標準答案[:：]\s*\n?(.+?)$/is,
        /【答案】\s*\n?(.+?)$/is
    ];

    for (const pattern of patterns) {
        const match = output.match(pattern);
        if (match && match[1]) {
            return match[1].trim();
        }
    }

    // Fallback: return last line
    const lines = output.split('\n').filter(l => l.trim());
    return lines[lines.length - 1]?.trim() || '（無法解析標準答案）';
}

function extractAnswer(output) {
    // 答題者直接回覆內容，無需特殊標籤，取最後一段或全部
    const patterns = [
        /【答案】\s*\n?(.+?)$/is,
        /答案[:：]\s*\n?(.+?)$/is,
        /A[:：]\s*\n?(.+?)$/is
    ];

    for (const pattern of patterns) {
        const match = output.match(pattern);
        if (match && match[1]) {
            return match[1].trim();
        }
    }

    // Fallback: 如果沒有標籤，直接當作全文就是答案
    return output.trim() || '（無法解析）';
}

// ============= API Routes =============

// SSE endpoint for real-time updates
app.get('/api/stream', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    // Send current state immediately
    res.write(`data: ${JSON.stringify({ game, timeLeft: game.timeLeft })}\n\n`);

    clients.push(res);
    req.on('close', () => {
        clients = clients.filter(c => c !== res);
    });
});

// Get current game state
app.get('/api/state', (req, res) => {
    res.json({ game, timeLeft: game.timeLeft });
});

// Initialize/reset game
app.post('/api/init', (req, res) => {
    if (gameTimer) clearInterval(gameTimer);
    if (retryTimer) clearInterval(retryTimer);

    game = {
        round: 1,
        maxRounds: 10,
        phase: PHASE.IDLE,
        scores: { designer: 0, xiaxia: 0 },
        players: {
            designer: { status: 'waiting', lastSeen: new Date().toISOString() },
            xiaxia: { status: 'waiting', lastSeen: new Date().toISOString() }
        },
        currentQuestion: null,
        currentAnswer: null,
        questioner: null,
        answerer: null,
        questions: [],
        timeLeft: 0,
        gameOver: false,
        lastUpdated: new Date().toISOString(),
        history: [],
        manualMode: false,
        // 傑尼監控系統初始化
        zeniMessage: null,
        zeniActions: [],
        zeniLog: [],
        connectionStatus: {
            mode: 'cloud',
            model: MODEL_CONFIG.cloud,
            lastError: null,
            rateLimitAt: null,
            retryIn: null
        }
    };

    zeniAlert('🐢 傑尼主控系統就緒！等待開始遊戲...', 'info', []);
    saveState();
    broadcastSSE();
    res.json({ status: 'ok', game });
});

// Start game - begins with 迪尼 asking
app.post('/api/start', async (req, res) => {
    if (game.gameOver) {
        return res.json({ error: 'Game is over. Please reset first.' });
    }
    if (game.phase !== PHASE.IDLE) {
        return res.json({ error: 'Game already in progress' });
    }

    console.log('[Game] ===== GAME START =====');

    res.json({ status: 'ok', message: 'Game started! 迪尼 準備構思題目...' });

    // Start the game flow
    await startDesignerAsking();
});

// Next turn API (Reserved for manual override if needed)
app.post('/api/next-turn', async (req, res) => {
    if (game.gameOver) return res.json({ error: 'Game is over' });
    res.json({ status: 'ok', message: 'Skipping to next round...' });
    await startNextRound();
});

// Judge decision
app.post('/api/judge', (req, res) => {
    const { correct, answererCorrect } = req.body;

    if (game.phase !== PHASE.JUDGE_PENDING) {
        return res.json({ error: 'Not in judging phase' });
    }

    // The answerer gets the point if correct
    // questioner gets the point if answerer is wrong (timeout or wrong answer)
    const answerer = game.answerer;
    const questioner = game.questioner;

    let result, pointsTo;

    if (answererCorrect === true) {
        // 答對了 - answerer 得分
        game.scores[answerer]++;
        result = 'correct';
        pointsTo = answerer;
    } else {
        // 答錯了或超時 - questioner 得分
        game.scores[questioner]++;
        result = 'wrong';
        pointsTo = questioner;
    }

    // Record in history
    game.history.push({
        round: game.round,
        questioner: questioner,
        answerer: answerer,
        question: game.currentQuestion,
        answer: game.currentAnswer,
        result: result,
        pointsTo: pointsTo
    });

    console.log(`[Game] Judge decision: ${result}! Point to ${PLAYERS[pointsTo].emoji} ${PLAYERS[pointsTo].name}`);
    console.log(`[Game] Score: 迪尼 ${game.scores.designer} - ${game.scores.xiaxia} 蝦蝦`);

    // Check if this was the last question of round 10
    if (game.round >= game.maxRounds && game.history.length >= game.maxRounds) {
        game.gameOver = true;
        game.phase = PHASE.GAME_OVER;
        console.log('[Game] ===== GAME OVER =====');
        console.log(`[Game] Final Score: 迪尼 ${game.scores.designer} - ${game.scores.xiaxia} 蝦蝦`);
    }

    saveState();
    broadcastSSE();

    res.json({
        status: 'ok',
        result,
        pointsTo,
        scores: game.scores,
        gameOver: game.gameOver
    });
});

// Manual judge (羅哥 decides if correct or not)
app.post('/api/judge-answer', (req, res) => {
    const { correct } = req.body;

    if (game.phase !== PHASE.JUDGE_PENDING) {
        return res.json({ error: 'Not in judging phase' });
    }

    // correct=true means answerer got it right
    // correct=false means answerer got it wrong
    return res.json({
        status: 'ok',
        message: correct ? '答對了！' : '答錯了！',
        ready: true
    });
});

// Get player info
app.get('/api/players', (req, res) => {
    res.json({
        players: PLAYERS,
        status: game.players
    });
});

// 手動模式：提交題目
app.post('/api/manual-question', (req, res) => {
    const { question } = req.body;
    if (typeof question !== 'string' || question.trim() === '') {
        return res.status(400).json({ error: 'missing or empty question' });
    }
    game.currentQuestion = question.trim();
    game.manualMode = false;
    // 若目前處於傑尼暫停狀態，恢復至候裁決階段
    if (game.phase === PHASE.PAUSED_BY_ZENI) {
        game.phase = PHASE.JUDGE_PENDING;
        game.zeniMessage = null;
        game.zeniActions = [];
        pausedPhaseBeforeZeni = null;
    }
    saveState();
    broadcastSSE();
    res.json({ status: 'ok', message: '題目已提交' });
});

// 手動模式：提交答案
app.post('/api/manual-answer', (req, res) => {
    const { answer } = req.body;
    if (typeof answer !== 'string' || answer.trim() === '') {
        return res.status(400).json({ error: 'missing or empty answer' });
    }
    game.currentAnswer = answer.trim();
    game.phase = PHASE.JUDGE_PENDING;
    game.manualMode = false;
    game.timeLeft = 0;
    game.zeniMessage = null;
    game.zeniActions = [];
    pausedPhaseBeforeZeni = null;
    saveState();
    broadcastSSE();
    res.json({ status: 'ok', message: '答案已提交' });
});

// ============= 傑尼決策端點 =============

/**
 * POST /api/zeni-action
 * 用戶對傑尼的警告做出回應
 * action: 'manual' | 'pause' | 'stop' | 'wait' | 'switch_cloud'
 */
app.post('/api/zeni-action', async (req, res) => {
    const { action } = req.body;

    console.log(`[🐢 傑尼] 收到用戶指令: ${action}`);

    switch (action) {
        case 'manual':
            // 進入手動模式：用戶自行輸入題目或答案
            game.manualMode = true;
            game.phase = pausedPhaseBeforeZeni || PHASE.JUDGE_PENDING;
            game.zeniMessage = null;
            game.zeniActions = [];
            pausedPhaseBeforeZeni = null;
            isProcessing = false;
            zeniAlert('📝 已進入手動模式。請你直接輸入下方的題目或答案。', 'info', []);
            saveState();
            broadcastSSE();
            return res.json({ status: 'ok', mode: 'manual' });

        case 'pause':
            // 暫停：保持目前狀態，等待用戶下一步指令
            game.phase = PHASE.PAUSED_BY_ZENI;
            game.zeniMessage = {
                time: new Date().toISOString(),
                message: '⏸️ 遊戲已暫停。隨時可以選擇繼續、手動模式或停止。',
                errorType: 'info',
                actions: ['manual', 'stop', 'wait']
            };
            game.zeniActions = ['manual', 'stop', 'wait'];
            isProcessing = false;
            if (retryTimer) { clearInterval(retryTimer); retryTimer = null; }
            saveState();
            broadcastSSE();
            return res.json({ status: 'ok', mode: 'paused' });

        case 'stop':
            // 強制結束比賽
            if (gameTimer) clearInterval(gameTimer);
            if (retryTimer) clearInterval(retryTimer);
            game.gameOver = true;
            game.phase = PHASE.GAME_OVER;
            game.zeniMessage = null;
            game.zeniActions = [];
            isProcessing = false;
            zeniAlert(`🛑 傑尼宣佈比賽提前結束！最終比分：🎨 迪尼 ${game.scores.designer} vs 🦐 蝦蝦 ${game.scores.xiaxia}`, 'info', []);
            saveState();
            broadcastSSE();
            return res.json({ status: 'ok', mode: 'stopped', scores: game.scores });

        case 'wait':
            // 等待：傑尼計時 60 秒後自動重試
            game.phase = PHASE.PAUSED_BY_ZENI;
            const savedPhase = pausedPhaseBeforeZeni;
            zeniAlert(`⏳ 傑尼開始等待 60 秒後自動重試連線...`, 'info', ['stop']);
            saveState();
            broadcastSSE();

            startRetryCountdown(60, async () => {
                // 重試：恢復到暫停前的狀態並繼續
                if (game.gameOver) return;
                game.phase = savedPhase || PHASE.IDLE;
                pausedPhaseBeforeZeni = null;
                game.zeniMessage = null;
                game.zeniActions = [];
                saveState();
                broadcastSSE();

                // 根據恢復的狀態繼續遊戲
                if (savedPhase === PHASE.DESIGNER_ASKING) {
                    await startDesignerAsking();
                } else if (savedPhase === PHASE.XIAXIA_ASKING) {
                    await startXiaxiaAsking();
                } else if (savedPhase === PHASE.XIAXIA_ANSWERING) {
                    await startXiaxiaAnswering();
                } else if (savedPhase === PHASE.DESIGNER_ANSWERING) {
                    await startDesignerAnswering();
                }
            });

            return res.json({ status: 'ok', mode: 'waiting', retryIn: 60 });

        case 'switch_cloud':
            // 手動切換回雲端模型
            updateConnectionStatus('cloud');
            game.zeniMessage = null;
            game.zeniActions = [];
            zeniAlert(`☁️ 已切換回雲端模型 (${MODEL_CONFIG.cloud})。如果仍然受限，傑尼會自動切回本地模型。`, 'info', []);
            saveState();
            broadcastSSE();
            return res.json({ status: 'ok', model: MODEL_CONFIG.cloud });

        default:
            return res.status(400).json({ error: '未知指令: ' + action });
    }
});

/**
 * GET /api/connection-status
 * 取得目前連線狀態
 */
app.get('/api/connection-status', (req, res) => {
    res.json({
        connectionMode,
        activeModel,
        rateLimitHitAt,
        availableModels: MODEL_CONFIG
    });
});

// ============= Start Server =============

const server = app.listen(PORT, () => {
    console.log('========================================');
    console.log('   🐢 推論猜謎對決 - 遊戲引擎 v4.0');
    console.log('========================================');
    console.log(`✅ 伺服器已啟動：http://localhost:${PORT}`);
    console.log(`📍 網頁界面：http://localhost:${PORT}/public/index.html`);
    console.log();
    console.log('👥 參賽選手：');
    console.log('   🎨 迪尼 (Designer)');
    console.log('   🦐 蝦蝦 (Xiaxia)');
    console.log('   🐢 傑尼 (Zeni - 主控代理人/裁判)');
    console.log();
    console.log('🔗 模型設定：');
    console.log(`   首選 (Cloud): ${MODEL_CONFIG.cloud}`);
    console.log(`   備援 (Local): ${MODEL_CONFIG.local}`);
    console.log();
    console.log('API 端點：');
    console.log('  GET  /api/state             - 遊戲狀態');
    console.log('  GET  /api/stream            - SSE 即時串流');
    console.log('  GET  /api/players           - 選手狀態');
    console.log('  GET  /api/connection-status - 連線狀態');
    console.log('  POST /api/init              - 初始化/重置遊戲');
    console.log('  POST /api/start             - 開始遊戲');
    console.log('  POST /api/judge             - 裁決');
    console.log('  POST /api/next-turn         - 下一回合');
    console.log('  POST /api/zeni-action       - 傑尼決策指令');
    console.log('  POST /api/manual-question   - 手動輸入題目');
    console.log('  POST /api/manual-answer     - 手動輸入答案');
    console.log('========================================');
});

// Initialize state after server starts
saveState();
autoDetectGateway().then(success => {
    if (success) {
        zeniAlert(`🐢 傑尼主控系統就緒！已成功連線至 Gateway (${GATEWAY_HOST})。`, 'info', []);
    } else {
        zeniAlert(`🔴 警告：傑尼找不到 Gateway 服務！請檢查網路或 OpenClaw 伺服器。`, 'connection', ['wait']);
    }
});
console.log('[🐢 傑尼] 引擎 v4.0 初始化完成');