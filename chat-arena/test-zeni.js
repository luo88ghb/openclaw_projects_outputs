const { spawn } = require('child_process');
const path = require('path');

const task = `你是裁判 🐢 傑尼。
請判斷玩家的回答是否正確。

【題目】
1+1=?

【標準答案】
2

【玩家回答】
2

請比對「玩家回答」與「標準答案」的核心概念是否一致。
如果意思相符，請只輸出「正確」。
如果意思不符或答非所問，請只輸出「錯誤」。
不要輸出任何其他解釋。`;

const modelToUse = 'openrouter/auto,ollama/qwen359b:latest';
const sessionId = 'test-zeni-' + Date.now();

const args = [
    'agent',
    '--message', task,
    '--session-id', sessionId,
    '--json',
    '--timeout', '60'
];

const nodeExe = process.execPath;
const openclawEntry = path.join(
    process.env.APPDATA || '', 'npm', 'node_modules', 'openclaw', 'dist', 'index.js'
);

console.log('Running test with args:', args);

const proc = spawn(nodeExe, [openclawEntry, ...args], {
    cwd: process.cwd(),
    timeout: 90000,
    env: {
        ...process.env,
        OPENCLAW_MODEL: modelToUse
    }
});

let output = '';
let stderr = '';

proc.stdout.on('data', (d) => { output += d.toString(); });
proc.stderr.on('data', (d) => { stderr += d.toString(); });

proc.on('close', (code) => {
    console.log('Code:', code);
    console.log('Stdout:', output);
    console.log('Stderr:', stderr);
});
