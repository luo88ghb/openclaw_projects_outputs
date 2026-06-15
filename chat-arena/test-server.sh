#!/bin/bash
cd /workspace/chat-arena
node game-server.js &
sleep 3
curl -s http://localhost:3001/api/state
pkill -f "node game-server" 2>/dev/null