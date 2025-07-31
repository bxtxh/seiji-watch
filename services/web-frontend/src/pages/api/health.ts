import type { NextApiRequest, NextApiResponse } from "next";

type HealthResponse = {
  status: string;
  timestamp: string;
  service: string;
  version: string;
  uptime: number;
};

export default function handler(
  req: NextApiRequest,
  res: NextApiResponse<HealthResponse>
) {
  if (req.method !== "GET") {
    res.setHeader("Allow", ["GET"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
    return;
  }

  const uptime = process.uptime();

  res.status(200).json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    service: "web-frontend",
    version: "1.0.0",
    uptime: Math.floor(uptime),
  });
}
