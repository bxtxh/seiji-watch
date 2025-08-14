# Airtable to Supabase Migration Guide

## Overview

This guide covers the Phase 1 implementation of migrating from Airtable to Supabase for the Diet Issue Tracker project. The migration follows a hybrid approach where Supabase is used for read operations while Airtable remains the source of truth for writes.

## Migration Phases

### Phase 1: Read-Only Migration (Current)
- **Duration**: 2-3 weeks
- **Goal**: Migrate read operations to Supabase while maintaining Airtable for writes
- **Benefits**: 50-80% performance improvement, no API rate limits

### Phase 2: Selective Migration (Future)
- **Duration**: 3-6 months  
- **Goal**: Gradually migrate write operations for stable data
- **Benefits**: Full performance benefits, reduced Airtable dependency

### Phase 3: Full Migration (Future)
- **Duration**: 1-2 months
- **Goal**: Complete migration to Supabase
- **Benefits**: Single data source, maximum performance

## Quick Start

### Prerequisites

1. **Environment Setup**
```bash
# Copy environment template
cp .env.supabase.example .env.supabase

# Edit with your credentials
vim .env.supabase
```

Required environment variables:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Anonymous key for public access
- `SUPABASE_SERVICE_KEY`: Service key for admin operations
- `AIRTABLE_PAT`: Airtable Personal Access Token
- `AIRTABLE_BASE_ID`: Airtable base identifier

2. **Install Dependencies**
```bash
# Python dependencies
pip install -r requirements.txt

# Additional migration tools
pip install click rich python-dotenv
```

3. **Database Setup**
```bash
# Run Supabase migrations
supabase db push

# Or manually execute SQL files
psql $SUPABASE_DB_URL < infra/supabase/migrations/001_initial_schema.sql
psql $SUPABASE_DB_URL < infra/supabase/migrations/002_security_policies.sql
```

### Initial Data Migration

1. **Create a rollback point** (recommended)
```bash
python scripts/migration_cli.py rollback create \
  --phase 1 \
  --description "Before initial migration" \
  --type full
```

2. **Run full migration**
```bash
# Dry run first
python scripts/migration_cli.py migrate full --dry-run

# Execute migration
python scripts/migration_cli.py migrate full
```

3. **Validate migration**
```bash
python scripts/migration_cli.py migrate validate
```

Expected output:
```
Data Consistency Report
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┓
┃ Table             ┃ Airtable ┃ Supabase ┃ Consistency ┃ Status ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━┩
│ Bills             │ 1000     │ 1000     │ 100.0%      │ Valid  │
│ Members           │ 744      │ 744      │ 100.0%      │ Valid  │
│ PolicyCategories  │ 150      │ 150      │ 100.0%      │ Valid  │
└───────────────────┴──────────┴──────────┴─────────────┴────────┘
```

### Starting Sync Service

1. **Start incremental sync**
```bash
python scripts/migration_cli.py sync start \
  --mode incremental \
  --interval 5
```

2. **Monitor sync status**
```bash
python scripts/migration_cli.py sync status
```

3. **View monitoring dashboard**
```bash
python scripts/migration_cli.py monitor dashboard
```

## API Integration

### Using the Hybrid API

The new hybrid API endpoints automatically route requests to the optimal data source:

```python
# Example: Get bills with automatic source selection
GET /api/v2/bills?status=審議中&limit=50

Response:
{
  "data": [...],
  "data_source": "supabase",  # or "airtable", "cache"
  "response_time": 0.125
}
```

### Feature Flags

Control migration behavior through environment variables:

```bash
# Enable/disable Supabase reads
FEATURE_SUPABASE_READ_ENABLED=true

# Enable/disable Supabase writes (Phase 2)
FEATURE_SUPABASE_WRITE_ENABLED=false

# Enable Airtable fallback
FEATURE_AIRTABLE_FALLBACK_ENABLED=true

# Enable caching
FEATURE_CACHE_ENABLED=true
```

