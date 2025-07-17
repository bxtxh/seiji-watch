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
    // Forward request to API Gateway to get bill issues
    const API_BASE_URL = process.env.API_GATEWAY_URL || "http://localhost:8000";
    const response = await fetch(
      `${API_BASE_URL}/api/issues/bills/${id}/issues`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    if (!response.ok) {
      if (response.status === 404) {
        // Return empty related bills instead of error for non-existent relationships
        return res.status(200).json({
          related_bills: [],
          message: "No related bills found",
        });
      }

      const errorText = await response.text();
      console.error("API Gateway error:", errorText);
      return res.status(response.status).json({
        message: "Failed to fetch related bills",
        error: "API_GATEWAY_ERROR",
      });
    }

    const billsData = await response.json();

    // Transform and return the bills data
    res.status(200).json({
      related_bills: billsData.related_issues || [],
      total_count: billsData.related_issues?.length || 0,
    });
  } catch (error) {
    console.error("Error fetching related bills:", error);

    // Return empty result instead of error to prevent page breaking
    res.status(200).json({
      related_bills: [],
      total_count: 0,
      message: "Could not fetch related bills",
    });
  }
}
