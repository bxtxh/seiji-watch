import React from 'react'
import { Issue, IssueTag } from '../types'

interface IssueListCardProps {
  issue: Issue
  tags: IssueTag[]
  viewMode: 'grid' | 'list'
  onClick: (issue: Issue) => void
}

const IssueListCard: React.FC<IssueListCardProps> = ({ issue, tags, viewMode, onClick }) => {
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200'
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'low': return 'bg-green-100 text-green-800 border-green-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'reviewed': return 'bg-purple-100 text-purple-800 border-purple-200'
      case 'archived': return 'bg-gray-100 text-gray-800 border-gray-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStageColor = (stage: string) => {
    switch (stage) {
      case '審議前': return 'bg-gray-100 text-gray-800 border-gray-200'
      case '審議中': return 'bg-blue-100 text-blue-800 border-blue-200'
      case '採決待ち': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case '成立': return 'bg-green-100 text-green-800 border-green-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const formatPriority = (priority: string) => {
    switch (priority) {
      case 'high': return '高'
      case 'medium': return '中' 
      case 'low': return '低'
      default: return priority
    }
  }

  const formatStatus = (status: string) => {
    switch (status) {
      case 'active': return 'アクティブ'
      case 'reviewed': return 'レビュー済み'
      case 'archived': return 'アーカイブ'
      default: return status
    }
  }

  if (viewMode === 'grid') {
    return (
      <div
        className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md hover:border-blue-300 transition-all duration-200 cursor-pointer"
        onClick={() => onClick(issue)}
      >
        {/* Header with badges */}
        <div className="flex justify-between items-start mb-3">
          <h3 className="text-lg font-semibold text-gray-900 line-clamp-2 flex-1 mr-3">
            {issue.title}
          </h3>
          <div className="flex flex-col gap-1 flex-shrink-0">
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(issue.priority)}`}>
              {formatPriority(issue.priority)}
            </span>
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(issue.status)}`}>
              {formatStatus(issue.status)}
            </span>
          </div>
        </div>

        {/* Stage Badge */}
        {issue.stage && (
          <div className="mb-3">
            <span className={`inline-flex items-center px-3 py-1 rounded-md text-sm font-medium border ${getStageColor(issue.stage)}`}>
              {issue.stage}
            </span>
          </div>
        )}

        {/* Description */}
        <p className="text-gray-600 text-sm mb-4 line-clamp-3">
          {issue.description}
        </p>

        {/* Tags */}
        {tags.length > 0 && (
          <div className="mb-4">
            <div className="flex flex-wrap gap-1">
              {tags.slice(0, 2).map((tag) => (
                <span
                  key={tag.id}
                  className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium"
                  style={{
                    backgroundColor: tag.color_code + '20',
                    color: tag.color_code,
                    border: `1px solid ${tag.color_code}30`
                  }}
                >
                  {tag.name}
                </span>
              ))}
              {tags.length > 2 && (
                <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">
                  +{tags.length - 2}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-between items-center text-xs text-gray-500 pt-3 border-t border-gray-100">
          <span>関連法案: {issue.related_bills_count || 0}件</span>
          <span>
            {issue.updated_at ? new Date(issue.updated_at).toLocaleDateString('ja-JP') : ''}
          </span>
        </div>
      </div>
    )
  }

  // List View
  return (
    <div
      className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md hover:border-blue-300 transition-all duration-200 cursor-pointer"
      onClick={() => onClick(issue)}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between mb-2">
            <h3 className="text-lg font-semibold text-gray-900 flex-1 mr-4">
              {issue.title}
            </h3>
            <div className="flex items-center gap-2 flex-shrink-0">
              {issue.stage && (
                <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${getStageColor(issue.stage)}`}>
                  {issue.stage}
                </span>
              )}
              <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(issue.priority)}`}>
                {formatPriority(issue.priority)}
              </span>
              <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(issue.status)}`}>
                {formatStatus(issue.status)}
              </span>
            </div>
          </div>

          <p className="text-gray-600 text-sm mb-3 line-clamp-2">
            {issue.description}
          </p>

          <div className="flex items-center justify-between">
            {/* Tags */}
            <div className="flex items-center space-x-2">
              {tags.slice(0, 3).map((tag) => (
                <span
                  key={tag.id}
                  className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium"
                  style={{
                    backgroundColor: tag.color_code + '20',
                    color: tag.color_code,
                    border: `1px solid ${tag.color_code}30`
                  }}
                >
                  {tag.name}
                </span>
              ))}
              {tags.length > 3 && (
                <span className="text-xs text-gray-500">+{tags.length - 3}</span>
              )}
            </div>

            {/* Meta Info */}
            <div className="flex items-center space-x-4 text-xs text-gray-500">
              <span>関連法案: {issue.related_bills_count || 0}件</span>
              <span>
                {issue.updated_at ? new Date(issue.updated_at).toLocaleDateString('ja-JP') : ''}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default IssueListCard