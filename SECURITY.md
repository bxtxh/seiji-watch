# Security Guidelines - Diet Issue Tracker

## 🚨 API Key and Secrets Management

### CRITICAL RULES

1. **NEVER commit API keys, passwords, or secrets to Git**
2. **ALWAYS use environment variables for sensitive data**
3. **IMMEDIATELY revoke any accidentally exposed keys**

### Secure Configuration

#### Environment Files
- ✅ Use `.env.local` for local development
- ✅ Use `.env.production` for production (not committed)
- ✅ `.env.template` shows required variables (safe to commit)
- ❌ NEVER commit `.env*` files with real values

#### API Keys Storage
```bash
# Create your local environment file
cp .env.template .env.local

# Add your real API keys to .env.local
echo "OPENAI_API_KEY=sk-proj-your-real-key-here" >> .env.local
```

### Required API Keys

#### OpenAI API
- **Purpose**: STT (Whisper), LLM (GPT), Embeddings
- **Format**: `sk-proj-...` (project-scoped key recommended)
- **Obtain**: https://platform.openai.com/api-keys
- **Environment**: `OPENAI_API_KEY=sk-proj-...`

#### Airtable API
- **Purpose**: Structured data storage
- **Format**: `pat...` (Personal Access Token)
- **Obtain**: https://airtable.com/create/tokens
- **Environment**: `AIRTABLE_API_KEY=pat...`

#### Weaviate Cloud
- **Purpose**: Vector database
- **Format**: Standard API key
- **Obtain**: https://console.weaviate.cloud/
- **Environment**: `WEAVIATE_API_KEY=...`

#### GCP Service Account
- **Purpose**: Cloud infrastructure
- **Format**: JSON key file
- **Obtain**: GCP Console → IAM → Service Accounts
- **Environment**: `GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json`

## 🔒 Production Security Checklist

### T52 - Production Security Configuration
- [ ] Security headers configured (X-Frame-Options, CSP, HSTS)
- [ ] CORS properly configured for production domains
- [ ] JWT authentication with secure token handling
- [ ] Rate limiting at infrastructure level
- [ ] DDoS protection enabled

### T51 - External API Security
- [ ] Circuit breaker patterns for API calls
- [ ] API key rotation procedure established
- [ ] Rate limiting compliance for all external APIs
- [ ] Error handling without exposing sensitive information

### T59 - Legal Compliance
- [ ] Data retention policies implemented
- [ ] Privacy-compliant analytics tracking
- [ ] GDPR compliance measures (data export, deletion)
- [ ] Audit logging for compliance requirements

## 🚨 Incident Response

### If API Key is Exposed
1. **Immediately revoke the exposed key** at the provider's console
2. **Generate a new key** 
3. **Update all environments** with the new key
4. **Check usage logs** for unauthorized access
5. **Monitor for unusual activity** for 24-48 hours

### Emergency Contacts
- **OpenAI**: https://help.openai.com/
- **Airtable**: https://support.airtable.com/
- **GCP**: https://cloud.google.com/support/

## ✅ Security Best Practices

### Development
- Use project-scoped API keys when available
- Implement request timeouts and retry logic
- Log security events (without exposing sensitive data)
- Regular dependency updates and security scanning

### Production
- Use GCP Secret Manager for production secrets
- Enable audit logging for all API access
- Monitor API usage and billing
- Implement automated secret rotation where possible

### Code Review
- Check for hardcoded secrets before merging
- Verify .gitignore includes all sensitive files
- Validate environment variable usage
- Test with invalid/expired credentials

---

**Remember**: Security is everyone's responsibility. When in doubt, ask for review before committing code that handles sensitive data.

*Last Updated: July 7, 2025*