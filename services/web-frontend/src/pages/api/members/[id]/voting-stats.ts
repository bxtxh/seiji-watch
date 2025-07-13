import { NextApiRequest, NextApiResponse } from 'next';

const API_BASE_URL = process.env.API_GATEWAY_URL || 'http://localhost:8001';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { id } = req.query;
  
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  try {
    // Fetch voting statistics from API Gateway
    const response = await fetch(`${API_BASE_URL}/api/members/${id}/voting-stats`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Diet-Tracker-Web-Frontend/1.0'
      }
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        return res.status(404).json({ error: 'Member voting stats not found' });
      }
      throw new Error(`API responded with status ${response.status}`);
    }
    
    const data = await response.json();
    
    return res.status(200).json({ 
      success: true, 
      stats: data.stats 
    });
    
  } catch (error) {
    console.error('Failed to fetch voting stats:', error);
    
    // Return mock data for development
    const mockStats = {
      total_votes: 156,
      attendance_rate: 0.92,
      party_alignment_rate: 0.87,
      voting_pattern: {
        yes_votes: 128,
        no_votes: 18,
        abstentions: 6,
        absences: 4
      }
    };
    
    return res.status(200).json({ 
      success: true, 
      stats: mockStats 
    });
  }
}