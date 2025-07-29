import React, {
  useState,
  useEffect,
  useMemo,
  useCallback,
  useRef,
} from "react";
import { useRouter } from "next/router";
import { useVirtualizer } from "@tanstack/react-virtual";
import * as wanakana from "wanakana";
import Layout from "@/components/Layout";
import { useObservability } from "@/lib/observability";

interface Member {
  id: string;
  name: string;
  name_kana: string;
  house: "house_of_representatives" | "house_of_councillors";
  party: string;
  constituency: string;
  terms_served: number;
  profile_image_url?: string | null;
  created_at?: string;
}

const MembersPage: React.FC = () => {
  const router = useRouter();
  const { recordPageView, recordError, recordMetric } = useObservability();
  const parentRef = useRef<HTMLDivElement>(null);

  const [allMembers, setAllMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search and filters
  const [searchQuery, setSearchQuery] = useState("");
  const [houseFilter, setHouseFilter] = useState<string>("");
  const [partyFilter, setPartyFilter] = useState<string>("");
  const [searchMode, setSearchMode] = useState<"auto" | "hiragana" | "romaji">(
    "auto",
  );

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";

  useEffect(() => {
    recordPageView("members_virtualized");
  }, [recordPageView]);

  // Memoized mock data cache
  const mockMembersCache = useRef<Member[] | null>(null);

  // Generate comprehensive mock data for 700+ members
  const generateMockMembers = useCallback((): Member[] => {
    // Return cached data if available
    if (mockMembersCache.current) {
      return mockMembersCache.current;
    }
    const parties = [
      "自由民主党",
      "立憲民主党",
      "日本維新の会",
      "公明党",
      "日本共産党",
      "国民民主党",
      "れいわ新選組",
      "社会民主党",
      "無所属",
    ];
    const prefectures = [
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
    ];

    const familyNames = [
      { kanji: "田中", kana: "たなか" },
      { kanji: "佐藤", kana: "さとう" },
      { kanji: "鈴木", kana: "すずき" },
      { kanji: "高橋", kana: "たかはし" },
      { kanji: "伊藤", kana: "いとう" },
      { kanji: "渡辺", kana: "わたなべ" },
      { kanji: "山本", kana: "やまもと" },
      { kanji: "中村", kana: "なかむら" },
      { kanji: "小林", kana: "こばやし" },
      { kanji: "加藤", kana: "かとう" },
      { kanji: "吉田", kana: "よしだ" },
      { kanji: "山田", kana: "やまだ" },
      { kanji: "佐々木", kana: "ささき" },
      { kanji: "山口", kana: "やまぐち" },
      { kanji: "松本", kana: "まつもと" },
      { kanji: "井上", kana: "いのうえ" },
      { kanji: "木村", kana: "きむら" },
      { kanji: "林", kana: "はやし" },
      { kanji: "斎藤", kana: "さいとう" },
      { kanji: "清水", kana: "しみず" },
      { kanji: "山崎", kana: "やまざき" },
      { kanji: "森", kana: "もり" },
      { kanji: "池田", kana: "いけだ" },
      { kanji: "橋本", kana: "はしもと" },
      { kanji: "阿部", kana: "あべ" },
      { kanji: "石川", kana: "いしかわ" },
      { kanji: "前田", kana: "まえだ" },
      { kanji: "藤原", kana: "ふじわら" },
      { kanji: "後藤", kana: "ごとう" },
      { kanji: "近藤", kana: "こんどう" },
    ];

    const givenNames = [
      { kanji: "太郎", kana: "たろう" },
      { kanji: "花子", kana: "はなこ" },
      { kanji: "一郎", kana: "いちろう" },
      { kanji: "美咲", kana: "みさき" },
      { kanji: "健", kana: "けん" },
      { kanji: "愛", kana: "あい" },
      { kanji: "誠", kana: "まこと" },
      { kanji: "恵", kana: "めぐみ" },
      { kanji: "学", kana: "まなぶ" },
      { kanji: "智子", kana: "ともこ" },
      { kanji: "正雄", kana: "まさお" },
      { kanji: "由美", kana: "ゆみ" },
      { kanji: "博", kana: "ひろし" },
      { kanji: "理恵", kana: "りえ" },
      { kanji: "和也", kana: "かずや" },
      { kanji: "純子", kana: "じゅんこ" },
      { kanji: "大輔", kana: "だいすけ" },
      { kanji: "美穂", kana: "みほ" },
      { kanji: "哲也", kana: "てつや" },
      { kanji: "真由美", kana: "まゆみ" },
    ];

    const members: Member[] = [];

    for (let i = 1; i <= 723; i++) {
      // Realistic number of Diet members
      const familyName = familyNames[i % familyNames.length];
      const givenName = givenNames[i % givenNames.length];
      const prefecture = prefectures[i % prefectures.length];
      const party = parties[Math.floor(Math.random() * parties.length)];
      const house =
        i <= 465 ? "house_of_representatives" : "house_of_councillors"; // 465 HR, 248 HC

      const constituencyType =
        house === "house_of_representatives"
          ? Math.random() > 0.8
            ? "比例代表"
            : `第${Math.floor(Math.random() * 15) + 1}区`
          : Math.random() > 0.5
            ? "選挙区"
            : "比例代表";

      members.push({
        id: `member_${i.toString().padStart(3, "0")}`,
        name: `${familyName.kanji}${givenName.kanji}`,
        name_kana: `${familyName.kana}${givenName.kana}`,
        house,
        party,
        constituency: `${prefecture}都道府県${constituencyType}`,
        terms_served: Math.floor(Math.random() * 8) + 1,
      });
    }

    const sortedMembers = members.sort((a, b) => a.name.localeCompare(b.name, "ja"));
    // Cache the generated data
    mockMembersCache.current = sortedMembers;
    return sortedMembers;
  }, []);

  useEffect(() => {
    const loadMembers = async () => {
      try {
        setLoading(true);
        setError(null);

        // Try to fetch from API first, fallback to mock data
        try {
          const response = await fetch(
            `${API_BASE_URL}/api/members?limit=1000`,
          );
          if (response.ok) {
            const data = await response.json();
            // Transform Airtable data to match the expected format
            if (Array.isArray(data) && data.length > 0) {
              const transformedMembers = data.map((record: any) => ({
                id: record.id,
                name: record.fields?.Name || "",
                name_kana: record.fields?.Name_Kana || "",
                house: (record.fields?.House === "衆議院" ? "house_of_representatives" : "house_of_councillors") as "house_of_representatives" | "house_of_councillors",
                party: record.fields?.Party_Name || "無所属",
                constituency: record.fields?.Constituency || "",
                terms_served: record.fields?.Terms_Served || 1,
                profile_image_url: null,
                created_at: record.fields?.Created_At || new Date().toISOString()
              })) as Member[];
              setAllMembers(transformedMembers);
              recordMetric({
                name: "members.virtualized.loaded",
                value: transformedMembers.length,
                timestamp: Date.now(),
                tags: { source: "api" },
              });
              return;
            }
          }
        } catch (apiError) {
          console.warn("API not available, using mock data:", apiError);
        }

        // Fallback to comprehensive mock data
        const mockMembers = generateMockMembers();
        setAllMembers(mockMembers);

        recordMetric({
          name: "members.virtualized.loaded",
          value: mockMembers.length,
          timestamp: Date.now(),
          tags: { source: "mock" },
        });
      } catch (err) {
        console.error("Failed to load members:", err);
        setError(err instanceof Error ? err.message : "Failed to load members");
        recordError({
          error: err as Error,
          context: "members_virtualized_load",
          timestamp: Date.now(),
        });
      } finally {
        setLoading(false);
      }
    };

    loadMembers();
  }, [generateMockMembers, API_BASE_URL, recordMetric, recordError]);

  // Enhanced Japanese text search with wanakana
  const normalizeSearchQuery = useCallback((query: string): string[] => {
    if (!query.trim()) return [];

    const normalized = query.toLowerCase().trim();
    const searches: string[] = [normalized];

    // If input contains romaji, convert to hiragana
    if (wanakana.isRomaji(normalized)) {
      searches.push(wanakana.toHiragana(normalized));
    }

    // If input contains katakana, convert to hiragana
    if (wanakana.isKatakana(normalized)) {
      searches.push(wanakana.toHiragana(normalized));
    }

    // If input contains hiragana, also try katakana
    if (wanakana.isHiragana(normalized)) {
      searches.push(wanakana.toKatakana(normalized));
    }

    return searches;
  }, []);

  // Filter and search members
  const filteredMembers = useMemo(() => {
    let filtered = allMembers;

    // Apply house filter
    if (houseFilter) {
      filtered = filtered.filter((member) => member.house === houseFilter);
    }

    // Apply party filter
    if (partyFilter) {
      filtered = filtered.filter((member) => member.party === partyFilter);
    }

    // Apply search query with Japanese text optimization
    if (searchQuery.trim()) {
      const searchTerms = normalizeSearchQuery(searchQuery);

      filtered = filtered.filter((member) => {
        return searchTerms.some(
          (term) =>
            member.name.toLowerCase().includes(term) ||
            member.name_kana.includes(term) ||
            member.party.toLowerCase().includes(term) ||
            member.constituency.toLowerCase().includes(term),
        );
      });
    }

    return filtered;
  }, [allMembers, houseFilter, partyFilter, searchQuery, normalizeSearchQuery]);

  // TanStack Virtual setup
  const virtualizer = useVirtualizer({
    count: filteredMembers.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 120, // Estimated height of each member card
    overscan: 10, // Render extra items for smooth scrolling
  });

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearchQuery(e.target.value);
    },
    [],
  );

  const handleMemberClick = useCallback(
    (memberId: string) => {
      router.push(`/members/${memberId}`);
    },
    [router],
  );

  const getHouseLabel = (house: string) => {
    return house === "house_of_representatives" ? "衆議院" : "参議院";
  };

  const getPartyColor = (party: string) => {
    switch (party) {
      case "自由民主党":
        return "bg-red-100 text-red-800 border-red-200";
      case "立憲民主党":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "日本維新の会":
        return "bg-orange-100 text-orange-800 border-orange-200";
      case "公明党":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "日本共産党":
        return "bg-red-100 text-red-800 border-red-200";
      case "国民民主党":
        return "bg-green-100 text-green-800 border-green-200";
      case "れいわ新選組":
        return "bg-purple-100 text-purple-800 border-purple-200";
      case "社会民主党":
        return "bg-pink-100 text-pink-800 border-pink-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  // Unique parties for filter dropdown
  const uniqueParties = useMemo(() => {
    const parties = new Set(allMembers.map((m) => m.party));
    return Array.from(parties).sort();
  }, [allMembers]);

  if (loading) {
    return (
      <Layout>
        <div className="max-w-6xl mx-auto py-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
            <div className="h-16 bg-gray-200 rounded mb-6"></div>
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-20 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-6xl mx-auto py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            国会議員一覧
          </h1>
          <p className="text-gray-600">
            {allMembers.length}名の議員が登録されています
            {filteredMembers.length !== allMembers.length &&
              ` (${filteredMembers.length}名が条件に一致)`}
          </p>
        </div>

        {/* Enhanced Search and Filters */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="space-y-4">
            {/* Search with Japanese optimization */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label
                  htmlFor="search"
                  className="block text-sm font-medium text-gray-700"
                >
                  議員名検索
                </label>
                <div className="flex items-center space-x-2 text-xs text-gray-500">
                  <span>日本語・ひらがな・ローマ字対応</span>
                  {searchQuery && wanakana.isRomaji(searchQuery) && (
                    <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded">
                      ローマ字入力: {wanakana.toHiragana(searchQuery)}
                    </span>
                  )}
                </div>
              </div>
              <input
                type="text"
                id="search"
                value={searchQuery}
                onChange={handleSearchChange}
                placeholder="例: tanaka, たなか, 田中"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Filters */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="house"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  院別
                </label>
                <select
                  id="house"
                  value={houseFilter}
                  onChange={(e) => setHouseFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">全て ({allMembers.length}名)</option>
                  <option value="house_of_representatives">
                    衆議院 (
                    {
                      allMembers.filter(
                        (m) => m.house === "house_of_representatives",
                      ).length
                    }
                    名)
                  </option>
                  <option value="house_of_councillors">
                    参議院 (
                    {
                      allMembers.filter(
                        (m) => m.house === "house_of_councillors",
                      ).length
                    }
                    名)
                  </option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="party"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  政党
                </label>
                <select
                  id="party"
                  value={partyFilter}
                  onChange={(e) => setPartyFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">全て</option>
                  {uniqueParties.map((party) => (
                    <option key={party} value={party}>
                      {party} (
                      {allMembers.filter((m) => m.party === party).length}名)
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Search stats */}
            {searchQuery && (
              <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded">
                <div className="flex items-center space-x-4">
                  <span>🔍 検索結果: {filteredMembers.length}名</span>
                  {wanakana.isRomaji(searchQuery) && (
                    <span>
                      📝 ローマ字変換: {searchQuery} →{" "}
                      {wanakana.toHiragana(searchQuery)}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Virtualized Member List */}
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <div className="text-red-800 font-medium mb-2">エラー</div>
            <div className="text-red-700">{error}</div>
          </div>
        ) : (
          <div
            className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
            data-testid="member-list"
          >
            {filteredMembers.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <svg
                  className="w-12 h-12 mx-auto mb-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                  />
                </svg>
                <p>条件に一致する議員が見つかりませんでした</p>
                <p className="text-sm mt-2">検索条件を変更してお試しください</p>
              </div>
            ) : (
              <div
                ref={parentRef}
                className="h-[600px] overflow-auto"
                style={{ contain: "strict" }}
                data-testid="virtual-scroll-container"
              >
                <div
                  style={{
                    height: `${virtualizer.getTotalSize()}px`,
                    width: "100%",
                    position: "relative",
                  }}
                >
                  {virtualizer.getVirtualItems().map((virtualItem) => {
                    const member = filteredMembers[virtualItem.index];
                    return (
                      <div
                        key={virtualItem.key}
                        style={{
                          position: "absolute",
                          top: 0,
                          left: 0,
                          width: "100%",
                          height: `${virtualItem.size}px`,
                          transform: `translateY(${virtualItem.start}px)`,
                        }}
                        className="border-b border-gray-200 last:border-b-0"
                      >
                        <div
                          onClick={() => handleMemberClick(member.id)}
                          className="p-6 hover:bg-gray-50 cursor-pointer transition-colors h-full flex items-center"
                          data-testid="member-card"
                        >
                          <div className="flex-1">
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <h3 className="text-lg font-medium text-gray-900">
                                  {member.name}
                                  <span className="text-sm font-normal text-gray-600 ml-2">
                                    （{member.name_kana}）
                                  </span>
                                </h3>

                                <div className="flex flex-wrap items-center gap-3 mt-2">
                                  <span className="text-sm text-gray-600">
                                    {getHouseLabel(member.house)}
                                  </span>

                                  <span
                                    className={`px-2 py-1 text-xs rounded-full border ${getPartyColor(member.party)}`}
                                  >
                                    {member.party}
                                  </span>

                                  <span className="text-sm text-gray-600">
                                    {member.constituency}
                                  </span>

                                  <span className="text-sm text-gray-600">
                                    {member.terms_served}期
                                  </span>
                                </div>
                              </div>

                              <div className="flex-shrink-0 ml-4">
                                <svg
                                  className="w-5 h-5 text-gray-400"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M9 5l7 7-7 7"
                                  />
                                </svg>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Virtual scrolling indicator */}
            {filteredMembers.length > 0 && (
              <div className="bg-gray-50 px-6 py-3 border-t border-gray-200 text-sm text-gray-600 text-center">
                📜 仮想スクロール: {filteredMembers.length}名中{" "}
                {virtualizer.getVirtualItems().length}名を表示中
                {filteredMembers.length > 100 && (
                  <span className="ml-2 text-xs">⚡ 高速レンダリング対応</span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default MembersPage;
