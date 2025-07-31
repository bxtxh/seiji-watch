# Enhanced Issues API Documentation

## Overview

The Enhanced Issues API provides comprehensive dual-level policy issue extraction and management capabilities. This API enables the extraction of policy issues from bill data at two comprehension levels (high school and general reader), with full lifecycle management including human review workflows.

## Base URL

```
https://api.seiji-watch.com/api/issues
```

## Authentication

All API endpoints require authentication via API key in the header:

```
Authorization: Bearer YOUR_API_KEY
```

## Core Concepts

### Dual-Level Issues

- **Level 1 (高校生向け)**: Simplified policy issues using high school-appropriate vocabulary
- **Level 2 (一般読者向け)**: Detailed policy issues for general readers with technical terminology

### Issue Lifecycle

1. **Extraction**: Policy issues extracted from bill data using LLM
2. **Validation**: Issues validated for vocabulary level and verb endings
3. **Review**: Human reviewers approve, reject, or request changes
4. **Publication**: Approved issues become available via API

## Endpoints

### GET /api/issues

Retrieve issues with optional filtering by level, status, and other criteria.

**Parameters:**

- `level` (optional): Filter by issue level (1 or 2)
- `status` (optional): Filter by status (pending, approved, rejected, failed_validation)
- `bill_id` (optional): Filter by source bill ID
- `parent_id` (optional): Filter by parent issue ID
- `max_records` (optional): Maximum number of records to return (default: 100, max: 1000)

**Example Request:**

