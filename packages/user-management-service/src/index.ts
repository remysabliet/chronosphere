/**
 * User Management Service - Minimal Stub
 * TODO: Implement actual service logic
 */

import http from 'http';

const PORT = process.env.PORT || 3001;

const server = http.createServer((req, res) => {
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

server.listen(PORT, () => {
  console.log(`✅ User Management Service running on port ${PORT}`);
});
