"""Models for bill process history tracking."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import Field

from .base import BaseRecord


class BillProcessHistory(BaseRecord):
    """Bill process history model for tracking legislative progress."""
    
    # Relations
    bill_id: int = Field(..., description="Bill identifier reference")
    
    # Process information
    stage: str = Field(..., description="審議段階")
    house: str = Field(..., description="議院 (参議院/衆議院)")
    committee: Optional[str] = Field(None, description="委員会")
    
    # Action details
    action_date: datetime = Field(..., description="実施日")
    action_type: str = Field(..., description="アクション種別")
    result: Optional[str] = Field(None, description="結果")
    details: Optional[Dict[str, Any]] = Field(None, description="詳細情報")
    notes: Optional[str] = Field(None, description="備考")
    
    def __repr__(self) -> str:
        return f"<BillProcessHistory(bill_id={self.bill_id}, stage='{self.stage}', action_type='{self.action_type}')>"
    
    @property
    def is_committee_action(self) -> bool:
        """Check if this is a committee-level action."""
        return self.committee is not None
    
    @property
    def is_plenary_action(self) -> bool:
        """Check if this is a plenary session action."""
        return self.action_type in ['本会議', '全体会議', '採決', '可決', '否決']
    
    @property
    def is_voting_action(self) -> bool:
        """Check if this is a voting-related action."""
        return self.action_type in ['採決', '可決', '否決', '修正可決']
    
    @property
    def formatted_action_date(self) -> str:
        """Get formatted action date string."""
        return self.action_date.strftime("%Y年%m月%d日")


class BillProcessStage:
    """Constants for bill process stages."""
    
    # 提出・受理段階
    SUBMITTED = "submitted"           # 提出
    RECEIVED = "received"             # 受理
    
    # 委員会段階
    COMMITTEE_REFERRED = "committee_referred"     # 委員会付託
    COMMITTEE_REVIEW = "committee_review"         # 委員会審査
    COMMITTEE_HEARING = "committee_hearing"       # 委員会公聴会
    COMMITTEE_VOTE = "committee_vote"             # 委員会採決
    COMMITTEE_PASSED = "committee_passed"         # 委員会可決
    COMMITTEE_REJECTED = "committee_rejected"     # 委員会否決
    COMMITTEE_AMENDED = "committee_amended"       # 委員会修正
    
    # 本会議段階
    PLENARY_REFERRED = "plenary_referred"         # 本会議付託
    PLENARY_DEBATE = "plenary_debate"             # 本会議討論
    PLENARY_VOTE = "plenary_vote"                 # 本会議採決
    PLENARY_PASSED = "plenary_passed"             # 本会議可決
    PLENARY_REJECTED = "plenary_rejected"         # 本会議否決
    PLENARY_AMENDED = "plenary_amended"           # 本会議修正
    
    # 両院間移動
    INTER_HOUSE_SENT = "inter_house_sent"         # 他院送付
    INTER_HOUSE_RECEIVED = "inter_house_received" # 他院受理
    
    # 最終段階
    ENACTED = "enacted"               # 成立
    REJECTED = "rejected"             # 否決
    WITHDRAWN = "withdrawn"           # 撤回
    EXPIRED = "expired"               # 廃案
    
    # 継続審議
    CONTINUED = "continued"           # 継続審議


class BillProcessActionType:
    """Constants for bill process action types."""
    
    # 提出・受理
    SUBMISSION = "submission"         # 提出
    RECEIPT = "receipt"              # 受理
    
    # 委員会アクション
    COMMITTEE_REFERRAL = "committee_referral"     # 委員会付託
    COMMITTEE_DISCUSSION = "committee_discussion"  # 委員会討議
    COMMITTEE_HEARING = "committee_hearing"       # 委員会公聴会
    COMMITTEE_VOTING = "committee_voting"         # 委員会採決
    COMMITTEE_REPORT = "committee_report"         # 委員会報告
    
    # 本会議アクション
    PLENARY_DISCUSSION = "plenary_discussion"     # 本会議討論
    PLENARY_VOTING = "plenary_voting"             # 本会議採決
    PLENARY_REPORT = "plenary_report"             # 本会議報告
    
    # 修正・変更
    AMENDMENT = "amendment"           # 修正
    REVISION = "revision"             # 改訂
    
    # 最終アクション
    ENACTMENT = "enactment"           # 成立
    REJECTION = "rejection"           # 否決
    WITHDRAWAL = "withdrawal"         # 撤回
    EXPIRATION = "expiration"         # 廃案
    
    # その他
    CONTINUATION = "continuation"     # 継続
    POSTPONEMENT = "postponement"     # 延期
    TRANSFER = "transfer"             # 移管


class BillProcessResult:
    """Constants for bill process results."""
    
    # 可決・承認
    APPROVED = "approved"             # 可決
    PASSED = "passed"                # 通過
    ADOPTED = "adopted"               # 採択
    
    # 否決・拒否
    REJECTED = "rejected"             # 否決
    DENIED = "denied"                # 拒否
    FAILED = "failed"                # 失敗
    
    # 修正
    AMENDED = "amended"               # 修正
    MODIFIED = "modified"             # 変更
    
    # 継続・保留
    CONTINUED = "continued"           # 継続
    POSTPONED = "postponed"           # 延期
    PENDING = "pending"               # 保留
    
    # 撤回・中止
    WITHDRAWN = "withdrawn"           # 撤回
    CANCELLED = "cancelled"           # 中止
    
    # その他
    REFERRED = "referred"             # 付託
    TRANSFERRED = "transferred"       # 移管
    NOTED = "noted"                   # 報告のみ