```bash
curl -X GET "https://api.seiji-watch.com/api/issues?level=1&status=approved&max_records=50" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Example Response:**

```json
{
  "issues": [
    {
      "issue_id": "issue_001",
      "record_id": "rec_abc123",
      "label": "介護制度を改善する",
      "confidence": 0.85,
      "source_bill_id": "bill_001",
      "quality_score": 0.8,
      "status": "approved",
      "created_at": "2024-01-15T10:30:00Z",
      "level": 1
    }
  ],
  "count": 1,
  "level_filter": 1,
  "status_filter": "approved"
}
```

### GET /api/issues/tree

Retrieve hierarchical issue tree structure showing parent-child relationships.

**Parameters:**

- `status` (optional): Filter by status (default: "approved")

**Example Response:**

```json
{
  "tree": [
    {
      "record_id": "rec_parent_1",
      "issue_id": "issue_p1",
      "label_lv1": "介護制度を改善する",
      "confidence": 0.85,
      "source_bill_id": "bill_001",
      "children": [
        {
          "issue_id": "issue_c1",
          "label_lv2": "高齢者介護保険制度の包括的な見直しを実施する",
          "confidence": 0.8,
          "source_bill_id": "bill_001"
        }
      ]
    }
  ],
  "total_parent_issues": 1,
  "total_child_issues": 1,
  "status_filter": "approved"
}
```

### GET /api/issues/{record_id}

Retrieve a specific issue by its Airtable record ID.

**Example Response:**

```json
{
  "issue": {
    "issue_id": "issue_001",
    "label_lv1": "介護制度を改善する",
    "label_lv2": "高齢者介護保険制度の包括的な見直しを実施する",
    "parent_id": null,
    "confidence": 0.85,
    "status": "approved",
    "valid_from": "2024-01-15",
    "valid_to": null,
    "source_bill_id": "bill_001",
    "created_at": "2024-01-15T10:30:00Z",
    "quality_score": 0.8,
    "extraction_version": "1.0.0"
  },
  "record_id": "rec_abc123"
}
```

### POST /api/issues/extract

Extract dual-level issues from bill data using LLM.

**Request Body:**

```json
{
  "bill_id": "bill_001",
  "bill_title": "介護保険制度改正法案",
  "bill_outline": "高齢者の介護負担を軽減し、制度の持続可能性を確保する",
  "background_context": "高齢化社会の進展により介護需要が増加している",
  "expected_effects": "介護費用の削減と質の向上が期待される",
  "key_provisions": ["自己負担率の見直し", "サービス提供体制の強化"],
  "submitter": "厚生労働省",
  "category": "社会保障"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Extracted and created 1 issue pairs",
  "bill_id": "bill_001",
  "created_issues": [
    {
      "lv1_record_id": "rec_lv1_123",
      "lv2_record_id": "rec_lv2_456",
      "label_lv1": "介護制度を改善する",
      "label_lv2": "高齢者介護保険制度の包括的な見直しを実施する",
      "confidence": 0.85,
      "quality_score": 0.8
    }
  ],
  "extraction_metadata": {
    "extraction_time_ms": 1500,
    "model_used": "gpt-4",
    "total_quality_score": 0.8
  }
}
```

### POST /api/issues/extract/batch

Extract issues from multiple bills in a single request.

**Request Body:**

```json
[
  {
    "bill_id": "bill_001",
    "bill_title": "介護保険制度改正法案",
    "bill_outline": "高齢者の介護負担を軽減する"
  },
  {
    "bill_id": "bill_002",
    "bill_title": "環境保護促進法案",
    "bill_outline": "環境保護を促進し、持続可能な社会を実現する"
  }
]
```

**Response:**

```json
{
  "message": "Processed 2 bills, 2 successful",
  "total_issues_created": 2,
  "results": [
    {
      "bill_id": "bill_001",
      "success": true,
      "issues_created": 1,
      "created_issues": [...]
    },
    {
      "bill_id": "bill_002",
      "success": true,
      "issues_created": 1,
      "created_issues": [...]
    }
  ]
}
```

### PATCH /api/issues/{record_id}/status

Update the status of an issue (for human review workflow).

**Request Body:**

```json
{
  "status": "approved",
  "reviewer_notes": "High quality issue with clear language"
}
```

**Valid Status Values:**

- `pending`: Awaiting review
- `approved`: Approved by reviewer
- `rejected`: Rejected by reviewer
- `failed_validation`: Failed automatic validation

**Response:**

```json
{
  "success": true,
  "message": "Issue status updated to approved",
  "record_id": "rec_abc123",
  "status": "approved"
}
```

### POST /api/issues/search

Search issues by text query with advanced filtering.

**Request Body:**

```json
{
  "query": "介護",
  "level": 1,
  "status": "approved",
  "max_records": 50
}
```

**Response:**

```json
{
  "query": "介護",
  "results": [
    {
      "record_id": "rec_abc123",
      "issue_id": "issue_001",
      "label_lv1": "介護制度を改善する",
      "label_lv2": "",
      "parent_id": null,
      "confidence": 0.85,
      "source_bill_id": "bill_001",
      "quality_score": 0.8,
      "status": "approved",
      "level": 1
    }
  ],
  "count": 1,
  "level_filter": 1,
  "status_filter": "approved"
}
```

### GET /api/issues/statistics

Get comprehensive statistics about issues in the system.

**Response:**

```json
{
  "total_issues": 1250,
  "approved_count": 1000,
  "pending_count": 200,
  "rejected_count": 50,
  "failed_validation_count": 0,
  "by_level": {
    "lv1": 625,
    "lv2": 625
  },
  "average_confidence": 0.83,
  "average_quality_score": 0.78,
  "unique_bills_count": 250,
  "issues_by_bill": {
    "bill_001": 5,
    "bill_002": 3
  }
}
```

### GET /api/issues/pending/count

Get count of pending issues for notification purposes.

**Parameters:**

- `exclude_failed_validation` (optional): Exclude failed validation issues (default: true)

**Response:**

```json
{
  "pending_count": 15,
  "exclude_failed_validation": true,
  "timestamp": "2024-01-15T14:30:00Z"
}
```

### GET /api/issues/health

Health check endpoint for the enhanced issues service.

**Response:**

```json
{
  "status": "healthy",
  "components": {
    "airtable_manager": "healthy",
    "policy_extractor": "healthy"
  },
  "timestamp": "2024-01-15T14:30:00Z"
}
```

## Error Handling

The API uses standard HTTP status codes and returns error details in a consistent format:

```json
{
  "error": "Validation failed",
  "detail": "Bill title cannot be empty",
  "status_code": 422
}
```

### Common Status Codes

- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `422`: Validation Error
- `429`: Rate Limited
- `500`: Internal Server Error

## Rate Limiting

API requests are limited to:

- **100 requests per minute** per API key for regular endpoints
- **10 requests per minute** per API key for extraction endpoints
- **5 requests per minute** per API key for batch extraction

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642257600
```

