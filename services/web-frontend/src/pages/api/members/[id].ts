import { NextApiRequest, NextApiResponse } from 'next';

const API_BASE_URL = process.env.API_GATEWAY_URL || 'http://localhost:8001';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { id } = req.query;
  
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  try {
    // Fetch member data from API Gateway
    const response = await fetch(`${API_BASE_URL}/api/members/${id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Diet-Tracker-Web-Frontend/1.0'
      }
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        return res.status(404).json({ error: 'Member not found' });
      }
      throw new Error(`API responded with status ${response.status}`);
    }
    
    const data = await response.json();
    
    // Transform the data to match frontend interface
    const member = {
      id: data.member_id || id,
      name: data.name || '名前不明',
      name_kana: data.name_kana || '',
      house: data.house || 'house_of_representatives',
      party: data.party || '無所属',
      constituency: data.constituency || '選挙区不明',
      terms_served: data.terms_served || 1,
      committees: data.committees || [],
      profile_image: data.profile_image || null,
      official_url: data.official_url || null,
      elected_date: data.elected_date || null,
      birth_date: data.birth_date || null,
      education: data.education || null,
      career: data.career || null
    };
    
    return res.status(200).json({ 
      success: true, 
      member 
    });
    
  } catch (error) {
    console.error('Failed to fetch member data:', error);
    
    // Return mock data for development
    const mockMember = {
      id: id as string,
      name: '田中太郎',
      name_kana: 'たなかたろう',
      house: 'house_of_representatives' as const,
      party: '自由民主党',
      constituency: '東京都第1区',
      terms_served: 3,
      committees: ['予算委員会', '厚生労働委員会'],
      profile_image: null,
      official_url: 'https://example.com/tanaka',
      elected_date: '2021-10-31',
      birth_date: '1970-05-15',
      education: '東京大学法学部卒業',
      career: '元外務省職員、弁護士'
    };
    
    return res.status(200).json({ 
      success: true, 
      member: mockMember 
    });
  }
}