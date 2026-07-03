/**
 * Analytics Service - Minimal Stub
 * TODO: Implement actual service logic
 */

import 'dotenv/config';
import http from 'http';

const PORT = process.env.PORT || 3004;

export const server = http.createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', service: 'analytics' }));
    return;
  }

  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(
    JSON.stringify({
      message: 'Analytics Service - Coming Soon',
      endpoints: {
        health: '/health',
      },
    })
  );
});

if (process.env.NODE_ENV !== 'test') {
  server.listen(PORT, () => {
    console.log(`✅ Analytics Service running on port ${PORT}`);
  });
}