## Data Validation

### Issue Labels

- **Length**: 10-60 characters
- **Language**: Japanese text
- **Verb Endings**: Must end with appropriate Japanese verb forms
- **Vocabulary**: Level 1 issues must use high school-appropriate vocabulary

### Confidence Scores

- **Range**: 0.0 to 1.0
- **Interpretation**:
  - 0.8-1.0: High confidence
  - 0.6-0.8: Medium confidence
  - 0.0-0.6: Low confidence

### Quality Scores

- **Range**: 0.0 to 1.0
- **Factors**: Label quality, confidence, review status, bill linkage

## Webhooks

The system supports webhooks for real-time notifications of issue status changes.

### Webhook Events

- `issue.approved`: Issue approved by reviewer
- `issue.rejected`: Issue rejected by reviewer
- `issue.created`: New issue extracted and created

### Webhook Payload

```json
{
  "event": "issue.approved",
  "timestamp": "2024-01-15T14:30:00Z",
  "data": {
    "record_id": "rec_abc123",
    "issue_id": "issue_001",
    "old_status": "pending",
    "new_status": "approved",
    "reviewer_notes": "High quality issue"
  }
}
```

## SDKs and Libraries

### JavaScript/TypeScript

```bash
npm install @seiji-watch/issues-api
```

```javascript
import { IssuesAPI } from "@seiji-watch/issues-api";

const api = new IssuesAPI("YOUR_API_KEY");

// Get level 1 issues
const issues = await api.getIssues({ level: 1, status: "approved" });

// Extract issues from bill
const result = await api.extractIssues({
  bill_id: "bill_001",
  bill_title: "介護保険制度改正法案",
  bill_outline: "...",
});
```

### Python

```bash
pip install seiji-watch-issues-api
```

```python
from seiji_watch import IssuesAPI

api = IssuesAPI('YOUR_API_KEY')

# Get level 1 issues
issues = api.get_issues(level=1, status='approved')

# Extract issues from bill
result = api.extract_issues({
    'bill_id': 'bill_001',
    'bill_title': '介護保険制度改正法案',
    'bill_outline': '...'
})
```

## Examples

### Frontend Level Toggle

```javascript
// Toggle between level 1 and level 2 display
async function toggleIssueLevel(currentLevel) {
  const newLevel = currentLevel === 1 ? 2 : 1;

  const issues = await api.getIssues({
    level: newLevel,
    status: "approved",
    max_records: 100,
  });

  displayIssues(issues, newLevel);
}
```

### Batch Processing Workflow

```python
# Process multiple bills efficiently
bills = [
  {'bill_id': 'bill_001', 'bill_title': '法案1', 'bill_outline': '...'},
  {'bill_id': 'bill_002', 'bill_title': '法案2', 'bill_outline': '...'},
]

result = api.batch_extract_issues(bills)
print(f"Created {result['total_issues_created']} issue pairs")
```

### Human Review Integration

```javascript
// Approve an issue after review
async function approveIssue(recordId, reviewerNotes) {
  const result = await api.updateIssueStatus(recordId, {
    status: "approved",
    reviewer_notes: reviewerNotes,
  });

  console.log("Issue approved:", result.message);
}
```

## Best Practices

### Performance

- Use batch extraction for multiple bills
- Implement caching for frequently accessed issues
- Use pagination for large result sets
- Filter by level to reduce response size

### Quality Assurance

- Always validate extracted issues before publishing
- Implement human review workflows for quality control
- Monitor confidence scores and quality metrics
- Use appropriate vocabulary levels for target audiences

### Error Handling

- Implement exponential backoff for rate limiting
- Handle network failures gracefully
- Validate input data before API calls
- Log errors for debugging and monitoring

### Security

- Keep API keys secure and rotate regularly
- Use HTTPS for all API communications
- Validate and sanitize all user inputs
- Implement proper access controls

## Changelog

### v1.0.0 (2024-01-15)

- Initial release of Enhanced Issues API
- Dual-level issue extraction and management
- Human review workflow support
- Comprehensive filtering and search capabilities
