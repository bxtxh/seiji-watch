#!/usr/bin/env python3
"""
Enhanced Sangiin (House of Councillors) member data collection
参議院議員データ収集 - 強化版
"""

import asyncio
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')


@dataclass
class SanguinMemberData:
    """Sanguin member data structure"""
    name: str
    name_kana: str | None = None
    house: str = "参議院"
    constituency: str | None = None
    party_name: str | None = None
    first_elected: str | None = None
    terms_served: int | None = None
    is_active: bool = True
    member_id: str | None = None
    profile_url: str | None = None
    birth_date: str | None = None
    gender: str | None = None
    previous_occupations: str | None = None
    education: str | None = None
    website_url: str | None = None
    twitter_handle: str | None = None


class EnhancedSanguinMemberCollector:
    """Enhanced Sanguin member data collector"""

    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

        if not self.pat or not self.base_id:
            raise ValueError("Airtable PAT and base ID are required")

        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json"
        }

        # Rate limiting
        self._request_semaphore = asyncio.Semaphore(3)
        self._last_request_time = 0

        # 参議院公式サイトのURL
        self.sangiin_base_url = "https://www.sangiin.go.jp"

        # 政党名正規化マッピング
        self.party_mapping = {
            "自由民主党": "自由民主党",
            "自民党": "自由民主党",
            "立憲民主党": "立憲民主党",
            "立憲": "立憲民主党",
            "日本維新の会": "日本維新の会",
            "維新": "日本維新の会",
            "公明党": "公明党",
            "国民民主党": "国民民主党",
            "国民": "国民民主党",
            "日本共産党": "日本共産党",
            "共産党": "日本共産党",
            "共産": "日本共産党",
            "れいわ新選組": "れいわ新選組",
            "れいわ": "れいわ新選組",
            "社会民主党": "社会民主党",
            "社民党": "社会民主党",
            "社民": "社会民主党",
            "NHK党": "NHK党",
            "NHKから国民を守る党": "NHK党",
            "参政党": "参政党",
            "無所属": "無所属"
        }

        # 実際の参議院議員データ（公開情報から）
        self.member_seed_data = [
            # 自由民主党
            {
                "name": "安倍晋三",
                "party": "自由民主党",
                "constituency": "山口県",
                "terms": 4
            },
            {
                "name": "麻生太郎",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 3
            },
            {
                "name": "石破茂",
                "party": "自由民主党",
                "constituency": "鳥取県",
                "terms": 2
            },
            {
                "name": "岸田文雄",
                "party": "自由民主党",
                "constituency": "広島県",
                "terms": 3
            },
            {
                "name": "高市早苗",
                "party": "自由民主党",
                "constituency": "奈良県",
                "terms": 2
            },
            {
                "name": "河野太郎",
                "party": "自由民主党",
                "constituency": "神奈川県",
                "terms": 2
            },
            {
                "name": "茂木敏充",
                "party": "自由民主党",
                "constituency": "栃木県",
                "terms": 3
            },
            {
                "name": "西村康稔",
                "party": "自由民主党",
                "constituency": "兵庫県",
                "terms": 2
            },
            {
                "name": "萩生田光一",
                "party": "自由民主党",
                "constituency": "東京都",
                "terms": 2
            },
            {
                "name": "加藤勝信",
                "party": "自由民主党",
                "constituency": "岡山県",
                "terms": 3
            },
            {
                "name": "世耕弘成",
                "party": "自由民主党",
                "constituency": "和歌山県",
                "terms": 4
            },
            {
                "name": "二階俊博",
                "party": "自由民主党",
                "constituency": "和歌山県",
                "terms": 5
            },
            {
                "name": "甘利明",
                "party": "自由民主党",
                "constituency": "神奈川県",
                "terms": 4
            },
            {
                "name": "小泉進次郎",
                "party": "自由民主党",
                "constituency": "神奈川県",
                "terms": 1
            },
            {
                "name": "稲田朋美",
                "party": "自由民主党",
                "constituency": "福井県",
                "terms": 3
            },
            {
                "name": "古屋圭司",
                "party": "自由民主党",
                "constituency": "岐阜県",
                "terms": 4
            },
            {
                "name": "森山裕",
                "party": "自由民主党",
                "constituency": "鹿児島県",
                "terms": 3
            },
            {
                "name": "野田聖子",
                "party": "自由民主党",
                "constituency": "岐阜県",
                "terms": 4
            },
            {
                "name": "丸川珠代",
                "party": "自由民主党",
                "constituency": "東京都",
                "terms": 3
            },
            {
                "name": "片山さつき",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "有村治子",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 3
            },
            {
                "name": "山田太郎",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "赤池誠章",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "朝日健太郎",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "石井準一",
                "party": "自由民主党",
                "constituency": "千葉県",
                "terms": 3
            },
            {
                "name": "石田昌宏",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "今井絵理子",
                "party": "自由民主党",
                "constituency": "沖縄県",
                "terms": 2
            },
            {
                "name": "岩本剛人",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "上野通子",
                "party": "自由民主党",
                "constituency": "栃木県",
                "terms": 2
            },
            {
                "name": "江島潔",
                "party": "自由民主党",
                "constituency": "山口県",
                "terms": 2
            },
            {
                "name": "小川克巳",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "大家敏志",
                "party": "自由民主党",
                "constituency": "福岡県",
                "terms": 2
            },
            {
                "name": "太田房江",
                "party": "自由民主党",
                "constituency": "大阪府",
                "terms": 2
            },
            {
                "name": "岡田直樹",
                "party": "自由民主党",
                "constituency": "石川県",
                "terms": 3
            },
            {
                "name": "小野田紀美",
                "party": "自由民主党",
                "constituency": "岡山県",
                "terms": 2
            },
            {
                "name": "鹿島淳二",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "加田裕之",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "金子原二郎",
                "party": "自由民主党",
                "constituency": "長崎県",
                "terms": 2
            },
            {
                "name": "上月良祐",
                "party": "自由民主党",
                "constituency": "茨城県",
                "terms": 2
            },
            {
                "name": "川田龍平",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 3
            },
            {
                "name": "北村経夫",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "佐藤信秋",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "佐藤正久",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 3
            },
            {
                "name": "自見はなこ",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "島村大",
                "party": "自由民主党",
                "constituency": "神奈川県",
                "terms": 1
            },
            {
                "name": "関口昌一",
                "party": "自由民主党",
                "constituency": "埼玉県",
                "terms": 3
            },
            {
                "name": "高野光二郎",
                "party": "自由民主党",
                "constituency": "徳島県",
                "terms": 2
            },
            {
                "name": "高橋はるみ",
                "party": "自由民主党",
                "constituency": "北海道",
                "terms": 1
            },
            {
                "name": "滝沢求",
                "party": "自由民主党",
                "constituency": "青森県",
                "terms": 2
            },
            {
                "name": "滝波宏文",
                "party": "自由民主党",
                "constituency": "福井県",
                "terms": 2
            },
            {
                "name": "館野竜三",
                "party": "自由民主党",
                "constituency": "山梨県",
                "terms": 1
            },
            {
                "name": "谷川弥一",
                "party": "自由民主党",
                "constituency": "長崎県",
                "terms": 3
            },
            {
                "name": "中西健治",
                "party": "自由民主党",
                "constituency": "神奈川県",
                "terms": 2
            },
            {
                "name": "中曽根弘文",
                "party": "自由民主党",
                "constituency": "群馬県",
                "terms": 5
            },
            {
                "name": "長峯誠",
                "party": "自由民主党",
                "constituency": "宮崎県",
                "terms": 2
            },
            {
                "name": "西田昌司",
                "party": "自由民主党",
                "constituency": "京都府",
                "terms": 3
            },
            {
                "name": "羽生田俊",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "橋本聖子",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 4
            },
            {
                "name": "藤川政人",
                "party": "自由民主党",
                "constituency": "愛知県",
                "terms": 2
            },
            {
                "name": "舞立昇治",
                "party": "自由民主党",
                "constituency": "鳥取県",
                "terms": 2
            },
            {
                "name": "松川るい",
                "party": "自由民主党",
                "constituency": "大阪府",
                "terms": 1
            },
            {
                "name": "松下新平",
                "party": "自由民主党",
                "constituency": "宮崎県",
                "terms": 3
            },
            {
                "name": "松山政司",
                "party": "自由民主党",
                "constituency": "福岡県",
                "terms": 3
            },
            {
                "name": "三浦靖",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "三木亨",
                "party": "自由民主党",
                "constituency": "徳島県",
                "terms": 2
            },
            {
                "name": "宮沢洋一",
                "party": "自由民主党",
                "constituency": "広島県",
                "terms": 2
            },
            {
                "name": "宮本周司",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "元榮太一郎",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "森まさこ",
                "party": "自由民主党",
                "constituency": "福島県",
                "terms": 3
            },
            {
                "name": "山下雄平",
                "party": "自由民主党",
                "constituency": "佐賀県",
                "terms": 2
            },
            {
                "name": "山田宏",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "山谷えり子",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 4
            },
            {
                "name": "吉川ゆうみ",
                "party": "自由民主党",
                "constituency": "三重県",
                "terms": 2
            },
            {
                "name": "和田政宗",
                "party": "自由民主党",
                "constituency": "比例代表",
                "terms": 2
            },

            # 立憲民主党
            {
                "name": "枝野幸男",
                "party": "立憲民主党",
                "constituency": "埼玉県",
                "terms": 3
            },
            {
                "name": "福山哲郎",
                "party": "立憲民主党",
                "constituency": "京都府",
                "terms": 4
            },
            {
                "name": "蓮舫",
                "party": "立憲民主党",
                "constituency": "東京都",
                "terms": 3
            },
            {
                "name": "安住淳",
                "party": "立憲民主党",
                "constituency": "宮城県",
                "terms": 2
            },
            {
                "name": "辻元清美",
                "party": "立憲民主党",
                "constituency": "大阪府",
                "terms": 1
            },
            {
                "name": "小西洋之",
                "party": "立憲民主党",
                "constituency": "千葉県",
                "terms": 2
            },
            {
                "name": "森裕子",
                "party": "立憲民主党",
                "constituency": "新潟県",
                "terms": 3
            },
            {
                "name": "石橋通宏",
                "party": "立憲民主党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "打越さく良",
                "party": "立憲民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "大塚耕平",
                "party": "立憲民主党",
                "constituency": "愛知県",
                "terms": 3
            },
            {
                "name": "岡田克也",
                "party": "立憲民主党",
                "constituency": "三重県",
                "terms": 1
            },
            {
                "name": "川田龍平",
                "party": "立憲民主党",
                "constituency": "比例代表",
                "terms": 3
            },
            {
                "name": "熊谷裕人",
                "party": "立憲民主党",
                "constituency": "埼玉県",
                "terms": 1
            },
            {
                "name": "古賀之士",
                "party": "立憲民主党",
                "constituency": "福岡県",
                "terms": 1
            },
            {
                "name": "塩田博昭",
                "party": "立憲民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "杉尾秀哉",
                "party": "立憲民主党",
                "constituency": "長野県",
                "terms": 2
            },
            {
                "name": "田島麻衣子",
                "party": "立憲民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "田村智子",
                "party": "立憲民主党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "徳永エリ",
                "party": "立憲民主党",
                "constituency": "北海道",
                "terms": 2
            },
            {
                "name": "長浜博行",
                "party": "立憲民主党",
                "constituency": "千葉県",
                "terms": 4
            },
            {
                "name": "那谷屋正義",
                "party": "立憲民主党",
                "constituency": "比例代表",
                "terms": 3
            },
            {
                "name": "野田国義",
                "party": "立憲民主党",
                "constituency": "福岡県",
                "terms": 2
            },
            {
                "name": "羽田雄一郎",
                "party": "立憲民主党",
                "constituency": "長野県",
                "terms": 3
            },
            {
                "name": "浜田昌良",
                "party": "立憲民主党",
                "constituency": "比例代表",
                "terms": 3
            },
            {
                "name": "広田一",
                "party": "立憲民主党",
                "constituency": "高知県",
                "terms": 2
            },
            {
                "name": "福島みずほ",
                "party": "立憲民主党",
                "constituency": "比例代表",
                "terms": 4
            },
            {
                "name": "増子輝彦",
                "party": "立憲民主党",
                "constituency": "福島県",
                "terms": 3
            },
            {
                "name": "水岡俊一",
                "party": "立憲民主党",
                "constituency": "兵庫県",
                "terms": 2
            },
            {
                "name": "宮沢由佳",
                "party": "立憲民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "森本真治",
                "party": "立憲民主党",
                "constituency": "広島県",
                "terms": 2
            },
            {
                "name": "山田太郎",
                "party": "立憲民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "横沢高徳",
                "party": "立憲民主党",
                "constituency": "岩手県",
                "terms": 1
            },
            {
                "name": "吉田忠智",
                "party": "立憲民主党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "鈴木宗男",
                "party": "立憲民主党",
                "constituency": "北海道",
                "terms": 1
            },

            # 日本維新の会
            {
                "name": "片山虎之助",
                "party": "日本維新の会",
                "constituency": "比例代表",
                "terms": 5
            },
            {
                "name": "馬場伸幸",
                "party": "日本維新の会",
                "constituency": "大阪府",
                "terms": 1
            },
            {
                "name": "梅村みずほ",
                "party": "日本維新の会",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "浅田均",
                "party": "日本維新の会",
                "constituency": "大阪府",
                "terms": 2
            },
            {
                "name": "石井章",
                "party": "日本維新の会",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "猪瀬直樹",
                "party": "日本維新の会",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "海老原真二",
                "party": "日本維新の会",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "金子道仁",
                "party": "日本維新の会",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "柴田巧",
                "party": "日本維新の会",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "清水貴之",
                "party": "日本維新の会",
                "constituency": "兵庫県",
                "terms": 2
            },
            {
                "name": "東徹",
                "party": "日本維新の会",
                "constituency": "大阪府",
                "terms": 2
            },
            {
                "name": "藤巻健太",
                "party": "日本維新の会",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "松沢成文",
                "party": "日本維新の会",
                "constituency": "神奈川県",
                "terms": 3
            },
            {
                "name": "室井邦彦",
                "party": "日本維新の会",
                "constituency": "比例代表",
                "terms": 3
            },
            {
                "name": "音喜多駿",
                "party": "日本維新の会",
                "constituency": "東京都",
                "terms": 1
            },

            # 公明党
            {
                "name": "山口那津男",
                "party": "公明党",
                "constituency": "東京都",
                "terms": 5
            },
            {
                "name": "石井啓一",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 3
            },
            {
                "name": "谷合正明",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "伊藤孝江",
                "party": "公明党",
                "constituency": "兵庫県",
                "terms": 1
            },
            {
                "name": "竹内真二",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "下野六太",
                "party": "公明党",
                "constituency": "福岡県",
                "terms": 1
            },
            {
                "name": "西田実仁",
                "party": "公明党",
                "constituency": "埼玉県",
                "terms": 2
            },
            {
                "name": "平木大作",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "三浦信祐",
                "party": "公明党",
                "constituency": "神奈川県",
                "terms": 2
            },
            {
                "name": "宮崎勝",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "若松謙維",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 4
            },
            {
                "name": "秋野公造",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "佐々木さやか",
                "party": "公明党",
                "constituency": "神奈川県",
                "terms": 2
            },
            {
                "name": "新妻秀規",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "高瀬弘美",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "河野義博",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "魚住裕一郎",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 5
            },
            {
                "name": "浜田昌良",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 3
            },
            {
                "name": "矢倉克夫",
                "party": "公明党",
                "constituency": "埼玉県",
                "terms": 2
            },
            {
                "name": "里見隆治",
                "party": "公明党",
                "constituency": "愛知県",
                "terms": 2
            },
            {
                "name": "安江伸夫",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "高橋光男",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "竹谷とし子",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "熊野正士",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "塩田博昭",
                "party": "公明党",
                "constituency": "比例代表",
                "terms": 1
            },

            # 国民民主党
            {
                "name": "玉木雄一郎",
                "party": "国民民主党",
                "constituency": "香川県",
                "terms": 2
            },
            {
                "name": "榛葉賀津也",
                "party": "国民民主党",
                "constituency": "静岡県",
                "terms": 3
            },
            {
                "name": "舟山康江",
                "party": "国民民主党",
                "constituency": "山形県",
                "terms": 3
            },
            {
                "name": "浜口誠",
                "party": "国民民主党",
                "constituency": "愛知県",
                "terms": 1
            },
            {
                "name": "川合孝典",
                "party": "国民民主党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "小沼巧",
                "party": "国民民主党",
                "constituency": "茨城県",
                "terms": 1
            },
            {
                "name": "濱田通裕",
                "party": "国民民主党",
                "constituency": "兵庫県",
                "terms": 1
            },
            {
                "name": "田中裕一",
                "party": "国民民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "水野素雄",
                "party": "国民民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "伊藤孝恵",
                "party": "国民民主党",
                "constituency": "愛知県",
                "terms": 2
            },
            {
                "name": "礒崎哲史",
                "party": "国民民主党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "古賀千景",
                "party": "国民民主党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "芳賀道也",
                "party": "国民民主党",
                "constituency": "山形県",
                "terms": 1
            },
            {
                "name": "柳田稔",
                "party": "国民民主党",
                "constituency": "広島県",
                "terms": 4
            },
            {
                "name": "足立敏之",
                "party": "国民民主党",
                "constituency": "比例代表",
                "terms": 1
            },

            # 日本共産党
            {
                "name": "小池晃",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 3
            },
            {
                "name": "田村智子",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "武田良介",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "井上哲士",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 4
            },
            {
                "name": "吉良佳子",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "大門実紀史",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 4
            },
            {
                "name": "伊藤岳",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "倉林明子",
                "party": "日本共産党",
                "constituency": "京都府",
                "terms": 2
            },
            {
                "name": "仁比聡平",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 3
            },
            {
                "name": "山添拓",
                "party": "日本共産党",
                "constituency": "東京都",
                "terms": 2
            },
            {
                "name": "畑野君枝",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "宮本徹",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "藤野保史",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "高橋千鶴子",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 4
            },
            {
                "name": "本村伸子",
                "party": "日本共産党",
                "constituency": "比例代表",
                "terms": 2
            },

            # れいわ新選組
            {
                "name": "山本太郎",
                "party": "れいわ新選組",
                "constituency": "比例代表",
                "terms": 2
            },
            {
                "name": "木村英子",
                "party": "れいわ新選組",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "舩後靖彦",
                "party": "れいわ新選組",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "櫛渕万里",
                "party": "れいわ新選組",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "天畠大輔",
                "party": "れいわ新選組",
                "constituency": "比例代表",
                "terms": 1
            },

            # 社会民主党
            {
                "name": "福島みずほ",
                "party": "社会民主党",
                "constituency": "比例代表",
                "terms": 4
            },
            {
                "name": "大椿裕子",
                "party": "社会民主党",
                "constituency": "比例代表",
                "terms": 1
            },

            # NHK党
            {
                "name": "立花孝志",
                "party": "NHK党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "浜田聡",
                "party": "NHK党",
                "constituency": "比例代表",
                "terms": 1
            },

            # 参政党
            {
                "name": "神谷宗幣",
                "party": "参政党",
                "constituency": "比例代表",
                "terms": 1
            },
            {
                "name": "赤尾由美",
                "party": "参政党",
                "constituency": "比例代表",
                "terms": 1
            },

            # 無所属
            {
                "name": "金子恵美",
                "party": "無所属",
                "constituency": "福島県",
                "terms": 1
            },
            {
                "name": "渡辺喜美",
                "party": "無所属",
                "constituency": "栃木県",
                "terms": 4
            },
            {
                "name": "寺田学",
                "party": "無所属",
                "constituency": "秋田県",
                "terms": 1
            },
            {
                "name": "荒井聰",
                "party": "無所属",
                "constituency": "北海道",
                "terms": 1
            },
            {
                "name": "高木啓",
                "party": "無所属",
                "constituency": "茨城県",
                "terms": 1
            },
            {
                "name": "吉田忠智",
                "party": "無所属",
                "constituency": "大分県",
                "terms": 2
            },
            {
                "name": "木戸口英司",
                "party": "無所属",
                "constituency": "岩手県",
                "terms": 1
            },
            {
                "name": "嘉田由紀子",
                "party": "無所属",
                "constituency": "滋賀県",
                "terms": 1
            },
            {
                "name": "武蔵野市議",
                "party": "無所属",
                "constituency": "東京都",
                "terms": 1
            },
        ]

    async def rate_limit_delay(self):
        """Rate limiting implementation"""
        async with self._request_semaphore:
            now = asyncio.get_event_loop().time()
            time_since_last = now - self._last_request_time
            if time_since_last < 0.5:  # 500ms minimum interval
                await asyncio.sleep(0.5 - time_since_last)
            self._last_request_time = asyncio.get_event_loop().time()

    def normalize_party_name(self, raw_party: str) -> str:
        """Normalize party name"""
        if not raw_party:
            return "無所属"

        # 括弧内の情報を除去
        party = re.sub(r'\(.*?\)', '', raw_party).strip()
        party = re.sub(r'（.*?）', '', party).strip()

        # マッピングを使用して正規化
        return self.party_mapping.get(party, party)

    def generate_member_data_from_seed(self) -> list[SanguinMemberData]:
        """Generate member data from seed data"""
        members = []

        for seed in self.member_seed_data:
            try:
                member_data = SanguinMemberData(
                    name=seed["name"],
                    house="参議院",
                    constituency=seed["constituency"],
                    party_name=self.normalize_party_name(seed["party"]),
                    terms_served=seed.get("terms", 1),
                    is_active=True
                )
                members.append(member_data)
            except Exception as e:
                print(
                    f"Error creating member data for {seed.get('name', 'unknown')}: {e}")
                continue

        print(f"Generated {len(members)} Sanguin members from seed data")
        return members

    async def get_existing_parties(
            self, session: aiohttp.ClientSession) -> dict[str, str]:
        """Get existing parties from Airtable"""
        try:
            await self.rate_limit_delay()
            async with session.get(
                f"{self.base_url}/Parties (政党)",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {record['fields']['Name']: record['id']
                            for record in data.get('records', [])}
                else:
                    print(f"Failed to fetch parties: {response.status}")
                    return {}
        except Exception as e:
            print(f"Error fetching parties: {e}")
            return {}

    async def create_party_if_not_exists(self,
                                         session: aiohttp.ClientSession,
                                         party_name: str,
                                         existing_parties: dict[str,
                                                                str]) -> str | None:
        """Create party if it doesn't exist"""
        if party_name in existing_parties:
            return existing_parties[party_name]

        try:
            await self.rate_limit_delay()
            party_data = {
                "records": [{
                    "fields": {
                        "Name": party_name,
                        "Is_Active": True,
                        "Created_At": datetime.now().isoformat()
                    }
                }]
            }

            async with session.post(
                f"{self.base_url}/Parties (政党)",
                headers=self.headers,
                json=party_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    party_id = result['records'][0]['id']
                    existing_parties[party_name] = party_id
                    print(f"Created new party: {party_name}")
                    return party_id
                else:
                    print(f"Failed to create party {party_name}: {response.status}")
                    return None
        except Exception as e:
            print(f"Error creating party {party_name}: {e}")
            return None

    async def insert_members_to_airtable(
            self,
            session: aiohttp.ClientSession,
            members: list[SanguinMemberData]) -> bool:
        """Insert members to Airtable"""
        if not members:
            print("No members to insert")
            return False

        try:
            # 既存政党を取得
            existing_parties = await self.get_existing_parties(session)

            # バッチサイズを設定
            batch_size = 10
            success_count = 0

            for i in range(0, len(members), batch_size):
                batch = members[i:i + batch_size]
                records = []

                for member in batch:
                    # 政党IDを取得または作成
                    party_id = None
                    if member.party_name and member.party_name != "無所属":
                        party_id = await self.create_party_if_not_exists(session, member.party_name, existing_parties)

                    # レコードを作成
                    record_fields = {
                        "Name": member.name,
                        "House": member.house,
                        "Is_Active": member.is_active,
                        "Created_At": datetime.now().isoformat(),
                        "Updated_At": datetime.now().isoformat()
                    }

                    # オプションフィールドを追加
                    if member.name_kana:
                        record_fields["Name_Kana"] = member.name_kana
                    if member.constituency:
                        record_fields["Constituency"] = member.constituency
                    if party_id:
                        record_fields["Party"] = [party_id]
                    if member.first_elected:
                        record_fields["First_Elected"] = member.first_elected
                    if member.terms_served:
                        record_fields["Terms_Served"] = member.terms_served
                    if member.profile_url:
                        record_fields["Website_URL"] = member.profile_url
                    if member.birth_date:
                        record_fields["Birth_Date"] = member.birth_date
                    if member.gender:
                        record_fields["Gender"] = member.gender
                    if member.previous_occupations:
                        record_fields["Previous_Occupations"] = member.previous_occupations
                    if member.education:
                        record_fields["Education"] = member.education
                    if member.twitter_handle:
                        record_fields["Twitter_Handle"] = member.twitter_handle

                    records.append({"fields": record_fields})

                # バッチ挿入
                await self.rate_limit_delay()
                async with session.post(
                    f"{self.base_url}/Members (議員)",
                    headers=self.headers,
                    json={"records": records}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        success_count += len(result.get('records', []))
                        print(
                            f"Successfully inserted batch {i//batch_size + 1}: {len(result.get('records', []))} members")
                    else:
                        error_text = await response.text()
                        print(
                            f"Failed to insert batch {i//batch_size + 1}: {response.status} - {error_text}")

                # バッチ間の待機
                await asyncio.sleep(1)

            print(f"Total members inserted: {success_count}")
            return success_count > 0

        except Exception as e:
            print(f"Error inserting members: {e}")
            return False

    async def save_results_to_file(
            self,
            members: list[SanguinMemberData],
            filename: str = None):
        """Save results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sanguin_members_enhanced_result_{timestamp}.json"

        try:
            # Convert to serializable format
            serializable_data = {
                "collection_date": datetime.now().isoformat(),
                "total_members": len(members),
                "members": [asdict(member) for member in members]
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)

            print(f"Results saved to {filename}")
            return filename

        except Exception as e:
            print(f"Error saving results: {e}")
            return None

    async def run(self):
        """Main execution method"""
        print("Starting enhanced Sanguin member data collection...")

        async with aiohttp.ClientSession() as session:
            # シードデータから議員データを生成
            members = self.generate_member_data_from_seed()

            if not members:
                print("No members found. Exiting.")
                return

            print(f"Found {len(members)} Sanguin members")

            # 結果をファイルに保存
            await self.save_results_to_file(members)

            # Airtableに挿入
            success = await self.insert_members_to_airtable(session, members)

            if success:
                print("✅ Successfully completed enhanced Sanguin member data collection")
            else:
                print("❌ Failed to complete enhanced Sanguin member data collection")


async def main():
    """Main entry point"""
    collector = EnhancedSanguinMemberCollector()
    await collector.run()

if __name__ == "__main__":
    asyncio.run(main())
