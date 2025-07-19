/**
 * Issue Extraction Panel Component
 * Interface for extracting policy issues from bill data using the enhanced dual-level system
 */

import React, { useState, useCallback } from 'react';
import { 
  PlusIcon,
  DocumentArrowUpIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';
import { useIssueExtraction } from '../../hooks/useEnhancedIssues';

export interface BillData {
  bill_id: string;
  bill_title: string;
  bill_outline: string;
  background_context?: string;
  expected_effects?: string;
  key_provisions?: string[];
  submitter?: string;
  category?: string;
}

export interface IssueExtractionPanelProps {
  onExtractionComplete?: (results: any) => void;
  onError?: (error: string) => void;
  disabled?: boolean;
  className?: string;
}

export const IssueExtractionPanel: React.FC<IssueExtractionPanelProps> = ({
  onExtractionComplete,
  onError,
  disabled = false,
  className = ''
}) => {
  const [showForm, setShowForm] = useState(false);
  const [billData, setBillData] = useState<BillData>({
    bill_id: '',
    bill_title: '',
    bill_outline: '',
    background_context: '',
    expected_effects: '',
    key_provisions: [''],
    submitter: '',
    category: ''
  });

  const {
    extracting,
    extractionResults,
    error: extractionError,
    extractSingle,
    clearResults,
    clearError
  } = useIssueExtraction();

  const handleInputChange = useCallback((field: keyof BillData, value: string | string[]) => {
    setBillData(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleProvisionChange = useCallback((index: number, value: string) => {
    setBillData(prev => ({
      ...prev,
      key_provisions: prev.key_provisions?.map((provision, i) => 
        i === index ? value : provision
      ) || []
    }));
  }, []);

  const addProvision = useCallback(() => {
    setBillData(prev => ({
      ...prev,
      key_provisions: [...(prev.key_provisions || []), '']
    }));
  }, []);

  const removeProvision = useCallback((index: number) => {
    setBillData(prev => ({
      ...prev,
      key_provisions: prev.key_provisions?.filter((_, i) => i !== index) || []
    }));
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!billData.bill_id || !billData.bill_title || !billData.bill_outline) {
      onError?.('必須項目を入力してください');
      return;
    }

    try {
      clearError();
      
      // Filter out empty provisions
      const filteredBillData = {
        ...billData,
        key_provisions: billData.key_provisions?.filter(p => p.trim()) || []
      };

      const results = await extractSingle(filteredBillData);
      
      onExtractionComplete?.(results);
      setShowForm(false);
      
      // Reset form
      setBillData({
        bill_id: '',
        bill_title: '',
        bill_outline: '',
        background_context: '',
        expected_effects: '',
        key_provisions: [''],
        submitter: '',
        category: ''
      });
      
    } catch (err) {
      onError?.(err instanceof Error ? err.message : '抽出に失敗しました');
    }
  }, [billData, extractSingle, onExtractionComplete, onError, clearError]);

  const handleCancel = useCallback(() => {
    setShowForm(false);
    clearResults();
    clearError();
  }, [clearResults, clearError]);

  const getExtractionStatusIcon = () => {
    if (extracting) return <ClockIcon className="w-5 h-5 text-blue-500 animate-spin" />;
    if (extractionError) return <XCircleIcon className="w-5 h-5 text-red-500" />;
    if (extractionResults?.success) return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
    return <SparklesIcon className="w-5 h-5 text-purple-500" />;
  };

  return (
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getExtractionStatusIcon()}
            <h3 className="text-lg font-medium text-gray-900">
              政策課題抽出
            </h3>
          </div>
          
          {!showForm && (
            <button
              onClick={() => setShowForm(true)}
              disabled={disabled || extracting}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              <PlusIcon className="w-4 h-4 mr-2" />
              法案から抽出
            </button>
          )}
        </div>
        
        <p className="mt-1 text-sm text-gray-600">
          法案データから高校生向けと一般読者向けの政策課題を自動抽出します
        </p>
      </div>

      {/* Extraction Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Required Fields */}
          <div className="grid grid-cols-1 gap-6">
            {/* Bill ID */}
            <div>
              <label htmlFor="bill_id" className="block text-sm font-medium text-gray-700">
                法案ID <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="bill_id"
                value={billData.bill_id}
                onChange={(e) => handleInputChange('bill_id', e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="例: bill_217_001"
                required
              />
            </div>

            {/* Bill Title */}
            <div>
              <label htmlFor="bill_title" className="block text-sm font-medium text-gray-700">
                法案タイトル <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="bill_title"
                value={billData.bill_title}
                onChange={(e) => handleInputChange('bill_title', e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="例: 介護保険制度改正法案"
                required
              />
            </div>

            {/* Bill Outline */}
            <div>
              <label htmlFor="bill_outline" className="block text-sm font-medium text-gray-700">
                法案概要 <span className="text-red-500">*</span>
              </label>
              <textarea
                id="bill_outline"
                rows={4}
                value={billData.bill_outline}
                onChange={(e) => handleInputChange('bill_outline', e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                placeholder="法案の概要を記述してください..."
                required
              />
            </div>
          </div>

          {/* Optional Fields */}
          <div className="border-t border-gray-200 pt-6">
            <h4 className="text-sm font-medium text-gray-900 mb-4">追加情報（任意）</h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Background Context */}
              <div>
                <label htmlFor="background_context" className="block text-sm font-medium text-gray-700">
                  背景・経緯
                </label>
                <textarea
                  id="background_context"
                  rows={3}
                  value={billData.background_context}
                  onChange={(e) => handleInputChange('background_context', e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="法案提出の背景や経緯..."
                />
              </div>

              {/* Expected Effects */}
              <div>
                <label htmlFor="expected_effects" className="block text-sm font-medium text-gray-700">
                  期待される効果
                </label>
                <textarea
                  id="expected_effects"
                  rows={3}
                  value={billData.expected_effects}
                  onChange={(e) => handleInputChange('expected_effects', e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="法案実施により期待される効果..."
                />
              </div>

              {/* Submitter */}
              <div>
                <label htmlFor="submitter" className="block text-sm font-medium text-gray-700">
                  提出者
                </label>
                <input
                  type="text"
                  id="submitter"
                  value={billData.submitter}
                  onChange={(e) => handleInputChange('submitter', e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="例: 厚生労働省"
                />
              </div>

              {/* Category */}
              <div>
                <label htmlFor="category" className="block text-sm font-medium text-gray-700">
                  カテゴリ
                </label>
                <select
                  id="category"
                  value={billData.category}
                  onChange={(e) => handleInputChange('category', e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">選択してください</option>
                  <option value="社会保障">社会保障</option>
                  <option value="経済・産業">経済・産業</option>
                  <option value="環境">環境</option>
                  <option value="教育">教育</option>
                  <option value="外交・防衛">外交・防衛</option>
                  <option value="司法・治安">司法・治安</option>
                  <option value="行政改革">行政改革</option>
                  <option value="その他">その他</option>
                </select>
              </div>
            </div>
          </div>

          {/* Key Provisions */}
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center justify-between mb-4">
              <label className="block text-sm font-medium text-gray-700">
                主要条項
              </label>
              <button
                type="button"
                onClick={addProvision}
                className="inline-flex items-center px-3 py-1 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50"
              >
                <PlusIcon className="w-4 h-4 mr-1" />
                条項を追加
              </button>
            </div>
            
            <div className="space-y-3">
              {billData.key_provisions?.map((provision, index) => (
                <div key={index} className="flex items-center space-x-3">
                  <input
                    type="text"
                    value={provision}
                    onChange={(e) => handleProvisionChange(index, e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder={`条項 ${index + 1}`}
                  />
                  {billData.key_provisions!.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeProvision(index)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <XCircleIcon className="w-5 h-5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-end space-x-3 pt-6 border-t border-gray-200">
            <button
              type="button"
              onClick={handleCancel}
              disabled={extracting}
              className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={extracting}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {extracting ? (
                <>
                  <ClockIcon className="w-4 h-4 mr-2 animate-spin" />
                  抽出中...
                </>
              ) : (
                <>
                  <DocumentArrowUpIcon className="w-4 h-4 mr-2" />
                  政策課題を抽出
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* Extraction Results */}
      {extractionResults && (
        <div className="border-t border-gray-200 p-6">
          <div className="flex items-center space-x-2 mb-4">
            <CheckCircleIcon className="w-5 h-5 text-green-500" />
            <h4 className="text-sm font-medium text-gray-900">抽出完了</h4>
          </div>
          
          <div className="bg-green-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-green-800">
                {extractionResults.created_issues?.length || 0}件の政策課題を抽出しました
              </span>
              <div className="flex items-center space-x-4 text-xs text-green-700">
                <span>抽出時間: {extractionResults.extraction_metadata?.extraction_time_ms}ms</span>
                <span>品質スコア: {Math.round((extractionResults.extraction_metadata?.total_quality_score || 0) * 100)}%</span>
              </div>
            </div>
            
            {extractionResults.created_issues?.map((issue: any, index: number) => (
              <div key={index} className="bg-white rounded border p-3 mb-2 last:mb-0">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <div className="text-xs font-medium text-blue-600 mb-1">レベル1（高校生向け）</div>
                    <div className="text-sm text-gray-900">{issue.label_lv1}</div>
                  </div>
                  <div>
                    <div className="text-xs font-medium text-green-600 mb-1">レベル2（一般読者向け）</div>
                    <div className="text-sm text-gray-900">{issue.label_lv2}</div>
                  </div>
                </div>
                <div className="mt-3 flex items-center space-x-4 text-xs text-gray-500">
                  <span className="flex items-center">
                    <ChartBarIcon className="w-3 h-3 mr-1" />
                    信頼度: {Math.round(issue.confidence * 100)}%
                  </span>
                  <span>レコードID: {issue.lv1_record_id} / {issue.lv2_record_id}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Display */}
      {extractionError && (
        <div className="border-t border-gray-200 p-6">
          <div className="flex items-center space-x-2 mb-3">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-500" />
            <h4 className="text-sm font-medium text-red-800">抽出エラー</h4>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-md p-3">
            <p className="text-sm text-red-700">{extractionError}</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default IssueExtractionPanel;