import React from "react";
import { CommitteeAssignment } from "@/types";
import {
  BuildingOffice2Icon,
  CalendarIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from "@heroicons/react/24/outline";
import { CheckCircleIcon as CheckCircleIconSolid } from "@heroicons/react/24/solid";

interface CommitteeAssignmentsProps {
  assignments: CommitteeAssignment[];
  compact?: boolean;
}

const CommitteeAssignments: React.FC<CommitteeAssignmentsProps> = ({
  assignments,
  compact = false,
}) => {
  const getStatusIcon = (status: CommitteeAssignment["status"]) => {
    switch (status) {
      case "completed":
        return <CheckCircleIconSolid className="w-5 h-5 text-green-500" />;
      case "in_progress":
        return <ClockIcon className="w-5 h-5 text-blue-500" />;
      case "pending":
        return <ExclamationCircleIcon className="w-5 h-5 text-yellow-500" />;
      default:
        return <ClockIcon className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusLabel = (status: CommitteeAssignment["status"]) => {
    switch (status) {
      case "completed":
        return "審議完了";
      case "in_progress":
        return "審議中";
      case "pending":
        return "付託済み";
      default:
        return "不明";
    }
  };

  const getStatusBadgeClass = (status: CommitteeAssignment["status"]) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800";
      case "in_progress":
        return "bg-blue-100 text-blue-800";
      case "pending":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getHouseBadgeClass = (house: CommitteeAssignment["house"]) => {
    return house === "衆議院" 
      ? "bg-purple-100 text-purple-800" 
      : "bg-indigo-100 text-indigo-800";
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("ja-JP", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateString;
    }
  };

  if (assignments.length === 0) {
    return (
      <div className="text-center py-8">
        <BuildingOffice2Icon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-4 text-sm font-medium text-gray-900">
          委員会付託情報なし
        </h3>
        <p className="mt-2 text-sm text-gray-600">
          この法案の委員会付託情報はまだ取得されていません。
        </p>
      </div>
    );
  }

  if (compact) {
    return (
      <div className="space-y-2">
        {assignments.map((assignment, index) => (
          <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
              {getStatusIcon(assignment.status)}
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-medium text-gray-900">
                    {assignment.committee_name}
                  </span>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getHouseBadgeClass(assignment.house)}`}>
                    {assignment.house}
                  </span>
                </div>
                <div className="text-sm text-gray-600">
                  {formatDate(assignment.assignment_date)}
                </div>
              </div>
            </div>
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusBadgeClass(assignment.status)}`}>
              {getStatusLabel(assignment.status)}
            </span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <section className="space-y-6" aria-labelledby="committee-assignments-heading">
      <header className="flex items-center justify-between">
        <h3 id="committee-assignments-heading" className="text-lg font-semibold text-gray-900 flex items-center">
          <BuildingOffice2Icon className="w-5 h-5 mr-2" />
          委員会付託状況
          <span className="ml-2 bg-gray-200 text-gray-700 px-2 py-1 rounded-full text-sm">
            {assignments.length}件
          </span>
        </h3>
      </header>

      <div className="space-y-4" role="list" aria-label="委員会付託一覧">
        {assignments.map((assignment, index) => (
          <article
            key={index}
            className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
            role="listitem"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0 mt-1">
                  {getStatusIcon(assignment.status)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-3 mb-2">
                    <h4 className="text-base font-semibold text-gray-900">
                      {assignment.committee_name}
                    </h4>
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getHouseBadgeClass(assignment.house)}`}>
                      {assignment.house}
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-4 text-sm text-gray-600">
                    <div className="flex items-center">
                      <CalendarIcon className="w-4 h-4 mr-1" />
                      <time dateTime={assignment.assignment_date}>
                        付託日: {formatDate(assignment.assignment_date)}
                      </time>
                    </div>
                  </div>

                  {/* Status description */}
                  <div className="mt-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-600">状況:</span>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusBadgeClass(assignment.status)}`}>
                        {getStatusLabel(assignment.status)}
                      </span>
                    </div>
                    
                    {assignment.status === "in_progress" && (
                      <p className="text-sm text-blue-700 mt-2">
                        現在この委員会で審議が行われています
                      </p>
                    )}
                    
                    {assignment.status === "completed" && (
                      <p className="text-sm text-green-700 mt-2">
                        委員会での審議が完了しました
                      </p>
                    )}
                    
                    {assignment.status === "pending" && (
                      <p className="text-sm text-yellow-700 mt-2">
                        委員会への付託が完了し、審議開始を待っています
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>

      {/* Summary */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-700 mb-2">付託状況サマリー</h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-lg font-semibold text-yellow-600">
              {assignments.filter(a => a.status === "pending").length}
            </div>
            <div className="text-sm text-gray-600">付託済み</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-blue-600">
              {assignments.filter(a => a.status === "in_progress").length}
            </div>
            <div className="text-sm text-gray-600">審議中</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-green-600">
              {assignments.filter(a => a.status === "completed").length}
            </div>
            <div className="text-sm text-gray-600">完了</div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default CommitteeAssignments;