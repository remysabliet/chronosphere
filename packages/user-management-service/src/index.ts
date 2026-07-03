/**
 * User Management Service - Minimal Stub
 * TODO: Implement actual service logic
 */

import 'dotenv/config';
import http from 'http';

const PORT = process.env.PORT || 3001;

export const server = http.createServer((req, res) => {
  // Health check endpoint
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', service: 'user-management' }));
    return;
  }

  // Default response
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(
    JSON.stringify({
      message: 'User Management Service - Coming Soon',
      endpoints: {
        health: '/health',
      },
    })
  );
});

if (process.env.NODE_ENV !== 'test') {
  server.listen(PORT, () => {
    console.log(`✅ Service running on port ${PORT}`);
  });
}
