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
    return res.status(400).json({ message: "Bill ID is required" });
  }

  try {
    // Forward request to API Gateway
    const API_BASE_URL = process.env.API_GATEWAY_URL || "http://localhost:8080";
    const response = await fetch(`${API_BASE_URL}/api/bills/${id}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return res.status(404).json({
          message: "Bill not found",
          error: "BILL_NOT_FOUND",
        });
      }

      const errorText = await response.text();
      console.error("API Gateway error:", errorText);
      return res.status(response.status).json({
        message: "Failed to fetch bill details",
        error: "API_GATEWAY_ERROR",
      });
    }

    const billData = await response.json();

    // Return the bill data directly
    res.status(200).json(billData);
  } catch (error) {
    console.error("Error fetching bill details:", error);
    res.status(500).json({
      message: "Internal server error",
      error: "INTERNAL_ERROR",
    });
  }
}