## Monitoring

### Health Checks

```bash
# Check system health
python scripts/migration_cli.py monitor health

# API health endpoint
GET /api/v2/monitoring/health
```

### Metrics Dashboard

Access real-time metrics:
```bash
# CLI dashboard
python scripts/migration_cli.py monitor dashboard

# Web dashboard
GET /api/v2/monitoring/dashboard
```

Key metrics to monitor:
- **Supabase Usage Rate**: Should increase over time (target: >80%)
- **Cache Hit Rate**: Should be >80% for optimal performance
- **Error Rate**: Should be <1%
- **Sync Lag**: Should be <5 minutes for incremental sync
- **Data Consistency**: Should be >95%

### Alerts

Active alerts are shown in the dashboard. Critical alerts include:
- Sync failures
- Data inconsistency (<90%)
- High error rates (>5%)
- Connection failures

## Rollback Procedures

### Creating Rollback Points

```bash
# Before major changes
python scripts/migration_cli.py rollback create \
  --phase 1 \
  --description "Before configuration change" \
  --type configuration
```

### Listing Rollback Points

```bash
python scripts/migration_cli.py rollback list
```

### Executing Rollback

```bash
# Rollback to specific point
python scripts/migration_cli.py rollback execute \
  --point-id rollback_1_1234567890 \
  --force
```

## Troubleshooting

### Common Issues

#### 1. Sync Lag Increasing
**Symptom**: Sync lag > 30 minutes

**Solution**:
```bash
# Stop incremental sync
python scripts/migration_cli.py sync stop

# Run full sync for affected table
python scripts/migration_cli.py migrate incremental -t Bills

# Restart sync service
python scripts/migration_cli.py sync start
```

#### 2. Data Inconsistency
**Symptom**: Validation shows <95% consistency

**Solution**:
```bash
# Identify inconsistent tables
python scripts/migration_cli.py migrate validate

# Re-sync specific table
python scripts/migration_cli.py sync table Bills --mode full
```

#### 3. High Error Rate
**Symptom**: Error rate >5% in monitoring

**Check**:
- API rate limits (Airtable: 5 req/sec)
- Database connections
- Network connectivity

**Solution**:
```bash
# Check health
python scripts/migration_cli.py monitor health

# Restart with reduced batch size
python scripts/migration_cli.py migrate full --batch-size 50
```

#### 4. Cache Issues
**Symptom**: Stale data or low hit rate

**Solution**:
```bash
# Clear cache
curl -X POST /api/v2/cache/invalidate?pattern=*

# Check cache stats
curl /api/v2/cache/stats
```

### Log Locations

- Migration logs: `./logs/migration.log`
- Sync logs: `./logs/sync.log`
- API logs: `./logs/api.log`
- Error logs: `./logs/error.log`

### Database Queries

Useful queries for debugging:

```sql
-- Check sync status
SELECT * FROM sync_status 
ORDER BY created_at DESC 
LIMIT 10;

-- Find sync conflicts
SELECT * FROM sync_conflicts 
WHERE resolution_status = 'pending';

-- Check data counts
SELECT 
  'bills' as table_name, 
  COUNT(*) as count 
FROM bills
UNION ALL
SELECT 
  'members', 
  COUNT(*) 
FROM members;

-- Find records without Airtable ID
SELECT * FROM bills 
WHERE airtable_id IS NULL;
```

## Performance Optimization

### Cache Configuration

Optimize cache TTL for different data types:

```python
# Cache configuration in hybrid_data_access.py
cache_config = {
    "parties": CacheStrategy.AGGRESSIVE,      # 1 hour
    "members": CacheStrategy.AGGRESSIVE,      # 1 hour  
    "policy_categories": CacheStrategy.AGGRESSIVE,  # 1 hour
    "bills": CacheStrategy.MODERATE,          # 5 minutes
    "meetings": CacheStrategy.MODERATE,       # 5 minutes
    "speeches": CacheStrategy.LIGHT,          # 1 minute
    "votes": CacheStrategy.LIGHT,             # 1 minute
}
```

