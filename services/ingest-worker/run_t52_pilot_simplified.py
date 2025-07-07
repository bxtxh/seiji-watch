#!/usr/bin/env python3
"""
Execute T52 pilot dataset generation (simplified version without external dependencies)
Focus on data collection and quality assessment without vector embeddings
"""
import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path

# Load environment variables
def load_env_file(env_file_path):
    """Load environment variables from .env file"""
    if not os.path.exists(env_file_path):
        return False
    
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"\'')
                os.environ[key] = value
    return True

async def collect_pilot_bills_data():
    """Collect pilot bill data for quality validation"""
    print("📄 Phase 1: Bill Data Collection")
    
    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    
    try:
        from scraper.diet_scraper import DietScraper
        
        # Initialize scraper with conservative settings
        scraper = DietScraper(enable_resilience=False)  # Avoid external dependencies
        
        print("🔍 Collecting bill data from Diet website...")
        bills = scraper.fetch_current_bills()
        
        print(f"✅ Successfully collected {len(bills)} bills from source")
        
        # Apply T52 limits
        limited_bills = bills[:30]  # T52 limit
        
        print(f"🎯 T52 Limited scope: {len(limited_bills)} bills")
        
        # Convert to structured data for analysis
        structured_bills = []
        for bill in limited_bills:
            bill_data = {
                'bill_id': bill.bill_id,
                'title': bill.title,
                'status': bill.status,
                'stage': bill.stage,
                'submitter': bill.submitter,
                'category': bill.category,
                'url': bill.url,
                'summary': bill.summary,
                'submission_date': bill.submission_date.isoformat() if bill.submission_date else None,
                'collected_at': datetime.now().isoformat()
            }
            structured_bills.append(bill_data)
        
        print(f"\n📋 Sample bills collected:")
        for i, bill in enumerate(structured_bills[:3], 1):
            print(f"  {i}. {bill['bill_id']}: {bill['title'][:50]}...")
            print(f"     Category: {bill['category']}, Status: {bill['status']}")
        
        return True, structured_bills
        
    except Exception as e:
        print(f"❌ Bill collection failed: {e}")
        import traceback
        traceback.print_exc()
        return False, []

async def collect_pilot_voting_data():
    """Collect pilot voting data for quality validation"""
    print(f"\n🗳️  Phase 2: Voting Data Collection")
    
    try:
        from scraper.voting_scraper import VotingScraper
        
        # Initialize voting scraper
        scraper = VotingScraper()
        
        print("🔍 Collecting voting session data...")
        sessions = scraper.fetch_voting_sessions()
        
        print(f"✅ Successfully collected {len(sessions)} voting sessions")
        
        # Apply T52 limits
        limited_sessions = sessions[:10]  # T52 limit
        
        print(f"🎯 T52 Limited scope: {len(limited_sessions)} sessions")
        
        # Convert to structured data
        structured_sessions = []
        for session in limited_sessions:
            session_data = {
                'bill_number': session.bill_number,
                'bill_title': session.bill_title,
                'vote_date': session.vote_date.isoformat(),
                'vote_type': session.vote_type,
                'vote_stage': session.vote_stage,
                'committee_name': session.committee_name,
                'total_votes': session.total_votes,
                'yes_votes': session.yes_votes,
                'no_votes': session.no_votes,
                'abstain_votes': session.abstain_votes,
                'absent_votes': session.absent_votes,
                'vote_records': []
            }
            
            # Add vote records
            for vote_record in session.vote_records:
                record_data = {
                    'member_name': vote_record.member_name,
                    'member_name_kana': vote_record.member_name_kana,
                    'party_name': vote_record.party_name,
                    'constituency': vote_record.constituency,
                    'house': vote_record.house,
                    'vote_result': vote_record.vote_result
                }
                session_data['vote_records'].append(record_data)
            
            structured_sessions.append(session_data)
        
        print(f"\n📋 Sample voting sessions:")
        for i, session in enumerate(structured_sessions[:2], 1):
            print(f"  {i}. {session['bill_number']}: {session['bill_title'][:50]}...")
            print(f"     Date: {session['vote_date'][:10]}, Records: {len(session['vote_records'])}")
        
        return True, structured_sessions
        
    except Exception as e:
        print(f"❌ Voting data collection failed: {e}")
        import traceback
        traceback.print_exc()
        return False, []

