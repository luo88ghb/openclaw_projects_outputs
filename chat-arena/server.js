// 討論聊天室伺服器
// 使用方式: node server.js

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3001;
const GAME_STATE_FILE = path.join(__dirname, 'game-state.json');
const HTML_FILE = path.join(__dirname, 'index.html');

// 初始化遊戲狀態
function initGame() {
    return {
        round: 1,
        maxRounds: 5,
        currentQuestioner: 'zeni',
        zeniScore: 0,
        designerScore: 0,
        questions: [],
        gameOver: false,
        lastUpdated: new Date().toISOString()
    };
}

// 載入遊戲狀態
function loadState() {
    try {
        if (fs.existsSync(GAME_STATE_FILE)) {
            return JSON.parse(fs.readFileSync(GAME_STATE_FILE, 'utf8'));
        }
    } catch (e) {}
    return initGame();
}

// 保存遊戲狀態
function saveState(state) {
    fs.writeFileSync(GAME_STATE_FILE, JSON.stringify(state, null, 2));
}

// 建立 HTTP 伺服器
const server = http.createServer((req, res) => {
    // CORS 標頭
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }
    
    // 路由處理
    if (req.url === '/' || req.url === '/index.html') {
        // 提供 HTML 頁面
        fs.readFile(HTML_FILE, 'utf8', (err, data) => {
            if (err) {
                res.writeHead(500);
                res.end('Error loading page');
                return;
            }
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(data);
        });
    } else if (req.url === '/api/state') {
        // 獲取遊戲狀態
        const state = loadState();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(state));
    } else if (req.url === '/api/init' && req.method === 'POST') {
        // 初始化遊戲
        const state = initGame();
        saveState(state);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(state));
    } else if (req.url.startsWith('/api/add') && req.method === 'POST') {
        // 添加題目
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            try {
                const { questioner, question, answerer, answer, correct, correctAnswer } = JSON.parse(body);
                const state = loadState();
                
                state.questions.push({
                    round: state.round,
                    questioner,
                    question,
                    answerer,
                    answer,
                    correct,
                    correctAnswer
                });
                
                if (correct) {
                    if (answerer === 'zeni') state.zeniScore++;
                    else if (answerer === 'designer') state.designerScore++;
                }
                
                state.round++;
                state.currentQuestioner = state.currentQuestioner === 'zeni' ? 'designer' : 'zeni';
                state.lastUpdated = new Date().toISOString();
                
                saveState(state);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(state));
            } catch (e) {
                res.writeHead(400);
                res.end(JSON.stringify({ error: e.message }));
            }
        });
    } else if (req.url === '/api/end' && req.method === 'POST') {
        // 結束遊戲
        const state = loadState();
        state.gameOver = true;
        state.lastUpdated = new Date().toISOString();
        saveState(state);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(state));
    } else if (req.url === '/api/reset' && req.method === 'POST') {
        // 重置遊戲
        const state = initGame();
        saveState(state);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(state));
    } else {
        res.writeHead(404);
        res.end('Not found');
    }
});

server.listen(PORT, () => {
    console.log(`
🐢 vs 🎨 推論猜謎對決 - 討論聊天室伺服器

✅ 伺服器已啟動！
📍 訪問地址：http://localhost:${PORT}

API 端點：
  GET  /api/state    - 獲取遊戲狀態
  POST /api/init     - 初始化遊戲
  POST /api/add      - 添加題目
  POST /api/end      - 結束遊戲
  POST /api/reset    - 重置遊戲
`);
});