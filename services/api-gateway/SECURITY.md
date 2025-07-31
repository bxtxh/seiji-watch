# Security Configuration for API Gateway

## Environment Variables Setup

⚠️ **IMPORTANT**: The Airtable Personal Access Token (PAT) that was previously hardcoded has been exposed and must be regenerated.

### Steps to Set Up Secure Configuration:

1. **Generate a New Airtable PAT**
   - Go to https://airtable.com/create/tokens
   - Create a new token with the necessary scopes
   - **DO NOT** reuse the exposed token

2. **Create .env File**

   ```bash
   cp .env.template .env
   ```

3. **Update .env with Your Credentials**

   ```
   AIRTABLE_PAT=your_new_pat_here
   AIRTABLE_BASE_ID=appA9UGcgf3NhdnK9
   ```

4. **Never Commit .env Files**
   - The .env file is already in .gitignore
   - Always use environment variables for sensitive data

## CORS Configuration

The API now uses a more restrictive CORS configuration:

- **Allowed Origins**: Only specified origins (default: localhost:3000, localhost:3001)
- **Allowed Methods**: GET, POST, PUT, DELETE, OPTIONS
- **Allowed Headers**: Content-Type, Authorization

To customize CORS settings, update your .env file:

```
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Content-Type,Authorization
```

## Security Best Practices

1. **Environment Variables**
   - Always use environment variables for sensitive data
   - Never hardcode credentials in source code
   - Use .env files for local development only

2. **Token Management**
   - Rotate tokens regularly
   - Use least privilege principle for token scopes
   - Monitor token usage

3. **CORS Policy**
   - Be specific about allowed origins
   - Limit allowed methods to what's needed
   - Review and update CORS settings for production
