# API Response Standardization Guide

## Overview

All API endpoints should follow a consistent response format to improve client-side handling and error management.

## Standard Response Formats

### Success Response

```json
{
  "success": true,
  "data": <response_data>,
  "message": "Optional success message",
  "count": 10,  // For list responses
  "metadata": {  // Optional metadata
    "timestamp": "2025-07-28T10:00:00Z",
    "version": "1.0.0"
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message",
  "error_code": "VALIDATION_ERROR",  // Optional
  "details": {  // Optional error details
    "field": "email",
    "reason": "Invalid format"
  },
  "timestamp": "2025-07-28T10:00:00Z"
}
```

### Paginated Response

```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  },
  "timestamp": "2025-07-28T10:00:00Z"
}
```

## Implementation Examples

### Before (Current Implementation)

```python
@app.get("/api/members")
async def get_members():
    members = await fetch_airtable("Members")
    return members  # Returns raw array
```

### After (Standardized)

```python
from src.utils.response_format import APIResponse

@app.get("/api/members")
async def get_members():
    try:
        members = await fetch_airtable("Members")
        return APIResponse.success(
            data=members,
            count=len(members),
            message="Members retrieved successfully"
        )
    except Exception as e:
        return APIResponse.error(
            error=str(e),
            status_code=500
        )
```

## Endpoints Requiring Standardization

### High Priority (Before Merge)
1. `/api/health` - Add success wrapper
2. `/api/members` - Wrap in success response with count
3. `/api/issues/kanban` - Already has success format, ensure consistency
4. `/api/bills` - Wrap in success response
5. `/api/speeches` - Wrap in success response

### Medium Priority (Post-Merge)
1. `/api/issues` - Add pagination support
2. `/api/bills/search` - Standardize search response
3. `/api/members/{id}` - Ensure 404 returns standard error
4. `/api/issues/{id}/bills` - Add relationship metadata

## Benefits

1. **Consistent Error Handling**: Clients can always check `success` field
2. **Better Debugging**: Timestamps and error codes help troubleshooting
3. **Future-Proof**: Metadata field allows adding new fields without breaking changes
4. **Type Safety**: Predictable response structure improves TypeScript support

## Migration Strategy

1. Add response utilities to shared code
2. Update endpoints incrementally
3. Maintain backward compatibility during transition
4. Update frontend to handle both formats
5. Complete migration and remove old format support

## Frontend Integration

```typescript
interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  count?: number;
  metadata?: Record<string, any>;
}

async function fetchAPI<T>(url: string): Promise<T> {
  const response = await fetch(url);
  const json: APIResponse<T> = await response.json();
  
  if (!json.success) {
    throw new Error(json.error || 'API request failed');
  }
  
  return json.data!;
}
```