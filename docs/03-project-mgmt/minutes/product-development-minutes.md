# Product Development Minutes - Database Architecture Decision

**Meeting Date**: July 1, 2025  
**Participants**: Development Team  
**Topic**: Database Architecture & Cost Optimization for MVP + Member Voting Features  
**Decisions**: 
1. Adopt Airtable + Weaviate Cloud approach
2. Add member voting data collection and visualization features

## Current Situation
- **Current Setup**: Cloud SQL Enterprise HA
- **Monthly Cost**: $628
- **Target Budget**: $350/month total infrastructure
- **Required Reduction**: 44% cost cut needed

## Option 1: Vector Database Services

### 1A. Pinecone + Standard Cloud SQL
**Architecture:**
- Pinecone for vector embeddings and semantic search
- Standard Cloud SQL for structured data (bills, members, votes)

**Monthly Costs:**
- **Pinecone Starter**: $70/month (100K vectors, 1024 dimensions)
- **Cloud SQL Standard** (db-custom-2-8192): $180/month  
- **Storage & Backup**: $30/month
- **Total**: $280/month (55% cost reduction)

**Pros:**
- Optimized vector search performance
- Reduces database complexity
- Pinecone handles scaling automatically

**Cons:**
- Two separate systems to maintain
- Data synchronization complexity
- Vendor lock-in for vector operations

### 1B. Weaviate Cloud + Standard Cloud SQL
**Monthly Costs:**
- **Weaviate Sandbox**: $25/month (small scale)
- **Cloud SQL Standard**: $180/month
- **Storage & Backup**: $30/month
- **Total**: $235/month (63% cost reduction)

**Pros:**
- Lower cost than Pinecone
- GraphQL API
- Good for MVP scale

**Cons:**
- Limited scale on sandbox tier
- Less mature ecosystem than Pinecone

### 1C. Qdrant Cloud + Standard Cloud SQL
**Monthly Costs:**
- **Qdrant Cloud Starter**: $20/month
- **Cloud SQL Standard**: $180/month
- **Storage & Backup**: $30/month
- **Total**: $230/month (63% cost reduction)

**Pros:**
- Most cost-effective vector solution
- Open source with good performance
- Easy to migrate to self-hosted later

**Cons:**
- Smaller ecosystem
- Less enterprise support

## Option 2: Airtable-Based Solutions

### 2A. Airtable + Vector Service Hybrid
**Architecture:**
- Airtable for structured data (bills, members, sessions)
- Dedicated vector service for embeddings

**Monthly Costs:**
- **Airtable Pro** (5 users): $100/month
- **Weaviate Cloud**: $25/month
- **Cloud Run** (API layer): $30/month
- **Total**: $155/month (75% cost reduction)

**Pros:**
- Massive cost savings
- Built-in admin interface
- Easy data management for non-technical users
- Fast MVP development

**Cons:**
- API rate limits (5 requests/second)
- Limited complex queries
- Row limits (50,000 records per base)
- Less suitable for high-traffic production

### 2B. Airtable + Self-hosted Vector DB
**Monthly Costs:**
- **Airtable Pro**: $100/month
- **GCE e2-micro** (Qdrant): $7/month
- **Cloud Run** (API): $30/month
- **Total**: $137/month (78% cost reduction)

**Pros:**
- Maximum cost savings
- Full control over vector operations
- Airtable provides excellent data management UI

**Cons:**
- Self-managed vector database
- Higher operational complexity
- Potential reliability concerns

## Option 3: Alternative Database Solutions

### 3A. Supabase + Vector Extension
**Monthly Costs:**
- **Supabase Pro**: $25/month
- **Additional compute**: $50/month
- **Storage**: $10/month
- **Total**: $85/month (86% cost reduction)

**Pros:**
- PostgreSQL-compatible with pgvector
- Built-in auth, API, real-time features
- Generous free tier

**Cons:**
- Smaller scale than Cloud SQL
- Less enterprise features
- Performance limitations

### 3B. PlanetScale + External Vector Service
**Monthly Costs:**
- **PlanetScale Scaler**: $39/month
- **Weaviate**: $25/month
- **Total**: $64/month (90% cost reduction)

**Pros:**
- Serverless MySQL with excellent scaling
- Branching for database schema changes
- Very cost-effective

**Cons:**
- MySQL instead of PostgreSQL
- No built-in vector support
- Schema change workflow different from PostgreSQL

### 3C. Firebase + Vector Service
**Monthly Costs:**
- **Firebase Blaze**: ~$50/month (estimated usage)
- **Weaviate**: $25/month
- **Total**: $75/month (88% cost reduction)

**Pros:**
- NoSQL flexibility
- Real-time updates
- Google Cloud integration

**Cons:**
- Different data model (NoSQL)
- Query limitations for complex relationships
- Potential for unpredictable costs

## Detailed Analysis: Top 3 Recommendations

### Recommendation 1: Airtable + Weaviate Cloud ($155/month)

