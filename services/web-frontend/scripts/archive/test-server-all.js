const http = require("http");

const server = http.createServer((req, res) => {
  res.writeHead(200, { "Content-Type": "text/plain" });
  res.end("Test server working on 0.0.0.0\n");
});

server.listen(3000, "0.0.0.0", () => {
  console.log("Test server running on http://0.0.0.0:3000");
});

server.on("error", (err) => {
  console.log("Server error:", err);
});
