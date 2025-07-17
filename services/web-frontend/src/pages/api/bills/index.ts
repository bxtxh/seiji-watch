import { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (req.method !== "GET") {
    return res.status(405).json({ message: "Method not allowed" });
  }

  const { max_records = "100", category } = req.query;

  try {
    // Forward request to API Gateway
    const API_BASE_URL = process.env.API_GATEWAY_URL || "http://localhost:8080";

    const queryParams = new URLSearchParams();
    queryParams.append("max_records", String(max_records));
    if (category && typeof category === "string") {
      queryParams.append("category", category);
    }

    const response = await fetch(`${API_BASE_URL}/api/bills?${queryParams}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("API Gateway error:", errorText);
      return res.status(response.status).json({
        message: "Failed to fetch bills",
        error: "API_GATEWAY_ERROR",
      });
    }

    const billsData = await response.json();

    // Return the bills data directly
    res.status(200).json(billsData);
  } catch (error) {
    console.error("Error fetching bills:", error);
    res.status(500).json({
      message: "Internal server error",
      error: "INTERNAL_ERROR",
    });
  }
}
