import type { NextApiRequest, NextApiResponse } from "next";
import mockMembers from "@/data/mock-members.json";

interface MemberRecord {
  id: string;
  fields: {
    Name: string;
    Name_Kana: string;
    Party: string;
    House: string;
    Constituency: string;
  };
}

interface MembersResponse {
  success: boolean;
  results: MemberRecord[];
  total_found: number;
}

export default function handler(
  req: NextApiRequest,
  res: NextApiResponse<MembersResponse>
) {
  if (req.method === "GET") {
    const { limit = 20 } = req.query;

    let filteredMembers = mockMembers as MemberRecord[];

    // Apply limit
    const limitNum = parseInt(limit as string, 10);
    if (!isNaN(limitNum) && limitNum > 0) {
      filteredMembers = filteredMembers.slice(0, limitNum);
    }

    res.status(200).json({
      success: true,
      results: filteredMembers,
      total_found: filteredMembers.length,
    });
  } else {
    res.setHeader("Allow", ["GET"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}
