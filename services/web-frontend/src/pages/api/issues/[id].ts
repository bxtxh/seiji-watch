import { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  const { id } = req.query;

  if (req.method !== "GET") {
    return res.status(405).json({ message: "Method not allowed" });
  }

  if (!id || typeof id !== "string") {
    return res.status(400).json({ message: "Issue ID is required" });
  }

  try {
    // Forward request to API Gateway
    const API_BASE_URL = process.env.API_GATEWAY_URL || "http://localhost:8080";
    const response = await fetch(`${API_BASE_URL}/api/issues/${id}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return res.status(404).json({
          message: "Issue not found",
          error: "ISSUE_NOT_FOUND",
        });
      }

      const errorText = await response.text();
      console.error("API Gateway error:", errorText);
      return res.status(response.status).json({
        message: "Failed to fetch issue details",
        error: "API_GATEWAY_ERROR",
      });
    }

    const issueData = await response.json();

    // Return the issue data directly
    res.status(200).json(issueData);
  } catch (error) {
    console.error("Error fetching issue details:", error);
    res.status(500).json({
      message: "Internal server error",
      error: "INTERNAL_ERROR",
    });
  }
}
