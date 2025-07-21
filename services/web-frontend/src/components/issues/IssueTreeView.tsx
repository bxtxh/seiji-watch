/**
 * Issue Tree View Component
 * Displays hierarchical relationship between Level 1 and Level 2 issues
 */

import React, { useState, useCallback, useMemo } from 'react';
import { 
  ChevronDownIcon,
  ChevronRightIcon,
  FolderIcon,
  FolderOpenIcon,
  DocumentIcon,
  EyeIcon,
  EyeSlashIcon
} from '@heroicons/react/24/outline';
import { IssueCard, CompactIssueCard, Issue } from './IssueCard';
import { DualLevelToggle } from './DualLevelToggle';

export interface IssueTreeNode {
  record_id: string;
  issue_id: string;
  label_lv1: string;
  label_lv2?: string;
  confidence: number;
  source_bill_id: string;
  quality_score: number;
  status: string;
  created_at: string;
  children: IssueTreeNode[];
}

export interface IssueTreeViewProps {
  treeData: IssueTreeNode[];
  currentLevel: 1 | 2;
  onLevelChange: (level: 1 | 2) => void;
  onStatusChange?: (issueId: string, status: string) => void;
  expandAll?: boolean;
  showCompact?: boolean;
  className?: string;
}

export const IssueTreeView: React.FC<IssueTreeViewProps> = ({
  treeData,
  currentLevel,
  onLevelChange,
  onStatusChange,
  expandAll = false,
  showCompact = false,
  className = ''
}) => {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(
    expandAll ? new Set(treeData.map(node => node.record_id)) : new Set()
  );
  const [selectedIssue, setSelectedIssue] = useState<string | null>(null);

  const handleToggleNode = useCallback((nodeId: string) => {
    setExpandedNodes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(nodeId)) {
        newSet.delete(nodeId);
      } else {
        newSet.add(nodeId);
      }
      return newSet;
    });
  }, []);

  const handleExpandAll = useCallback(() => {
    const allNodeIds = new Set<string>();
    const collectNodeIds = (nodes: IssueTreeNode[]) => {
      nodes.forEach(node => {
        allNodeIds.add(node.record_id);
        if (node.children.length > 0) {
          collectNodeIds(node.children);
        }
      });
    };
    collectNodeIds(treeData);
    setExpandedNodes(allNodeIds);
  }, [treeData]);

  const handleCollapseAll = useCallback(() => {
    setExpandedNodes(new Set());
  }, []);

  const handleToggleDetails = useCallback((issueId: string) => {
    setSelectedIssue(prev => prev === issueId ? null : issueId);
  }, []);

  // Convert tree nodes to Issue format for IssueCard
  const convertToIssue = useCallback((node: IssueTreeNode): Issue => ({
    issue_id: node.issue_id,
    record_id: node.record_id,
    label_lv1: node.label_lv1,
    label_lv2: node.label_lv2,
    confidence: node.confidence,
    quality_score: node.quality_score,
    status: node.status as any,
    source_bill_id: node.source_bill_id,
    created_at: node.created_at,
    level: currentLevel,
    children: node.children.map(convertToIssue)
  }), [currentLevel]);

  const TreeNode: React.FC<{
    node: IssueTreeNode;
    level: number;
    parentExpanded?: boolean;
  }> = ({ node, level, parentExpanded = true }) => {
    const isExpanded = expandedNodes.has(node.record_id);
    const hasChildren = node.children.length > 0;
    const isSelected = selectedIssue === node.issue_id;

    const issueData = convertToIssue(node);

    return (
      <div className={`${!parentExpanded ? 'hidden' : ''}`}>
        <div className="flex items-start space-x-2">
          {/* Indentation */}
          <div className="flex-shrink-0" style={{ marginLeft: `${level * 24}px` }}>
            {hasChildren ? (
              <button
                onClick={() => handleToggleNode(node.record_id)}
                className="flex items-center justify-center w-6 h-6 text-gray-400 hover:text-gray-600 transition-colors duration-150"
                aria-label={isExpanded ? '折りたたむ' : '展開する'}
              >
                {isExpanded ? (
                  <ChevronDownIcon className="w-4 h-4" />
                ) : (
                  <ChevronRightIcon className="w-4 h-4" />
                )}
              </button>
            ) : (
              <div className="w-6 h-6 flex items-center justify-center">
                <div className="w-2 h-2 bg-gray-300 rounded-full" />
              </div>
            )}
          </div>

          {/* Node Icon */}
          <div className="flex-shrink-0 mt-1">
            {hasChildren ? (
              isExpanded ? (
                <FolderOpenIcon className="w-5 h-5 text-blue-500" />
              ) : (
                <FolderIcon className="w-5 h-5 text-blue-500" />
              )
            ) : (
              <DocumentIcon className="w-5 h-5 text-gray-400" />
            )}
          </div>

          {/* Issue Content */}
          <div className="flex-1 min-w-0">
            {showCompact ? (
              <CompactIssueCard
                issue={issueData}
                currentLevel={currentLevel}
                onToggleDetails={handleToggleDetails}
                className="mb-2"
              />
            ) : (
              <IssueCard
                issue={issueData}
                currentLevel={currentLevel}
                showDetails={isSelected}
                onStatusChange={onStatusChange}
                onToggleDetails={handleToggleDetails}
                className="mb-4"
              />
            )}
          </div>
        </div>

        {/* Children */}
        {hasChildren && (
          <div className={`transition-all duration-200 ${isExpanded ? 'opacity-100' : 'opacity-0'}`}>
            {node.children.map((child) => (
              <TreeNode
                key={child.record_id}
                node={child}
                level={level + 1}
                parentExpanded={isExpanded}
              />
            ))}
          </div>
        )}
      </div>
    );
  };

  const treeStats = useMemo(() => {
    let totalNodes = 0;
    let parentNodes = 0;
    let childNodes = 0;

    const countNodes = (nodes: IssueTreeNode[]) => {
      nodes.forEach(node => {
        totalNodes++;
        if (node.children.length > 0) {
          parentNodes++;
          childNodes += node.children.length;
          countNodes(node.children);
        }
      });
    };

    countNodes(treeData);

    return { totalNodes, parentNodes, childNodes };
  }, [treeData]);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h2 className="text-lg font-semibold text-gray-900">
            政策課題ツリー
          </h2>
          
          {/* Tree Stats */}
          <div className="flex items-center space-x-3 text-sm text-gray-600">
            <span>総数: {treeStats.totalNodes}</span>
            <span>親: {treeStats.parentNodes}</span>
            <span>子: {treeStats.childNodes}</span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Level Toggle */}
          <DualLevelToggle
            currentLevel={currentLevel}
            onLevelChange={onLevelChange}
          />

          {/* Tree Controls */}
          <div className="flex items-center space-x-2">
            <button
              onClick={handleExpandAll}
              className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors duration-150"
            >
              <EyeIcon className="w-4 h-4 mr-1" />
              全て展開
            </button>
            <button
              onClick={handleCollapseAll}
              className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors duration-150"
            >
              <EyeSlashIcon className="w-4 h-4 mr-1" />
              全て折りたたみ
            </button>
          </div>
        </div>
      </div>

      {/* Tree Content */}
      <div className="bg-white rounded-lg border shadow-sm">
        {treeData.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <DocumentIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>表示する政策課題がありません</p>
          </div>
        ) : (
          <div className="p-6">
            {treeData.map((node) => (
              <TreeNode
                key={node.record_id}
                node={node}
                level={0}
              />
            ))}
          </div>
        )}
      </div>

      {/* Tree Legend */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-900 mb-3">凡例</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="flex items-center space-x-2">
            <FolderIcon className="w-4 h-4 text-blue-500" />
            <span>レベル1課題（高校生向け）</span>
          </div>
          <div className="flex items-center space-x-2">
            <DocumentIcon className="w-4 h-4 text-gray-400" />
            <span>レベル2課題（一般読者向け）</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-green-100 border border-green-300 rounded" />
            <span>承認済み課題</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-yellow-100 border border-yellow-300 rounded" />
            <span>審査中課題</span>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Hook for managing tree view state
 */
export const useIssueTree = () => {
  const [treeData, setTreeData] = useState<IssueTreeNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTreeData = useCallback(async (status: string = 'approved') => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/issues/tree?status=${status}`);
      if (!response.ok) {
        throw new Error('Failed to load tree data');
      }

      const data = await response.json();
      setTreeData(data.tree || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshTree = useCallback(() => {
    loadTreeData();
  }, [loadTreeData]);

  return {
    treeData,
    loading,
    error,
    loadTreeData,
    refreshTree
  };
};

export default IssueTreeView;