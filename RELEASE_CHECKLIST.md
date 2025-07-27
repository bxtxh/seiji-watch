# Diet Issue Tracker - Release Checklist

This checklist ensures a smooth and safe production release. Complete all items before deploying to production.

## 📋 Pre-Release Checklist

### 1. Code Quality ✓

- [ ] All feature branches merged to `main`
- [ ] No merge conflicts
- [ ] Code review completed for all changes
- [ ] No `TODO` or `FIXME` comments for critical items
- [ ] No hardcoded secrets or API keys
- [ ] No debug code or console.logs in production code

### 2. Testing ✓

#### Automated Tests
- [ ] All unit tests passing (`pytest` for Python, `jest` for JavaScript)
- [ ] All integration tests passing
- [ ] All E2E tests passing (Playwright)
- [ ] Test coverage meets minimum threshold (80%+)

#### Manual Testing
- [ ] Critical user flows tested:
  - [ ] Bill search and filtering
  - [ ] Issue category navigation
  - [ ] Member profile viewing
  - [ ] Speech search functionality
  - [ ] Mobile responsiveness
  - [ ] Offline functionality (PWA)
- [ ] Cross-browser testing completed:
  - [ ] Chrome/Edge
  - [ ] Firefox
  - [ ] Safari
  - [ ] Mobile browsers

### 3. Performance ✓

- [ ] Lighthouse scores verified:
  - [ ] Performance: 90+
  - [ ] Accessibility: 95+
  - [ ] Best Practices: 90+
  - [ ] SEO: 90+
- [ ] API response times < 200ms (p95)
- [ ] Frontend bundle size optimized
- [ ] Database queries optimized (no N+1 queries)

### 4. Security ✓

- [ ] Security audit completed
- [ ] Dependencies updated (no critical vulnerabilities)
- [ ] OWASP Top 10 checklist reviewed
- [ ] API rate limiting configured
- [ ] CORS settings reviewed
- [ ] JWT token expiration appropriate
- [ ] Content Security Policy headers set

### 5. Infrastructure ✓

- [ ] Production infrastructure provisioned
- [ ] Database backups configured
- [ ] Monitoring and alerting set up:
  - [ ] Application metrics
  - [ ] Error tracking
  - [ ] Performance monitoring
  - [ ] Uptime monitoring
- [ ] Auto-scaling configured
- [ ] SSL certificates valid
- [ ] CDN configured for static assets

### 6. Configuration ✓

- [ ] Production environment variables set
- [ ] Secrets stored in Secret Manager
- [ ] API keys rotated if needed
- [ ] Database migrations tested
- [ ] Feature flags configured
- [ ] Third-party service limits verified

### 7. Documentation ✓

- [ ] API documentation up to date
- [ ] README files current
- [ ] Changelog updated
- [ ] Release notes prepared
- [ ] Known issues documented
- [ ] Runbook updated

## 🚀 Release Process

### 1. Pre-Deployment (Day Before)

```bash
# Create release branch
git checkout -b release/v1.0.0

# Update version numbers
# - package.json files
# - pyproject.toml files
# - API version endpoints

# Tag the release
git tag -a v1.0.0 -m "Release version 1.0.0"
```

### 2. Staging Deployment

- [ ] Deploy to staging environment
- [ ] Run smoke tests on staging
- [ ] Verify all integrations working
- [ ] Performance test on staging
- [ ] Security scan on staging

### 3. Production Deployment

```bash
# Trigger production deployment
gcloud builds submit --config=cloudbuild.prod.yaml

# Or via GitHub Actions
# Push tag to trigger production workflow
git push origin v1.0.0
```

### 4. Deployment Steps

1. [ ] Enable maintenance mode (if applicable)
2. [ ] Deploy database migrations
3. [ ] Deploy backend services:
   - [ ] diet-scraper
   - [ ] stt-worker
   - [ ] data-processor
   - [ ] vector-store
   - [ ] api-gateway
   - [ ] notifications-worker
4. [ ] Deploy frontend
5. [ ] Verify health checks passing
6. [ ] Disable maintenance mode

### 5. Post-Deployment Verification

- [ ] All services healthy
- [ ] API endpoints responding
- [ ] Frontend loading correctly
- [ ] Critical user flows working
- [ ] Monitoring showing normal metrics
- [ ] No error spike in logs

## 🚨 Rollback Plan

If issues are detected:

1. **Immediate Rollback** (< 5 minutes)
   ```bash
   # Rollback to previous version
   gcloud run services update-traffic api-gateway --to-revisions=PREVIOUS_REVISION=100
   gcloud run services update-traffic web-frontend --to-revisions=PREVIOUS_REVISION=100
   ```

2. **Database Rollback** (if needed)
   ```bash
   # Run rollback migration
   cd services/data-processor
   poetry run alembic downgrade -1
   ```

3. **Communication**
   - [ ] Update status page
   - [ ] Notify team in Slack
   - [ ] Create incident report

## 📊 Post-Release Monitoring

### First Hour
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Review user feedback channels
- [ ] Verify data pipeline functioning

### First 24 Hours
- [ ] Daily batch jobs completing
- [ ] No memory leaks
- [ ] Database connections stable
- [ ] Cache hit rates normal

### First Week
- [ ] User adoption metrics
- [ ] Feature usage analytics
- [ ] Performance trends
- [ ] Cost analysis

## 📝 Release Communication

### Internal
- [ ] Team notification sent
- [ ] Release notes in Slack/Email
- [ ] Known issues communicated

### External
- [ ] User announcement prepared
- [ ] Social media updates scheduled
- [ ] Documentation site updated
- [ ] API changelog published

## ⚠️ Critical Contacts

| Role | Name | Contact |
|------|------|---------|
| Release Manager | TBD | email/phone |
| Tech Lead | TBD | email/phone |
| DevOps Lead | TBD | email/phone |
| On-Call Engineer | TBD | email/phone |

## 🎯 Success Criteria

- [ ] All services running without errors
- [ ] Performance SLAs met
- [ ] No critical bugs reported
- [ ] User feedback positive
- [ ] Monitoring shows stable system

## 📋 Final Sign-offs

- [ ] Engineering Lead approval
- [ ] QA Lead approval
- [ ] Product Manager approval
- [ ] Security review passed

---

**Release Date**: ________________  
**Release Version**: ________________  
**Release Manager**: ________________  

*Remember: It's better to delay a release than to ship broken code!*