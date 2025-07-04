import { useState, useEffect } from 'react'
import Layout from '../../components/Layout'
import { Issue, IssueTag } from '../../types'

interface IssueWithTags extends Issue {
  tags?: IssueTag[]
}

const IssuesPage = () => {
  const [issues, setIssues] = useState<IssueWithTags[]>([])
  const [issueTags, setIssueTags] = useState<IssueTag[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedStatus, setSelectedStatus] = useState<string>('')

  const categories = [
    '環境・エネルギー',
    '経済・産業', 
    '社会保障・福祉',
    '外交・安全保障',
    '教育・文化',
    '司法・法務',
    '行政・公務員',
    'インフラ・交通',
    'その他'
  ]

  useEffect(() => {
    fetchIssues()
    fetchIssueTags()
  }, [selectedCategory, selectedStatus])

  const fetchIssues = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      if (selectedCategory) params.append('category', selectedCategory)
      if (selectedStatus) params.append('status', selectedStatus)

      const response = await fetch(`/api/issues?${params}`)
      const data = await response.json()
      
      // Transform Airtable response to our format
      const transformedIssues: IssueWithTags[] = data.map((record: any) => ({
        id: record.id,
        title: record.fields?.Title || '',
        description: record.fields?.Description || '',
        priority: record.fields?.Priority || 'medium',
        status: record.fields?.Status || 'active',
        related_bills: record.fields?.Related_Bills || [],
        issue_tags: record.fields?.Issue_Tags || [],
        created_at: record.fields?.Created_At,
        updated_at: record.fields?.Updated_At
      }))
      
      setIssues(transformedIssues)
    } catch (error) {
      console.error('Failed to fetch issues:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchIssueTags = async () => {
    try {
      const response = await fetch('/api/issues/tags/')
      const data = await response.json()
      
      const transformedTags: IssueTag[] = data.map((record: any) => ({
        id: record.id,
        name: record.fields?.Name || '',
        color_code: record.fields?.Color_Code || '#3B82F6',
        category: record.fields?.Category || '',
        description: record.fields?.Description
      }))
      
      setIssueTags(transformedTags)
    } catch (error) {
      console.error('Failed to fetch issue tags:', error)
    }
  }

  const getTagsForIssue = (issue: IssueWithTags): IssueTag[] => {
    if (!issue.issue_tags) return []
    return issueTags.filter(tag => issue.issue_tags!.includes(tag.id))
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-800'
      case 'medium': return 'bg-yellow-100 text-yellow-800'
      case 'low': return 'bg-green-100 text-green-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-blue-100 text-blue-800'
      case 'reviewed': return 'bg-purple-100 text-purple-800'
      case 'archived': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
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

        {/* Filters */}
        <div className="mb-6 flex flex-wrap gap-4">
          <div>
            <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-1">
              カテゴリ
            </label>
            <select
              id="category"
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">すべて</option>
              {categories.map(category => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-1">
              ステータス
            </label>
            <select
              id="status"
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">すべて</option>
              <option value="active">アクティブ</option>
              <option value="reviewed">レビュー済み</option>
              <option value="archived">アーカイブ</option>
            </select>
          </div>
        </div>

        {/* Issues Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {issues.map((issue) => {
            const tags = getTagsForIssue(issue)
            return (
              <div
                key={issue.id}
                className="bg-white rounded-lg shadow border border-gray-200 p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
                    {issue.title}
                  </h3>
                  <div className="flex flex-col gap-1 ml-2">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(issue.priority)}`}>
                      {issue.priority === 'high' ? '高' : issue.priority === 'medium' ? '中' : '低'}
                    </span>
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(issue.status)}`}>
                      {issue.status === 'active' ? 'アクティブ' : issue.status === 'reviewed' ? 'レビュー済み' : 'アーカイブ'}
                    </span>
                  </div>
                </div>

                <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                  {issue.description}
                </p>

                {/* Issue Tags */}
                {tags.length > 0 && (
                  <div className="mb-4">
                    <div className="flex flex-wrap gap-1">
                      {tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag.id}
                          className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium"
                          style={{
                            backgroundColor: tag.color_code + '20',
                            color: tag.color_code
                          }}
                        >
                          {tag.name}
                        </span>
                      ))}
                      {tags.length > 3 && (
                        <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
                          +{tags.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Related Bills Count */}
                <div className="flex justify-between items-center text-sm text-gray-500">
                  <span>
                    関連法案: {issue.related_bills?.length || 0}件
                  </span>
                  {issue.created_at && (
                    <span>
                      {new Date(issue.created_at).toLocaleDateString('ja-JP')}
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* Empty state */}
        {issues.length === 0 && !loading && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg mb-2">イシューが見つかりませんでした</div>
            <p className="text-gray-600">別の条件で検索してみてください</p>
          </div>
        )}
      </div>
    </Layout>
  )
}

export default IssuesPage