const http = require('http');
const net = require('net');

console.log('Node.js version:', process.version);
console.log('Platform:', process.platform);

// Test if we can bind to port 3000
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello from simple server\n');
});

server.on('error', (err) => {
  console.error('Server error:', err);
});

server.on('listening', () => {
  const addr = server.address();
  console.log('Server successfully bound to:', addr);
});

console.log('Attempting to listen on port 3000...');
server.listen(3000, '127.0.0.1', () => {
  console.log('Simple server running on http://127.0.0.1:3000');
});

// Keep the server running for 30 seconds
setTimeout(() => {
  console.log('Closing server...');
  server.close();
}, 30000);