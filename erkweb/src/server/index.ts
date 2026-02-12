import {createServer} from 'http';

import express from 'express';
import {WebSocketServer} from 'ws';

import plansRouter from './routes/plans.js';
import {handleChatConnection} from './ws/chat.js';

const app = express();
const server = createServer(app);
const wss = new WebSocketServer({server, path: '/ws/chat'});

app.use(express.json());
app.use('/api', plansRouter);

wss.on('connection', (ws) => {
  handleChatConnection(ws);
});

const PORT = parseInt(process.env.ERKWEB_PORT || '3001', 10);
server.listen(PORT, () => {
  console.log(`erkweb server listening on http://localhost:${PORT}`);
});
