const http = require("http");
const net = require("net");

console.log("Testing port 3000 availability...");

// Test if port is available
const testSocket = new net.Socket();
testSocket.setTimeout(1000);

testSocket.on("connect", () => {
  console.log("Port 3000 is already in use");
  testSocket.destroy();
});

testSocket.on("timeout", () => {
  console.log("Port 3000 timeout - likely available");
  testSocket.destroy();
  startServer();
});

testSocket.on("error", (err) => {
  console.log("Port 3000 error:", err.code);
  if (err.code === "ECONNREFUSED") {
    console.log("Port 3000 is available");
    startServer();
  }
});

testSocket.connect(3000, "127.0.0.1");

function startServer() {
  const server = http.createServer((req, res) => {
    res.writeHead(200, { "Content-Type": "text/plain" });
    res.end("Debug server working\n");
  });

  server.on("listening", () => {
    const address = server.address();
    console.log("Server is listening on:", address);
  });

  server.on("error", (err) => {
    console.log("Server error:", err);
  });

  server.listen(3000, "127.0.0.1", () => {
    console.log("Server started on 127.0.0.1:3000");
  });
}
