import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import Layout from '../../components/Layout'
import IssueSearchFilters from '../../components/IssueSearchFilters'
import IssueListCard from '../../components/IssueListCard'
import { Issue, IssueTag } from '../../types'

const IssuesPage = () => {
  const router = useRouter()
  const [issues, setIssues] = useState<Issue[]>([])
  const [issueTags, setIssueTags] = useState<IssueTag[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedStatus, setSelectedStatus] = useState<string>('')
  const [selectedPriority, setSelectedPriority] = useState<string>('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [sortBy, setSortBy] = useState<string>('updated_desc')

  const categories = [
    '環境・エネルギー',
    '経済・産業', 
    '社会保障',
    '外交・国際',
    '教育・文化',
    '司法・法務',
    '行政改革',
    '国土・交通',
    'その他'
  ]

  useEffect(() => {
    fetchIssues()
    fetchIssueTags()
  }, [selectedCategory, selectedStatus, selectedPriority])

  const fetchIssues = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (selectedCategory) params.append('category', selectedCategory)
      if (selectedStatus) params.append('status', selectedStatus)
      if (selectedPriority) params.append('priority', selectedPriority)
      params.append('limit', '100')  // Get more results

      const response = await fetch(`/api/issues?${params}`)
      const data = await response.json()
      
      if (data.success && data.issues) {
        setIssues(data.issues)
      } else {
        console.error('API response error:', data)
        setIssues([])
      }
    } catch (error) {
      console.error('Failed to fetch issues:', error)
      setIssues([])
    } finally {
      setLoading(false)
    }
  }

  const fetchIssueTags = async () => {
    try {
      const response = await fetch('/api/issues/tags')
      const data = await response.json()
      
      if (data.success && data.tags) {
        setIssueTags(data.tags)
      } else {
        console.error('API response error:', data)
        setIssueTags([])
      }
    } catch (error) {
      console.error('Failed to fetch issue tags:', error)
      setIssueTags([])
    }
  }

  const getTagsForIssue = (issue: Issue): IssueTag[] => {
    if (!issue.issue_tags) return []
    // For now, return the tags directly from the issue since they're already formatted
    return issue.issue_tags
  }


  const handleIssueClick = (issue: Issue) => {
    router.push(`/issues/${issue.id}`)
  }

  // Filter and sort issues
  const filteredAndSortedIssues = issues
    .filter(issue =>
      issue.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      issue.description.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'updated_desc':
          return new Date(b.updated_at || 0).getTime() - new Date(a.updated_at || 0).getTime()
        case 'created_desc':
          return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
        case 'priority_desc':
          const priorityOrder = { high: 3, medium: 2, low: 1 }
          return (priorityOrder[b.priority as keyof typeof priorityOrder] || 0) - 
                 (priorityOrder[a.priority as keyof typeof priorityOrder] || 0)
        case 'title_asc':
          return a.title.localeCompare(b.title, 'ja')
        default:
          return 0
      }
    })

  const handleClearFilters = () => {
    setSelectedCategory('')
    setSelectedStatus('')
    setSelectedPriority('')
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center min-h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            政策イシューボード
          </h1>
          <p className="text-gray-600">
            国会で議論されている政策課題を一覧できます
          </p>
        </div>

        {/* Search and Filters Component */}
        <IssueSearchFilters
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          selectedCategory={selectedCategory}
          setSelectedCategory={setSelectedCategory}
          selectedStatus={selectedStatus}
          setSelectedStatus={setSelectedStatus}
          selectedPriority={selectedPriority}
          setSelectedPriority={setSelectedPriority}
          viewMode={viewMode}
          setViewMode={setViewMode}
          sortBy={sortBy}
          setSortBy={setSortBy}
          categories={categories}
          onClearFilters={handleClearFilters}
        />

        {/* Issues Display */}
        <div className={viewMode === 'grid' ? 'grid gap-6 md:grid-cols-2 lg:grid-cols-3' : 'space-y-4'}>
          {filteredAndSortedIssues.map((issue) => {
            const tags = getTagsForIssue(issue)
            return (
              <IssueListCard
                key={issue.id}
                issue={issue}
                tags={tags}
                viewMode={viewMode}
                onClick={handleIssueClick}
              />
            )
          })}
        </div>

        {/* Empty state */}
        {filteredAndSortedIssues.length === 0 && !loading && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg mb-2">
              {searchQuery ? '検索結果が見つかりませんでした' : 'イシューが見つかりませんでした'}
            </div>
            <p className="text-gray-600">
              {searchQuery ? '別のキーワードで検索してみてください' : '別の条件で検索してみてください'}
            </p>
          </div>
        )}

        {/* Results count */}
        {!loading && filteredAndSortedIssues.length > 0 && (
          <div className="mt-8 text-center text-sm text-gray-500">
            {filteredAndSortedIssues.length}件のイシューを表示中
            {searchQuery && (
              <span className="ml-2">
                (「{searchQuery}」で検索)
              </span>
            )}
          </div>
        )}
      </div>
    </Layout>
  )
}

export default IssuesPage