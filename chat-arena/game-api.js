// 遊戲 API - 用於更新聊天室
// 這個腳本由工作人員（主持人）使用，來記錄遊戲進展

const GAME_STATE_FILE = '/workspace/chat-arena/game-state.json';

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

// 添加題目
function addQuestion(questioner, question, answerer, answer, correct, correctAnswer) {
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
    return state;
}

// 結束遊戲
function endGame() {
    const state = loadState();
    state.gameOver = true;
    state.lastUpdated = new Date().toISOString();
    saveState(state);
    return state;
}

// 載入狀態
function loadState() {
    try {
        const fs = require('fs');
        if (fs.existsSync(GAME_STATE_FILE)) {
            return JSON.parse(fs.readFileSync(GAME_STATE_FILE, 'utf8'));
        }
    } catch (e) {}
    return initGame();
}

// 保存狀態
function saveState(state) {
    try {
        const fs = require('fs');
        fs.writeFileSync(GAME_STATE_FILE, JSON.stringify(state, null, 2));
    } catch (e) {
        console.error('Failed to save state:', e);
    }
}

// 命令行介面
const args = process.argv.slice(2);
if (args.length === 0) {
    console.log(`
🎮 推論猜謎遊戲 API

用法:
    node game-api.js init                      # 初始化遊戲
    node game-api.js add "題目" "答案"         # 添加題目（需手動編輯）
    node game-api.js score                    # 查看當前分數
    node game-api.js end                      # 結束遊戲
    node game-api.js status                   # 查看遊戲狀態
    `);
} else {
    const cmd = args[0];
    const state = loadState();
    
    switch(cmd) {
        case 'init':
            const newState = initGame();
            saveState(newState);
            console.log('✅ 遊戲已初始化！');
            console.log(JSON.stringify(newState, null, 2));
            break;
        case 'score':
            console.log(`📊 當前分數：🐢 傑尼 ${state.zeniScore} vs 🎨 迪尼 ${state.designerScore}`);
            break;
        case 'status':
            console.log(JSON.stringify(state, null, 2));
            break;
        case 'end':
            endGame();
            console.log('🏆 遊戲已結束！');
            console.log(`最終比分：🐢 ${state.zeniScore} vs 🎨 ${state.designerScore}`);
            break;
        default:
            console.log('未知命令');
    }
}