**Data Architecture:**
```
Airtable Bases:
├── Bills Base (ID, title, status, category, submitter)
├── Members Base (name, party, constituency, house) 
├── Speeches Base (content, speaker_id, bill_id, date)
├── Sessions Base (date, type, participants)
├── Votes Base (bill_id, session_id, vote_type, date)
└── VoteResults Base (vote_id, member_id, position, party)

Weaviate:
└── Speech vectors (content embeddings + metadata)
```

**Implementation Benefits:**
- Airtable provides excellent data management UI
- Non-technical team members can easily update/verify data
- Weaviate handles semantic search efficiently
- 75% cost reduction from current setup

**Limitations:**
- 5 req/sec API limit requires caching strategy
- 50K records per base (manageable for 9-month scope)
- Complex joins require application-level logic

### Recommendation 2: Qdrant Cloud + Standard Cloud SQL ($230/month)

**Benefits:**
- Proven PostgreSQL for complex queries
- Cost-effective vector search with Qdrant
- Familiar SQL operations
- 63% cost reduction

**Migration Path:**
- Keep existing PostgreSQL schema
- Extract vector operations to Qdrant
- Minimal code changes required

### Recommendation 3: Supabase Complete Solution ($85/month)

**Benefits:**
- All-in-one solution (database + API + auth)
- PostgreSQL with pgvector support
- 86% cost reduction
- Fastest development time

**Risks:**
- Performance limits on smaller tier
- Less proven at scale
- Migration complexity if outgrown

## Implementation Strategy

### Phase 1: MVP (Choose Airtable + Weaviate)
- Fastest development with lowest cost
- Airtable for data management and basic CRUD
- Weaviate for semantic search functionality
- Budget: $155/month

### Phase 2: Post-Fundraising Migration
- Migrate to PostgreSQL + Qdrant when traffic grows
- Keep Airtable as admin interface
- Scale vector operations independently

### Phase 3: Full Scale
- Cloud SQL Enterprise HA when revenue supports
- Dedicated vector infrastructure
- Full microservices architecture

## Risk Assessment

### Airtable Approach Risks:
- **API Limits**: Mitigated by caching and rate limiting
- **Scale Limits**: 9-month data scope fits within limits
- **Query Complexity**: Acceptable for MVP functionality

### Vector Service Risks:
- **Vendor Lock-in**: Mitigated by using open standards
- **Data Sync**: Requires robust sync logic between systems
- **Latency**: Additional network hop for search queries

## Final Recommendation

**Choose Airtable + Weaviate Cloud for MVP ($155/month)**

**Rationale:**
1. **75% cost reduction** meets budget constraints
2. **Rapid development** - Airtable provides instant admin UI
3. **Low operational overhead** - both services are fully managed
4. **Clear migration path** when ready to scale
5. **Perfect for MVP scope** - 9 months of Diet data fits comfortably

**Next Steps:**
1. Set up Airtable bases for structured data
2. Configure Weaviate Cloud for vector operations
3. Build API layer to bridge both services
4. Implement caching to handle API rate limits
5. Plan migration strategy for post-fundraising scaling

This approach allows rapid MVP delivery within budget while maintaining a clear path to scale after successful fundraising.

## Additional Feature Decision: Member Voting Data

### Research Summary
Based on internal investigation of Diet voting data availability:

**Data Sources Available:**
- **House of Councillors**: HTML voting result pages with member names and positions
- **House of Representatives**: PDF name lists for roll-call votes only (standing votes excluded)
- **Committee votes**: Not available through official sources

**Implementation Feasibility:**
- **House of Councillors PoC**: 2 person-days (16 hours)
- **House of Representatives addition**: 1.5 person-days (12 hours)
- **UI visualization**: 0.5 person-days (4 hours)
- **Total additional effort**: 32 hours

**Technical Approach:**
1. HTML scraping for House of Councillors voting pages
2. PDF text extraction for House of Representatives roll-call votes
3. Member name dictionary matching for OCR error correction
4. Airtable storage with Members, Votes, and VoteResults bases
5. UI visualization with voting chips and pattern analysis

**Risk Mitigation:**
- XPath backup rules for HTML structure changes
- OCR verification through member name dictionaries
- Clear UI indicators for missing data cases (standing votes, etc.)

**Decision**: Proceed with member voting feature implementation as part of MVP, focusing on House of Councillors data with House of Representatives as secondary priority.

---

## 📝 Implementation Tasks - Member Voting Features
**Added Date**: July 1, 2025

### Infrastructure Team Actions Required:
**T02 Update**: Cloud SQL → Airtable + Weaviate migration (4 hours, due July 2)
**T04 Update**: Data models extension for voting (6 hours, due July 3)

### Development Team Actions Required:
**T16 New**: House of Councillors voting scraper (16 hours, due July 10)
**T17 New**: Voting visualization UI (4 hours, due July 11)
**T23 New**: House of Representatives PDF processing (12 hours, P2 priority)

### Modified Components:
- ~~PostgreSQL + pgvector~~ → **Airtable + Weaviate Cloud** (cost reduction: $628→$155/month)
- ~~High performance targets~~ → **MVP-adjusted performance** (realistic for timeline)
- **Total additional effort**: +32 hours over 3-week timeline