def analyze_data_quality(bills_data, voting_data):
    """Analyze data quality for validation report"""
    print(f"\n📊 Phase 3: Data Quality Analysis")
    
    quality_metrics = {
        'bills_analysis': {
            'total_collected': len(bills_data),
            'complete_records': 0,
            'missing_summaries': 0,
            'missing_dates': 0,
            'category_distribution': {},
            'status_distribution': {},
            'title_length_avg': 0,
            'quality_score': 0
        },
        'voting_analysis': {
            'total_sessions': len(voting_data),
            'total_vote_records': 0,
            'unique_members': set(),
            'unique_parties': set(),
            'vote_type_distribution': {},
            'quality_score': 0
        }
    }
    
    # Analyze bills
    if bills_data:
        title_lengths = []
        for bill in bills_data:
            # Check completeness
            if all(bill.get(field) for field in ['bill_id', 'title', 'status', 'category']):
                quality_metrics['bills_analysis']['complete_records'] += 1
            
            if not bill.get('summary'):
                quality_metrics['bills_analysis']['missing_summaries'] += 1
            
            if not bill.get('submission_date'):
                quality_metrics['bills_analysis']['missing_dates'] += 1
            
            # Category distribution
            category = bill.get('category', 'Unknown')
            quality_metrics['bills_analysis']['category_distribution'][category] = \
                quality_metrics['bills_analysis']['category_distribution'].get(category, 0) + 1
            
            # Status distribution
            status = bill.get('status', 'Unknown')
            quality_metrics['bills_analysis']['status_distribution'][status] = \
                quality_metrics['bills_analysis']['status_distribution'].get(status, 0) + 1
            
            # Title length
            if bill.get('title'):
                title_lengths.append(len(bill['title']))
        
        if title_lengths:
            quality_metrics['bills_analysis']['title_length_avg'] = sum(title_lengths) / len(title_lengths)
        
        # Calculate quality score
        completeness_rate = quality_metrics['bills_analysis']['complete_records'] / len(bills_data)
        summary_rate = 1 - (quality_metrics['bills_analysis']['missing_summaries'] / len(bills_data))
        quality_metrics['bills_analysis']['quality_score'] = (completeness_rate + summary_rate) / 2
    
    # Analyze voting data
    if voting_data:
        for session in voting_data:
            # Count vote records
            vote_records = session.get('vote_records', [])
            quality_metrics['voting_analysis']['total_vote_records'] += len(vote_records)
            
            # Track unique members and parties
            for record in vote_records:
                quality_metrics['voting_analysis']['unique_members'].add(record.get('member_name', ''))
                quality_metrics['voting_analysis']['unique_parties'].add(record.get('party_name', ''))
            
            # Vote type distribution
            vote_type = session.get('vote_type', 'Unknown')
            quality_metrics['voting_analysis']['vote_type_distribution'][vote_type] = \
                quality_metrics['voting_analysis']['vote_type_distribution'].get(vote_type, 0) + 1
        
        # Convert sets to counts
        quality_metrics['voting_analysis']['unique_members'] = len(quality_metrics['voting_analysis']['unique_members'])
        quality_metrics['voting_analysis']['unique_parties'] = len(quality_metrics['voting_analysis']['unique_parties'])
        
        # Calculate quality score
        if quality_metrics['voting_analysis']['total_sessions'] > 0:
            avg_records_per_session = quality_metrics['voting_analysis']['total_vote_records'] / quality_metrics['voting_analysis']['total_sessions']
            quality_metrics['voting_analysis']['quality_score'] = min(avg_records_per_session / 20, 1.0)  # Assume 20 is good
    
    # Display analysis
    print("📊 Bills Data Quality:")
    bills_metrics = quality_metrics['bills_analysis']
    print(f"  • Total bills: {bills_metrics['total_collected']}")
    print(f"  • Complete records: {bills_metrics['complete_records']} ({bills_metrics['complete_records']/bills_metrics['total_collected']*100:.1f}%)")
    print(f"  • Missing summaries: {bills_metrics['missing_summaries']}")
    print(f"  • Average title length: {bills_metrics['title_length_avg']:.1f} characters")
    print(f"  • Quality score: {bills_metrics['quality_score']:.2f}")
    
    print(f"\n📊 Voting Data Quality:")
    voting_metrics = quality_metrics['voting_analysis']
    print(f"  • Total sessions: {voting_metrics['total_sessions']}")
    print(f"  • Total vote records: {voting_metrics['total_vote_records']}")
    print(f"  • Unique members: {voting_metrics['unique_members']}")
    print(f"  • Unique parties: {voting_metrics['unique_parties']}")
    print(f"  • Quality score: {voting_metrics['quality_score']:.2f}")
    
    return quality_metrics

