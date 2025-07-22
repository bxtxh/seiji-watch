#!/usr/bin/env python3
"""
Simple FastAPI server for Diet Issue Tracker MVP
Serves production data collected from scraping
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Diet Issue Tracker API",
    description="API for Japanese Diet Issue Tracker",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Load production data
production_data = {}


def load_production_data():
    """Load production data from scraping results"""
    global production_data

    # Find the most recent production data file
    ingest_worker_path = Path(__file__).parent.parent / "ingest-worker"
    data_files = list(ingest_worker_path.glob("production_scraping_june2025_*.json"))

    if not data_files:
        logger.warning("No production data files found")
        return

    # Load the most recent file
    latest_file = max(data_files, key=lambda f: f.stat().st_mtime)
    logger.info(f"Loading production data from: {latest_file}")

    with open(latest_file, encoding="utf-8") as f:
        production_data = json.load(f)

    logger.info(
        f"Loaded {len(production_data.get('production_dataset', {}).get('bills', []))} bills"
    )
    logger.info(
        f"Loaded {len(production_data.get('production_dataset', {}).get('voting_sessions', []))} voting sessions"
    )


# Load data on startup
load_production_data()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Diet Issue Tracker API",
        "version": "1.0.0",
        "data_status": "loaded" if production_data else "empty",
        "bills_count": len(
            production_data.get("production_dataset", {}).get("bills", [])
        ),
        "voting_sessions_count": len(
            production_data.get("production_dataset", {}).get("voting_sessions", [])
        ),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "1.0.0",
        "data_loaded": bool(production_data),
    }


@app.get("/api/health")
async def api_health_check():
    """API Health check endpoint for frontend"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "1.0.0",
        "data_loaded": bool(production_data),
    }


@app.get("/bills")
async def get_bills(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: str | None = Query(None),
    search: str | None = Query(None),
):
    """Get bills with pagination and filtering"""

    if not production_data:
        raise HTTPException(status_code=503, detail="Production data not loaded")

    bills = production_data.get("production_dataset", {}).get("bills", [])

    # Filter by category
    if category:
        bills = [bill for bill in bills if bill.get("category") == category]

    # Filter by search term
    if search:
        search_lower = search.lower()
        bills = [
            bill
            for bill in bills
            if search_lower in bill.get("title", "").lower()
            or search_lower in bill.get("bill_id", "").lower()
        ]

    # Apply pagination
    total = len(bills)
    bills_page = bills[offset : offset + limit]

    return {
        "bills": bills_page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }


@app.get("/bills/{bill_id}")
async def get_bill(bill_id: str):
    """Get specific bill by ID"""

    if not production_data:
        raise HTTPException(status_code=503, detail="Production data not loaded")

    bills = production_data.get("production_dataset", {}).get("bills", [])

    for bill in bills:
        if bill.get("bill_id") == bill_id:
            return bill

    raise HTTPException(status_code=404, detail=f"Bill {bill_id} not found")


@app.get("/voting-sessions")
async def get_voting_sessions(
    limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)
):
    """Get voting sessions with pagination"""

    if not production_data:
        raise HTTPException(status_code=503, detail="Production data not loaded")

    sessions = production_data.get("production_dataset", {}).get("voting_sessions", [])

    # Apply pagination
    total = len(sessions)
    sessions_page = sessions[offset : offset + limit]

    return {
        "voting_sessions": sessions_page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }


@app.get("/voting-sessions/{bill_number}")
async def get_voting_session(bill_number: str):
    """Get voting session by bill number"""

    if not production_data:
        raise HTTPException(status_code=503, detail="Production data not loaded")

    sessions = production_data.get("production_dataset", {}).get("voting_sessions", [])

    for session in sessions:
        if session.get("bill_number") == bill_number:
            return session

    raise HTTPException(
        status_code=404, detail=f"Voting session for bill {bill_number} not found"
    )


