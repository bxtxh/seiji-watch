// Health check endpoint for container monitoring
export default function handler(req, res) {
  res.status(200).json({
    status: 'healthy',
    service: 'web-frontend',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development'
  });
}