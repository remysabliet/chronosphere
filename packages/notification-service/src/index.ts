/**
 * Notification Service - Minimal Stub
 * TODO: Implement actual service logic
 */

import http from 'http';

const PORT = process.env.PORT || 3005;

const server = http.createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', service: 'notification' }));
    return;
  }

  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    message: 'Notification Service - Coming Soon',
    endpoints: {
      health: '/health'
    }
  }));
});

server.listen(PORT, () => {
  console.log(`✅ Notification Service running on port ${PORT}`);
});