### Database Indexing

Ensure proper indexes are in place:

```sql
-- Check existing indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'bills';

-- Add missing indexes if needed
CREATE INDEX CONCURRENTLY idx_bills_status_date 
ON bills(status, submitted_date DESC);
```

### Connection Pooling

Configure connection pool settings:

```bash
# Supabase connection pool
SUPABASE_DB_POOL_MIN=2
SUPABASE_DB_POOL_MAX=10
SUPABASE_DB_POOL_IDLE_TIMEOUT=30000
```

## Security Considerations

### API Authentication

Ensure proper authentication for admin operations:

```python
# Required for write operations
headers = {
    "Authorization": f"Bearer {JWT_TOKEN}",
    "X-Admin-Key": ADMIN_KEY
}
```

### Row Level Security

RLS policies are automatically applied. Key policies:
- Public read access for bills, members, categories
- Admin-only write access
- Service role for sync operations

### Sensitive Data

Never expose in logs or responses:
- API keys
- Database passwords
- Personal information (PII)

## Maintenance

### Regular Tasks

**Daily**:
- Check monitoring dashboard
- Review active alerts
- Verify sync status

**Weekly**:
- Validate data consistency
- Review error logs
- Clean up old rollback points

**Monthly**:
- Full data validation
- Performance review
- Update documentation

### Backup Strategy

```bash
# Create backup before major changes
python scripts/migration_cli.py rollback create \
  --phase 1 \
  --description "Weekly backup" \
  --type full

# Clean old backups (>30 days)
python scripts/migration_cli.py rollback cleanup --days 30
```

## Migration Checklist

### Pre-Migration
- [ ] Environment variables configured
- [ ] Supabase project created
- [ ] Database schema deployed
- [ ] Dependencies installed
- [ ] Rollback point created

### Migration
- [ ] Dry run completed
- [ ] Full migration executed
- [ ] Data validation passed
- [ ] Sync service started
- [ ] Monitoring enabled

### Post-Migration
- [ ] API endpoints tested
- [ ] Performance metrics reviewed
- [ ] Documentation updated
- [ ] Team training completed
- [ ] Rollback procedure tested

## Support

### Resources
- [Supabase Documentation](https://supabase.io/docs)
- [Airtable API Reference](https://airtable.com/api)
- Project Issues: `https://github.com/your-org/seiji-watch/issues`

### Contact
- Technical Lead: `tech-lead@example.com`
- DevOps Team: `devops@example.com`
- On-call: Check PagerDuty schedule

## Appendix

### Table Mappings

| Airtable Table | Supabase Table | Notes |
|---|---|---|
| Parties | parties | Political parties |
| Members | members | Diet members |
| Bills (法案) | bills | Legislative bills |
| IssueCategories | policy_categories | CAP-compliant categories |
| Bills_PolicyCategories | bills_policy_categories | Junction table |
| Meetings | meetings | Diet sessions |
| Speeches | speeches | Member speeches |
| Votes (投票) | votes | Voting records |
| Issues | issues | Policy issues |
| IssueTags | issue_tags | Issue categorization |

### Migration Timeline

**Week 1**:
- Day 1-2: Environment setup
- Day 3-4: Initial migration
- Day 5: Validation and testing

**Week 2**:
- Day 1-2: Sync service setup
- Day 3-4: API integration
- Day 5: Performance testing

**Week 3**:
- Day 1-2: Monitoring setup
- Day 3-4: Documentation
- Day 5: Production deployment

### Version History

- v1.0.0 (2025-01-13): Initial Phase 1 implementation
- v1.0.1: Added rollback procedures
- v1.0.2: Enhanced monitoring capabilities
- v1.0.3: Performance optimizations