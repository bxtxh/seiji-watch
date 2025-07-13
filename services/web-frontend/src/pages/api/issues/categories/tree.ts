import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Get API URL from environment
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    const response = await fetch(`${apiUrl}/api/issues/categories/tree`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        // Add any auth headers if needed
      },
    });

    if (!response.ok) {
      throw new Error(`API responded with status: ${response.status}`);
    }

    const data = await response.json();
    res.status(200).json(data);
  } catch (error) {
    console.error('Failed to fetch category tree:', error);
    res.status(500).json({ 
      error: 'Failed to fetch category tree',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}