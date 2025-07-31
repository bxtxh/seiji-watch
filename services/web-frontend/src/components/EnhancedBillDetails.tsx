import React, { useState } from "react";
import { Bill } from "@/types";
import {
  DocumentTextIcon,
  InformationCircleIcon,
  SparklesIcon,
  ListBulletIcon,
  ScaleIcon,
  CalendarIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from "@heroicons/react/24/outline";

interface EnhancedBillDetailsProps {
  bill: Bill;
}

const EnhancedBillDetails: React.FC<EnhancedBillDetailsProps> = ({ bill }) => {
  const [expandedSections, setExpandedSections] = useState<
    Record<string, boolean>
  >({
    outline: false,
    background: false,
    effects: false,
    provisions: false,
    laws: false,
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("ja-JP", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    } catch {
      return dateString;
    }
  };

  const CollapsibleSection: React.FC<{
    id: string;
    title: string;
    icon: React.ReactNode;
    content: string | string[];
    isArray?: boolean;
    emptyMessage?: string;
  }> = ({
    id,
    title,
    icon,
    content,
    isArray = false,
    emptyMessage = "情報がありません",
  }) => {
    const hasContent = isArray
      ? Array.isArray(content) && content.length > 0
      : content;
    const isExpanded = expandedSections[id];

    if (!hasContent) {
      return (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-center text-gray-500">
            {icon}
            <span className="ml-2 font-medium">{title}</span>
          </div>
          <p className="text-sm text-gray-400 mt-2">{emptyMessage}</p>
        </div>
      );
    }

    return (
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          onClick={() => toggleSection(id)}
          className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between text-left transition-colors"
          aria-expanded={isExpanded}
          aria-controls={`${id}-content`}
        >
          <div className="flex items-center">
            {icon}
            <span className="ml-2 font-medium text-gray-900">{title}</span>
          </div>
          {isExpanded ? (
            <ChevronUpIcon className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronDownIcon className="w-5 h-5 text-gray-500" />
          )}
        </button>

        {isExpanded && (
          <div id={`${id}-content`} className="p-4 bg-white">
            {isArray ? (
              <ul className="space-y-2" role="list">
                {(content as string[]).map((item, index) => (
                  <li key={index} className="flex items-start" role="listitem">
                    <span
                      className="inline-block w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"
                      aria-hidden="true"
                    />
                    <span className="text-gray-700 japanese-text leading-relaxed">
                      {item}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="prose prose-sm max-w-none">
                <p className="text-gray-700 japanese-text leading-relaxed whitespace-pre-wrap">
                  {content as string}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <section className="space-y-6" aria-labelledby="enhanced-bill-details">
      <header>
        <h3
          id="enhanced-bill-details"
          className="text-lg font-semibold text-gray-900 flex items-center"
        >
          <DocumentTextIcon className="w-5 h-5 mr-2" />
          詳細情報
        </h3>
      </header>

      <div className="space-y-4">
        {/* Bill Outline */}
        <CollapsibleSection
          id="outline"
          title="法案要旨"
          icon={<DocumentTextIcon className="w-5 h-5 text-blue-600" />}
          content={bill.bill_outline || ""}
          emptyMessage="法案要旨の詳細情報はまだ取得されていません"
        />

        {/* Background Context */}
        <CollapsibleSection
          id="background"
          title="提出背景・経緯"
          icon={<InformationCircleIcon className="w-5 h-5 text-purple-600" />}
          content={bill.background_context || ""}
          emptyMessage="提出背景・経緯の情報はまだ取得されていません"
        />

        {/* Expected Effects */}
        <CollapsibleSection
          id="effects"
          title="期待される効果"
          icon={<SparklesIcon className="w-5 h-5 text-green-600" />}
          content={bill.expected_effects || ""}
          emptyMessage="期待される効果の情報はまだ取得されていません"
        />

        {/* Key Provisions */}
        <CollapsibleSection
          id="provisions"
          title="主要条項"
          icon={<ListBulletIcon className="w-5 h-5 text-orange-600" />}
          content={bill.key_provisions || []}
          isArray={true}
          emptyMessage="主要条項の情報はまだ取得されていません"
        />

        {/* Related Laws */}
        <CollapsibleSection
          id="laws"
          title="関連法律"
          icon={<ScaleIcon className="w-5 h-5 text-red-600" />}
          content={bill.related_laws || []}
          isArray={true}
          emptyMessage="関連法律の情報はまだ取得されていません"
        />

        {/* Implementation Date */}
        {bill.implementation_date && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center">
              <CalendarIcon className="w-5 h-5 text-blue-600" />
              <span className="ml-2 font-medium text-blue-900">施行予定日</span>
            </div>
            <div className="mt-2 ml-7">
              <time
                dateTime={bill.implementation_date}
                className="text-blue-800 font-medium"
              >
                {formatDate(bill.implementation_date)}
              </time>
            </div>
          </div>
        )}

        {/* Inter-house Status */}
        {bill.inter_house_status && (
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <div className="flex items-center">
              <InformationCircleIcon className="w-5 h-5 text-purple-600" />
              <span className="ml-2 font-medium text-purple-900">
                両院間の状況
              </span>
            </div>
            <div className="mt-2 ml-7">
              <span className="text-purple-800">{bill.inter_house_status}</span>
            </div>
          </div>
        )}
      </div>

      {/* Data Completeness Notice */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start">
          <InformationCircleIcon className="w-5 h-5 text-yellow-600 mt-0.5" />
          <div className="ml-2">
            <h4 className="text-sm font-medium text-yellow-900">
              情報について
            </h4>
            <p className="text-sm text-yellow-800 mt-1">
              詳細情報は段階的に取得・更新されます。最新の情報については、
              <a
                href={bill.diet_url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-yellow-900"
              >
                国会ウェブサイト
              </a>
              をご確認ください。
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default EnhancedBillDetails;