@app.get("/search")
async def search_content(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Search across bills and voting sessions"""

    if not production_data:
        raise HTTPException(status_code=503, detail="Production data not loaded")

    results = []
    query_lower = q.lower()

    # Search bills
    bills = production_data.get("production_dataset", {}).get("bills", [])
    for bill in bills:
        if (
            query_lower in bill.get("title", "").lower()
            or query_lower in bill.get("bill_id", "").lower()
            or query_lower in bill.get("category", "").lower()
        ):
            results.append(
                {
                    "type": "bill",
                    "id": bill.get("bill_id"),
                    "title": bill.get("title"),
                    "category": bill.get("category"),
                    "url": bill.get("url"),
                    "relevance": 1.0,  # Simple relevance score
                }
            )

    # Search voting sessions
    sessions = production_data.get("production_dataset", {}).get("voting_sessions", [])
    for session in sessions:
        if (
            query_lower in session.get("bill_title", "").lower()
            or query_lower in session.get("bill_number", "").lower()
        ):
            results.append(
                {
                    "type": "voting_session",
                    "id": session.get("bill_number"),
                    "title": session.get("bill_title"),
                    "vote_date": session.get("vote_date"),
                    "total_votes": session.get("total_votes"),
                    "relevance": 0.8,  # Slightly lower relevance for voting sessions
                }
            )

    # Sort by relevance (descending)
    results.sort(key=lambda x: x["relevance"], reverse=True)

    # Apply pagination
    total = len(results)
    results_page = results[offset : offset + limit]

    return {
        "results": results_page,
        "query": q,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }


@app.get("/categories")
async def get_categories():
    """Get available bill categories"""

    if not production_data:
        raise HTTPException(status_code=503, detail="Production data not loaded")

    bills = production_data.get("production_dataset", {}).get("bills", [])
    categories = {}

    for bill in bills:
        category = bill.get("category", "その他")
        categories[category] = categories.get(category, 0) + 1

    return {
        "categories": [
            {"name": name, "count": count} for name, count in sorted(categories.items())
        ]
    }


@app.get("/stats")
async def get_stats():
    """Get overall statistics"""

    if not production_data:
        raise HTTPException(status_code=503, detail="Production data not loaded")

    bills = production_data.get("production_dataset", {}).get("bills", [])
    sessions = production_data.get("production_dataset", {}).get("voting_sessions", [])

    # Calculate vote records
    total_vote_records = sum(
        len(session.get("vote_records", [])) for session in sessions
    )

    # Calculate categories
    categories = {}
    for bill in bills:
        category = bill.get("category", "その他")
        categories[category] = categories.get(category, 0) + 1

    return {
        "bills": {"total": len(bills), "categories": categories},
        "voting_sessions": {
            "total": len(sessions),
            "total_vote_records": total_vote_records,
        },
        "data_collection": {
            "execution_date": production_data.get("execution_info", {}).get(
                "timestamp"
            ),
            "target_period": production_data.get("execution_info", {}).get(
                "target_period"
            ),
            "processing_time": production_data.get("pipeline_results", {}).get(
                "total_time"
            ),
        },
    }


# Member endpoints for MVP
@app.get("/api/members")
async def get_members_list(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    house: str | None = Query(None),
    party: str | None = Query(None),
    search: str | None = Query(None),
):
    """Get paginated list of members with optional filters"""

    # Mock data for MVP - realistic Japanese names
    parties = [
        "自由民主党",
        "立憲民主党",
        "日本維新の会",
        "公明党",
        "日本共産党",
        "国民民主党",
        "れいわ新選組",
        "社会民主党",
        "無所属",
    ]
    prefectures = [
        "北海道",
        "青森",
        "岩手",
        "宮城",
        "秋田",
        "山形",
        "福島",
        "茨城",
        "栃木",
        "群馬",
        "埼玉",
        "千葉",
        "東京",
        "神奈川",
        "新潟",
        "富山",
        "石川",
        "福井",
        "山梨",
        "長野",
        "岐阜",
        "静岡",
        "愛知",
        "三重",
        "滋賀",
        "京都",
        "大阪",
        "兵庫",
        "奈良",
        "和歌山",
        "鳥取",
        "島根",
        "岡山",
        "広島",
        "山口",
        "徳島",
        "香川",
        "愛媛",
        "高知",
        "福岡",
        "佐賀",
        "長崎",
        "熊本",
        "大分",
        "宮崎",
        "鹿児島",
        "沖縄",
    ]

    family_names = [
        ("田中", "たなか"),
        ("佐藤", "さとう"),
        ("鈴木", "すずき"),
        ("高橋", "たかはし"),
        ("伊藤", "いとう"),
        ("渡辺", "わたなべ"),
        ("山本", "やまもと"),
        ("中村", "なかむら"),
        ("小林", "こばやし"),
        ("加藤", "かとう"),
        ("吉田", "よしだ"),
        ("山田", "やまだ"),
        ("佐々木", "ささき"),
        ("山口", "やまぐち"),
        ("松本", "まつもと"),
        ("井上", "いのうえ"),
        ("木村", "きむら"),
        ("林", "はやし"),
        ("斎藤", "さいとう"),
        ("清水", "しみず"),
        ("山崎", "やまざき"),
        ("森", "もり"),
        ("池田", "いけだ"),
        ("橋本", "はしもと"),
        ("阿部", "あべ"),
        ("石川", "いしかわ"),
        ("前田", "まえだ"),
        ("藤原", "ふじわら"),
        ("後藤", "ごとう"),
        ("近藤", "こんどう"),
    ]

    given_names = [
        ("太郎", "たろう"),
        ("花子", "はなこ"),
        ("一郎", "いちろう"),
        ("美咲", "みさき"),
        ("健", "けん"),
        ("愛", "あい"),
        ("誠", "まこと"),
        ("恵", "めぐみ"),
        ("学", "まなぶ"),
        ("智子", "ともこ"),
        ("正雄", "まさお"),
        ("由美", "ゆみ"),
        ("博", "ひろし"),
        ("理恵", "りえ"),
        ("和也", "かずや"),
        ("純子", "じゅんこ"),
        ("大輔", "だいすけ"),
        ("美穂", "みほ"),
        ("哲也", "てつや"),
        ("真由美", "まゆみ"),
    ]

    mock_members = []
    for i in range(1, 724):  # 723 total Diet members (465 HR + 258 HC)
        family_name = family_names[i % len(family_names)]
        given_name = given_names[i % len(given_names)]
        prefecture = prefectures[i % len(prefectures)]
        party = parties[i % len(parties)]
        house = "house_of_representatives" if i <= 465 else "house_of_councillors"

        constituency_type = "比例代表" if i % 7 == 0 else f"第{(i % 15) + 1}区"

        mock_members.append(
            {
                "member_id": f"member_{i:03d}",
                "name": f"{family_name[0]}{given_name[0]}",
                "name_kana": f"{family_name[1]}{given_name[1]}",
                "house": house,
                "party": party,
                "constituency": f"{prefecture}都道府県{constituency_type}",
                "terms_served": (i % 8) + 1,
            }
        )

    # Sort by name for consistency
    mock_members.sort(key=lambda x: x["name"])

    # Apply filters
    filtered_members = mock_members
    if house:
        filtered_members = [m for m in filtered_members if m["house"] == house]
    if party:
        filtered_members = [m for m in filtered_members if m["party"] == party]
    if search:
        search_lower = search.lower()
        filtered_members = [
            m for m in filtered_members if search_lower in m["name"].lower()
        ]

    # Apply pagination
    offset = (page - 1) * limit
    total_count = len(filtered_members)
    paginated_members = filtered_members[offset : offset + limit]

    return {
        "success": True,
        "members": paginated_members,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total_count,
            "has_next": offset + limit < total_count,
            "has_prev": page > 1,
        },
        "filters": {"house": house, "party": party, "search": search},
    }


@app.get("/api/members/{member_id}")
async def get_member_profile(member_id: str):
    """Get member profile information"""

    # Mock member data
    mock_member = {
        "member_id": member_id,
        "name": "田中太郎",
        "name_kana": "たなかたろう",
        "house": "house_of_representatives",
        "party": "自由民主党",
        "constituency": "東京都第1区",
        "terms_served": 3,
        "committees": ["予算委員会", "厚生労働委員会"],
        "profile_image": None,
        "official_url": "https://example.com/tanaka",
        "elected_date": "2021-10-31",
        "birth_date": "1970-05-15",
        "education": "東京大学法学部卒業",
        "career": "元外務省職員、弁護士",
    }

    return {"success": True, **mock_member}


@app.get("/api/members/{member_id}/voting-stats")
async def get_member_voting_stats(member_id: str):
    """Get member's voting statistics"""

    # Mock voting stats
    mock_stats = {
        "total_votes": 156,
        "attendance_rate": 0.92,
        "party_alignment_rate": 0.87,
        "voting_pattern": {
            "yes_votes": 128,
            "no_votes": 18,
            "abstentions": 6,
            "absences": 4,
        },
    }

    return {"success": True, "member_id": member_id, "stats": mock_stats}


@app.get("/api/policy/member/{member_id}/analysis")
async def get_member_policy_analysis(member_id: str):
    """Get comprehensive policy analysis for a member"""

    # Mock policy analysis
    mock_analysis = {
        "member_id": member_id,
        "analysis_timestamp": "2025-07-09T10:00:00Z",
        "overall_activity_level": 0.87,
        "party_alignment_rate": 0.78,
        "data_completeness": 0.92,
        "stance_distribution": {
            "strong_support": 3,
            "support": 4,
            "neutral": 2,
            "oppose": 1,
            "strong_oppose": 0,
        },
        "strongest_positions": [
            {
                "issue_tag": "経済・産業",
                "issue_name": "経済・産業政策",
                "stance": "strong_support",
                "confidence": 0.95,
                "vote_count": 15,
                "supporting_evidence": [
                    "経済・産業に関する積極的な議員立法を提出",
                    "委員会で経済・産業の推進を強く主張",
                ],
                "last_updated": "2025-07-08T15:30:00Z",
            },
            {
                "issue_tag": "社会保障",
                "issue_name": "社会保障制度",
                "stance": "support",
                "confidence": 0.82,
                "vote_count": 12,
                "supporting_evidence": [
                    "社会保障に関する賛成討論を実施",
                    "委員会質疑で社会保障の必要性を指摘",
                ],
                "last_updated": "2025-07-07T11:15:00Z",
            },
        ],
        "total_issues_analyzed": 10,
    }

    return {"success": True, "analysis": mock_analysis}


# Kanban API endpoint for TOP page (must be defined before dynamic routes)
@app.get("/api/issues/kanban")
async def get_issues_kanban(
    range: str = Query("30d", description="Date range: 7d, 30d, or 90d"),
    max_per_stage: int = Query(8, ge=1, le=50, description="Max items per stage"),
):
    """Get issues organized by Kanban stages for TOP page"""

    if not production_data:
        raise HTTPException(status_code=503, detail="Production data not loaded")

    # Parse date range
    range_days = {"7d": 7, "30d": 30, "90d": 90}.get(range, 30)
    cutoff_date = datetime.now() - timedelta(days=range_days)

    bills = production_data.get("production_dataset", {}).get("bills", [])
    voting_sessions = production_data.get("production_dataset", {}).get(
        "voting_sessions", []
    )

    # Create a mapping of bills to voting sessions
    bill_vote_map = {}
    for session in voting_sessions:
        bill_number = session.get("bill_number", "")
        if bill_number:
            bill_vote_map[bill_number] = session

    # Convert bills to Kanban issues
    kanban_issues = []
    for i, bill in enumerate(bills):
        # Determine stage based on bill and voting data
        bill_id = bill.get("bill_id", f"bill_{i}")
        voting_session = bill_vote_map.get(bill_id)

        # Stage determination logic
        if voting_session:
            vote_date = voting_session.get("vote_date")
            if vote_date:
                stage = "成立"  # Bills with voting sessions are considered passed
            else:
                stage = "採決待ち"  # Voting session exists but no date
        else:
            # No voting session - determine by bill status or default to 審議中
            stage = "審議中"  # Default for bills without voting data

        # Create schedule information
        schedule_from = cutoff_date.strftime("%Y-%m-%d")
        schedule_to = datetime.now().strftime("%Y-%m-%d")

        # Extract category tags
        category = bill.get("category", "その他")
        tags = [category]
        if len(bill.get("title", "")) > 50:
            tags.append("長期審議")

        # Create related bills list
        related_bills = [
            {
                "bill_id": bill_id,
                "title": bill.get("title", ""),
                "stage": stage,
                "bill_number": bill_id,
            }
        ]

        # Generate issue title (shortened bill title)
        full_title = bill.get("title", "")
        issue_title = full_title[:20] + "..." if len(full_title) > 20 else full_title

        kanban_issue = {
            "id": f"ISS-{i + 1:03d}",
            "title": issue_title,
            "stage": stage,
            "schedule": {"from": schedule_from, "to": schedule_to},
            "tags": tags[:3],  # Max 3 tags
            "related_bills": related_bills[:5],  # Max 5 related bills
            "updated_at": datetime.now().strftime("%Y-%m-%d"),
        }

        kanban_issues.append(kanban_issue)

    # Group issues by stage
    stages = {"審議前": [], "審議中": [], "採決待ち": [], "成立": []}

    for issue in kanban_issues:
        stage = issue["stage"]
        if stage in stages:
            stages[stage].append(issue)

    # Limit issues per stage and sort by title
    for stage in stages:
        stages[stage] = sorted(stages[stage], key=lambda x: x["title"])[:max_per_stage]

    # Calculate metadata
    total_issues = sum(len(stage_issues) for stage_issues in stages.values())
    date_range = {
        "from": cutoff_date.strftime("%Y-%m-%d"),
        "to": datetime.now().strftime("%Y-%m-%d"),
    }

    response = {
        "metadata": {
            "total_issues": total_issues,
            "last_updated": datetime.now().isoformat() + "Z",
            "date_range": date_range,
        },
        "stages": stages,
    }

    return response


# Issue API endpoints
@app.get("/api/issues")
async def get_issues(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: str | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
):
    """Get issues list with pagination and filtering"""

    if not production_data:
        raise HTTPException(status_code=503, detail="Production data not loaded")

    bills = production_data.get("production_dataset", {}).get("bills", [])
    voting_sessions = production_data.get("production_dataset", {}).get(
        "voting_sessions", []
    )

    # Create a mapping of bills to voting sessions
    bill_vote_map = {}
    for session in voting_sessions:
        bill_number = session.get("bill_number", "")
        if bill_number:
            bill_vote_map[bill_number] = session

    # Generate issues from bills data
    issues = []
    for i, bill in enumerate(bills):
        bill_id = bill.get("bill_id", f"bill_{i}")
        voting_session = bill_vote_map.get(bill_id)

        # Stage determination logic
        if voting_session:
            vote_date = voting_session.get("vote_date")
            if vote_date:
                stage = "成立"
            else:
                stage = "採決待ち"
        else:
            stage = "審議中"

        # Extract category from bill
        bill_category = bill.get("category", "その他")

        # Create PolicyCategory structure
        policy_category = {
            "id": f"cat_{bill_category.replace('・', '_')}",
            "layer": "L1",
            "title_ja": bill_category,
        }

        # Create IssueTag
        issue_tags = [
            {
                "id": f"tag_{bill_category}",
                "name": bill_category,
                "color_code": "#3B82F6",
                "category": "自動生成",
                "description": f"{bill_category}に関連するイシュー",
            }
        ]

        # Generate issue from bill
        full_title = bill.get("title", "")
        issue_title = full_title[:50] + "..." if len(full_title) > 50 else full_title

        issue = {
            "id": f"ISS-{i + 1:03d}",
            "title": issue_title,
            "description": f"法案「{full_title}」に関連する政策課題",
            "stage": stage,
            "policy_category": policy_category,
            "issue_tags": issue_tags,
            "related_bills": [bill_id],
            "related_bills_count": 1,
            "extraction_confidence": 0.8,
            "is_llm_generated": True,
            "created_at": "2025-07-01T10:00:00Z",
            "updated_at": datetime.now().isoformat() + "Z",
        }

        issues.append(issue)

    # Apply filters
    if category:
        issues = [
            issue
            for issue in issues
            if issue.get("policy_category", {}).get("title_ja") == category
        ]

    if status:
        issues = [issue for issue in issues if issue.get("status") == status]

    if priority:
        issues = [issue for issue in issues if issue.get("priority") == priority]

    # Apply pagination
    total = len(issues)
    issues_page = issues[offset : offset + limit]

    return {
        "success": True,
        "issues": issues_page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }


# Issue tags endpoint (must be before individual issue endpoint)
@app.get("/api/issues/tags")
async def get_issue_tags():
    """Get all available issue tags"""

    if not production_data:
        raise HTTPException(status_code=503, detail="Production data not loaded")

    bills = production_data.get("production_dataset", {}).get("bills", [])

    # Extract unique categories and create tags
    categories = set()
    for bill in bills:
        category = bill.get("category", "その他")
        categories.add(category)

    # Create issue tags from categories
    issue_tags = []
    for i, category in enumerate(sorted(categories)):
        tag = {
            "id": f"tag_{category.replace('・', '_')}_{i}",
            "name": category,
            "color_code": "#3B82F6",
            "category": "政策分野",
            "description": f"{category}分野に関連するイシュー",
        }
        issue_tags.append(tag)

    # Add some common status tags
    status_tags = [
        {
            "id": "tag_long_deliberation",
            "name": "長期審議",
            "color_code": "#F59E0B",
            "category": "審議期間",
            "description": "長期間にわたって審議されているイシュー",
        },
        {
            "id": "tag_urgent",
            "name": "緊急性高",
            "color_code": "#EF4444",
            "category": "緊急度",
            "description": "緊急に対応が必要なイシュー",
        },
        {
            "id": "tag_bipartisan",
            "name": "与野党対立",
            "color_code": "#8B5CF6",
            "category": "審議特徴",
            "description": "与野党間で意見が対立しているイシュー",
        },
    ]

    all_tags = issue_tags + status_tags

    return {"success": True, "tags": all_tags, "total": len(all_tags)}


# Individual Issue API endpoints (defined after specific routes)
@app.get("/api/issues/{issue_id}")
async def get_issue_detail(issue_id: str):
    """Get individual issue details by ID"""

    if not production_data:
        raise HTTPException(status_code=503, detail="Production data not loaded")

    bills = production_data.get("production_dataset", {}).get("bills", [])
    voting_sessions = production_data.get("production_dataset", {}).get(
        "voting_sessions", []
    )

    # Create a mapping of bills to voting sessions
    bill_vote_map = {}
    for session in voting_sessions:
        bill_number = session.get("bill_number", "")
        if bill_number:
            bill_vote_map[bill_number] = session

    # Find the issue by ID (ISS-XXX format)
    try:
        # Extract issue index from ISS-XXX format
        if not issue_id.startswith("ISS-"):
            raise HTTPException(status_code=400, detail="Invalid issue ID format")

        issue_index = int(issue_id.split("-")[1]) - 1  # Convert ISS-001 to index 0

        if issue_index < 0 or issue_index >= len(bills):
            raise HTTPException(status_code=404, detail="Issue not found")

        bill = bills[issue_index]

    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid issue ID format")

    # Determine stage based on bill and voting data
    bill_id = bill.get("bill_id", f"bill_{issue_index}")
    voting_session = bill_vote_map.get(bill_id)

    # Stage determination logic (same as Kanban)
    if voting_session:
        vote_date = voting_session.get("vote_date")
        if vote_date:
            stage = "成立"
        else:
            stage = "採決待ち"
    else:
        stage = "審議中"

    # Create schedule information
    from datetime import datetime, timedelta

    cutoff_date = datetime.now() - timedelta(days=30)
    schedule_from = cutoff_date.strftime("%Y-%m-%d")
    schedule_to = datetime.now().strftime("%Y-%m-%d")

    # Extract category and create IssueTag (イシュータグ) - Issue特有の分類タグ
    category = bill.get("category", "その他")
    issue_tags = [
        {
            "id": f"tag_{category}",
            "name": category,
            "color_code": "#3B82F6",
            "category": "自動生成",
            "description": f"{category}に関連するイシュー",
        }
    ]
    if len(bill.get("title", "")) > 50:
        issue_tags.append(
            {
                "id": "tag_long",
                "name": "長期審議",
                "color_code": "#F59E0B",
                "category": "審議期間",
                "description": "長期間にわたって審議されているイシュー",
            }
        )

    # Create PolicyCategory (政策分野) - CAP基準の政策分類システム
    policy_category = {
        "id": f"cat_{category}",
        "cap_code": "13" if "社会保障" in category else "1",
        "layer": "L1",
        "title_ja": category,
        "parent_category": None,
    }

    # Create related bills list
    related_bills = [
        {
            "bill_id": bill_id,
            "title": bill.get("title", ""),
            "status": "under_review"
            if stage == "審議中"
            else "enacted"
            if stage == "成立"
            else "pending_vote",
            "stage": stage,
            "bill_number": bill_id,
            "relevance_score": 1.0,
            "relationship_type": "primary",
        }
    ]

    # Generate issue title (shortened bill title)
    full_title = bill.get("title", "")
    issue_title = full_title[:20] + "..." if len(full_title) > 20 else full_title

    # Create issue detail response
    issue_detail = {
        "success": True,
        "issue": {
            "id": issue_id,
            "title": issue_title,
            "description": bill.get("title", ""),  # Use full title as description
            "priority": "medium",
            "status": "active",
            "stage": stage,
            "policy_category": policy_category,
            "issue_tags": issue_tags,
            "related_bills_count": len(related_bills),
            "extraction_confidence": 0.95,
            "is_llm_generated": True,
            "created_at": schedule_from + "T10:00:00Z",
            "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "schedule": {"from": schedule_from, "to": schedule_to},
        },
    }

    return issue_detail


@app.get("/api/issues/{issue_id}/bills")
async def get_issue_related_bills(issue_id: str):
    """Get related bills for a specific issue"""

    if not production_data:
        raise HTTPException(status_code=503, detail="Production data not loaded")

    bills = production_data.get("production_dataset", {}).get("bills", [])
    voting_sessions = production_data.get("production_dataset", {}).get(
        "voting_sessions", []
    )

    # Create a mapping of bills to voting sessions
    bill_vote_map = {}
    for session in voting_sessions:
        bill_number = session.get("bill_number", "")
        if bill_number:
            bill_vote_map[bill_number] = session

    # Find the issue by ID
    try:
        if not issue_id.startswith("ISS-"):
            raise HTTPException(status_code=400, detail="Invalid issue ID format")

        issue_index = int(issue_id.split("-")[1]) - 1

        if issue_index < 0 or issue_index >= len(bills):
            raise HTTPException(status_code=404, detail="Issue not found")

        bill = bills[issue_index]

    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid issue ID format")

    # Determine stage
    bill_id = bill.get("bill_id", f"bill_{issue_index}")
    voting_session = bill_vote_map.get(bill_id)

    if voting_session:
        vote_date = voting_session.get("vote_date")
        if vote_date:
            stage = "成立"
        else:
            stage = "採決待ち"
    else:
        stage = "審議中"

    # Create related bills response with PolicyCategory (政策分野) 概念統一
    bill_category = bill.get("category", "その他")
    related_bills = [
        {
            "bill_id": bill_id,
            "title": bill.get("title", ""),
            "summary": bill.get("title", "")[:100] + "..."
            if len(bill.get("title", "")) > 100
            else bill.get("title", ""),
            "policy_category": {
                "id": f"cat_{bill_category}",
                "title_ja": bill_category,
                "layer": "L1",
            },
            "status": "under_review"
            if stage == "審議中"
            else "enacted"
            if stage == "成立"
            else "pending_vote",
            "stage": stage,
            "bill_number": bill_id,
            "diet_url": bill.get("url", "#"),
            "relevance_score": 1.0,
            "relationship_type": "primary",
            "search_method": "direct",
        }
    ]

    return {
        "success": True,
        "bills": related_bills,  # 仕様書に合わせてbillsフィールドに統一
        "total_count": len(related_bills),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
