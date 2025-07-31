/**
 * Data transformation utilities for converting between API responses and frontend models
 */

import { Bill, Issue, Member, Speech } from "@/types";

// Bill transformations
export interface BillRecord {
  id: string;
  fields: {
    Bill_Number: string;
    Name: string;
    Bill_Status: string;
    Category?: string;
    Diet_Session?: string;
    Submitted_Date?: string;
    Summary?: string;
    Notes?: string;
    Stage?: string;
  };
}

export function transformBillRecordToBill(billRecord: BillRecord): Bill {
  return {
    id: billRecord.id,
    bill_number: billRecord.fields.Bill_Number || "",
    title: billRecord.fields.Name || "",
    summary: billRecord.fields.Summary || billRecord.fields.Notes || "",
    category: billRecord.fields.Category || "",
    status: billRecord.fields.Bill_Status || "",
    diet_url: "", // Not available in BillRecord interface
  };
}

// Issue transformations
export interface IssueRecord {
  id: string;
  fields: {
    Title: string;
    Status: string;
    Stage?: string;
    Summary?: string;
    Description?: string;
    Category?: string;
    Priority?: string;
    Updated_At?: string;
    Related_Bills?: string[];
  };
}

export function transformIssueRecordToIssue(issueRecord: IssueRecord): Issue {
  return {
    id: issueRecord.id,
    title: issueRecord.fields.Title || "",
    status: issueRecord.fields.Status || "",
    stage: issueRecord.fields.Stage || "",
    summary: issueRecord.fields.Summary || issueRecord.fields.Description || "",
    category: issueRecord.fields.Category || "",
    priority: issueRecord.fields.Priority || "medium",
    updated_at: issueRecord.fields.Updated_At || new Date().toISOString(),
    related_bills: issueRecord.fields.Related_Bills || [],
  };
}

// Member transformations
export interface MemberRecord {
  id: string;
  fields: {
    Name_JA: string;
    Name_EN?: string;
    Party?: string;
    House?: string;
    District?: string;
    Profile?: string;
    Photo_URL?: string;
  };
}

export function transformMemberRecordToMember(
  memberRecord: MemberRecord
): Member {
  return {
    id: memberRecord.id,
    name_ja: memberRecord.fields.Name_JA || "",
    name_en: memberRecord.fields.Name_EN || "",
    party: memberRecord.fields.Party || "",
    house: memberRecord.fields.House || "",
    district: memberRecord.fields.District || "",
    profile: memberRecord.fields.Profile || "",
    photo_url: memberRecord.fields.Photo_URL || "",
  };
}

// Speech transformations
export interface SpeechRecord {
  id: string;
  fields: {
    Speaker_Name: string;
    Content: string;
    Date: string;
    Meeting_Type?: string;
    Bill_ID?: string;
    Issue_ID?: string;
    Duration?: number;
  };
}

export function transformSpeechRecordToSpeech(
  speechRecord: SpeechRecord
): Partial<Speech> {
  return {
    id: speechRecord.id,
    speaker_name: speechRecord.fields.Speaker_Name || "",
    original_text: speechRecord.fields.Content || "",
    meeting_id: "", // Not available in SpeechRecord
    speech_order: 0, // Not available in SpeechRecord
    speaker_type: "", // Not available in SpeechRecord
    is_interruption: false,
    is_processed: true,
    needs_review: false,
    related_bill_id: speechRecord.fields.Bill_ID,
    duration_seconds: speechRecord.fields.Duration,
  };
}

// Stage mappings for Kanban board
export const STAGE_MAPPINGS = {
  backlog: "審議前",
  in_progress: "審議中",
  in_review: "採決待ち",
  completed: "成立",
} as const;

export function transformEnglishStageToJapanese(
  stage: keyof typeof STAGE_MAPPINGS
): string {
  return STAGE_MAPPINGS[stage] || stage;
}

// API Response standardization
export interface StandardApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  metadata?: {
    total_count?: number;
    page?: number;
    per_page?: number;
    last_updated?: string;
  };
}

export function createSuccessResponse<T>(
  data: T,
  metadata?: StandardApiResponse<T>["metadata"]
): StandardApiResponse<T> {
  return {
    success: true,
    data,
    metadata,
  };
}

export function createErrorResponse<T>(
  error: string
): StandardApiResponse<T | null> {
  return {
    success: false,
    data: null,
    error,
  };
}
