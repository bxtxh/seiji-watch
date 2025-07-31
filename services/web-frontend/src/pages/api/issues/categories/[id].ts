import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const { id } = req.query;

  if (!id || Array.isArray(id)) {
    return res.status(400).json({ error: "Invalid category ID" });
  }

  try {
    // Get API URL from environment
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    // Route different methods to appropriate endpoints
    let endpoint = `${apiUrl}/api/issues/categories/${id}`;

    if (req.method === "GET") {
      // Check if this is a request for children
      if (req.url?.endsWith("/children")) {
        endpoint = `${apiUrl}/api/issues/categories/${id}/children`;
      }

      const response = await fetch(endpoint, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          return res.status(404).json({ error: "Category not found" });
        }
        throw new Error(`API responded with status: ${response.status}`);
      }

      const data = await response.json();
      res.status(200).json(data);
    } else {
      res.status(405).json({ error: "Method not allowed" });
    }
  } catch (error) {
    console.error("Failed to fetch category:", error);
    res.status(500).json({
      error: "Failed to fetch category",
      details: error instanceof Error ? error.message : "Unknown error",
    });
  }
}
