const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3000;
const PROJECT_DIR = __dirname; // Force using __dirname directly

const CONFIG_PATH = path.join(PROJECT_DIR, 'arena_config.json');
const SCOREBOARD_PATH = path.join(PROJECT_DIR, 'visual_scoreboard.json');
const LOG_PATH = path.join(PROJECT_DIR, 'server.log');

function readJSON(filePath) {
    try {
        if (!fs.existsSync(filePath)) {
            console.log(`[WARN] File does not exist: ${filePath}`);
            return null;
        }
        const content = fs.readFileSync(filePath, 'utf8');
        const parsed = JSON.parse(content);
        console.log(`[OK] JSON parsed from: ${filePath}`);
        return parsed;
    } catch (e) {
        console.log(`[ERROR] readJSON failed for ${filePath}: ${e.message}`);
        return null;
    }
}

function writeJSON(filePath, data) {
    try {
        fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
        console.log(`[OK] Written to: ${filePath}`);
        return true;
    } catch (e) {
        console.log(`[ERROR] writeJSON failed: ${e.message}`);
        return false;
    }
}

function appendLog(message) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] ${message}`;
    fs.appendFileSync(LOG_PATH, logEntry + '\n', 'utf8');
    console.log(logEntry);
}

let gameState = {
    currentRound: 0,
    currentQuestionIndex: 0,
    currentPlayerId: null,
    status: 'IDLE',
    roundData: []
};

const server = http.createServer((req, res) => {
    const url = req.url;
    const method = req.method;

    console.log(`[REQUEST] ${method} ${url}`);

    if (url === '/api/ping') {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        return res.end(JSON.stringify({ 
            status: 'ok', 
            timestamp: new Date().toISOString(),
            __dirname: PROJECT_DIR
        }));
    }

    if (url === '/api/scoreboard') {
        console.log('[DEBUG] Handling /api/scoreboard');
        let data = readJSON(SCOREBOARD_PATH);
        console.log(`[DEBUG] readJSON result: ${JSON.stringify(data)}`);
        
        if (!data) {
            console.log('[DEBUG] data was null, initializing default');
            data = { rounds: [], cumulative: { dini: 0, xixia: 0 } };
            writeJSON(SCOREBOARD_PATH, data);
        }
        
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        return res.end(JSON.stringify(data));
    }

    if (url === '/api/log') {
        if (fs.existsSync(LOG_PATH)) {
            const log = fs.readFileSync(LOG_PATH, 'utf8');
            res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
            return res.end(log);
        }
        res.writeHead(404);
        return res.end('Log not found');
    }

    if (method === 'POST' && url === '/api/game/start') {
        gameState.currentRound = 1;
        gameState.status = 'WAITING_FOR_PLAYER';
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        return res.end(JSON.stringify({ status: 'started' }));
    }

    // Static file serving
    let filePath;
    if (url === '/' || url === '') {
        filePath = path.join(PROJECT_DIR, 'viewer.html');
    } else {
        filePath = path.join(PROJECT_DIR, url);
    }

    console.log(`[DEBUG] Serving: ${filePath}`);

    fs.readFile(filePath, (err, content) => {
        if (err) {
            console.log(`[ERROR] File read failed: ${filePath}`);
            res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
            return res.end('Not found');
        }
        const ext = path.extname(filePath).toLowerCase();
        const mime = {
            '.html': 'text/html; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.json': 'application/json; charset=utf-8',
            '.txt': 'text/plain; charset=utf-8'
        }[ext] || 'application/octet-stream';
        res.writeHead(200, { 'Content-Type': mime });
        res.end(content);
    });
});

server.on('error', (err) => {
    console.error(`[SERVER ERROR] ${err.message}`);
});

server.listen(PORT, () => {
    console.log('========================================');
    console.log(`Server STARTED at http://localhost:${PORT}`);
    console.log(`PROJECT_DIR: ${PROJECT_DIR}`);
    console.log(`CONFIG: ${CONFIG_PATH}`);
    console.log(`SCOREBOARD: ${SCOREBOARD_PATH}`);
    console.log(`LOG: ${LOG_PATH}`);
    console.log('========================================');
});

process.on('uncaughtException', (err) => {
    console.error(`[UNCAUGHT] ${err.message}`);
});