import type { NextApiRequest, NextApiResponse } from "next";
import mockBills from "@/data/mock-bills.json";

interface BillRecord {
  id: string;
  fields: {
    Bill_Number: string;
    Name: string;
    Bill_Status: string;
    Category?: string;
    Diet_Session?: string;
    Submitted_Date?: string;
    Summary?: string;
    Stage?: string;
  };
}

interface SearchResponse {
  success: boolean;
  results: BillRecord[];
  total_found: number;
  query?: string;
  filters: {
    status?: string;
    stage?: string;
    policy_category_ids?: string[];
    policy_category_layer?: string;
  };
}

export default function handler(req: NextApiRequest, res: NextApiResponse<SearchResponse>) {
  if (req.method === "GET") {
    const { q, status, stage, limit = 20 } = req.query;
    
    let filteredBills = mockBills as BillRecord[];
    
    // Apply search query filter
    if (q && typeof q === "string") {
      filteredBills = filteredBills.filter(bill => 
        bill.fields.Name.toLowerCase().includes(q.toLowerCase()) ||
        (bill.fields.Summary && bill.fields.Summary.toLowerCase().includes(q.toLowerCase()))
      );
    }
    
    // Apply status filter
    if (status && typeof status === "string") {
      filteredBills = filteredBills.filter(bill => 
        bill.fields.Bill_Status === status
      );
    }
    
    // Apply stage filter
    if (stage && typeof stage === "string") {
      filteredBills = filteredBills.filter(bill => 
        bill.fields.Stage === stage
      );
    }
    
    // Apply limit
    const limitNum = parseInt(limit as string, 10);
    if (!isNaN(limitNum) && limitNum > 0) {
      filteredBills = filteredBills.slice(0, limitNum);
    }

    res.status(200).json({
      success: true,
      results: filteredBills,
      total_found: filteredBills.length,
      query: q as string,
      filters: {
        status: status as string,
        stage: stage as string,
      }
    });
  } else {
    res.setHeader("Allow", ["GET"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}