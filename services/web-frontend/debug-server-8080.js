const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello from port 8080\n');
});

server.listen(8080, '127.0.0.1', () => {
  console.log('Server running on http://127.0.0.1:8080');
});

setTimeout(() => {
  console.log('Closing server...');
  server.close();
}, 30000);