async def execute_t52_pilot_simplified():
    """Execute simplified T52 pilot generation"""
    print("🚀 T52 Simplified Pilot Dataset Generation")
    print(f"📅 Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Target: Quality validation dataset (simplified)")
    print()
    
    start_time = datetime.now()
    
    # Phase 1: Collect bills
    bills_success, bills_data = await collect_pilot_bills_data()
    
    # Phase 2: Collect voting data
    voting_success, voting_data = await collect_pilot_voting_data()
    
    # Phase 3: Analyze quality
    if bills_success or voting_success:
        quality_metrics = analyze_data_quality(bills_data, voting_data)
    else:
        quality_metrics = {}
    
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    # Generate results
    overall_success = bills_success and voting_success
    
    result = {
        'execution_info': {
            'timestamp': datetime.now().isoformat(),
            'execution_type': 'simplified_pilot_generation',
            'target_period': '2025-06-02 to 2025-06-08',
            'duration_seconds': total_time
        },
        'collection_results': {
            'bills_collected': len(bills_data),
            'voting_sessions_collected': len(voting_data),
            'bills_success': bills_success,
            'voting_success': voting_success,
            'overall_success': overall_success
        },
        'data_quality': quality_metrics,
        'pilot_dataset': {
            'bills': bills_data,
            'voting_sessions': voting_data
        },
        'next_steps': {
            'quality_validation': 'Ready for T53 - Data Quality Validation',
            'ui_testing': 'Ready for T54 - UI/UX Testing',
            'external_api_integration': 'Consider adding OpenAI/Weaviate integration'
        }
    }
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"t52_pilot_simplified_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Summary
    print(f"\n{'='*60}")
    print("🏁 T52 Simplified Pilot Generation Summary")
    print(f"{'='*60}")
    
    print(f"⏱️  Duration: {total_time:.2f}s")
    print(f"📄 Bills Collected: {len(bills_data)}")
    print(f"🗳️  Voting Sessions: {len(voting_data)}")
    print(f"✅ Overall Success: {overall_success}")
    
    if overall_success:
        print("\n🎯 Key Achievements:")
        print("  • Real Diet bill data collected and structured")
        print("  • Voting session data with member records")
        print("  • Data quality metrics calculated")
        print("  • Pilot dataset ready for validation")
        
        print("\n📋 Ready for:")
        print("  • T53: Data Quality Validation & Report")
        print("  • T54: UI/UX Testing with Real Data")
        print("  • External API integration when dependencies resolved")
    else:
        print("\n⚠️  Partial success - check individual phase results")
    
    return overall_success

async def main():
    """Main execution function"""
    # Load environment
    env_file = Path(__file__).parent / ".env.local"
    if not load_env_file(env_file):
        print("⚠️  No .env.local file found - continuing with system environment")
    
    # Execute simplified pilot generation
    success = await execute_t52_pilot_simplified()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)