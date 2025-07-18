import React from "react";
import { LegislativeStage, LegislativeMilestone } from "@/types";
import {
  ClockIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  CalendarIcon,
} from "@heroicons/react/24/outline";
import { CheckCircleIcon as CheckCircleIconSolid } from "@heroicons/react/24/solid";

interface LegislativeProgressBarProps {
  stage: LegislativeStage;
  compact?: boolean;
}

const LegislativeProgressBar: React.FC<LegislativeProgressBarProps> = ({
  stage,
  compact = false,
}) => {
  const getStageColor = (stageName: string, completed: boolean) => {
    if (completed) {
      return "bg-green-500 text-white";
    }
    
    if (stageName === stage.current_stage) {
      return "bg-blue-500 text-white";
    }
    
    return "bg-gray-200 text-gray-600";
  };

  const getStageIcon = (milestone: LegislativeMilestone, isCurrentStage: boolean) => {
    if (milestone.completed) {
      return <CheckCircleIconSolid className="w-5 h-5 text-green-500" />;
    }
    
    if (isCurrentStage) {
      return <ClockIcon className="w-5 h-5 text-blue-500" />;
    }
    
    return <div className="w-5 h-5 rounded-full border-2 border-gray-300" />;
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("ja-JP", {
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateString;
    }
  };

  const getProgressPercentage = () => {
    const completedMilestones = stage.milestones.filter(m => m.completed).length;
    return Math.round((completedMilestones / stage.milestones.length) * 100);
  };

  if (compact) {
    return (
      <div className="flex items-center space-x-3" role="progressbar" aria-valuenow={stage.stage_progress} aria-valuemin={0} aria-valuemax={100}>
        <div className="flex-1">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>{stage.current_stage}</span>
            <span>{getProgressPercentage()}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${getProgressPercentage()}%` }}
              aria-label={`進捗: ${getProgressPercentage()}%`}
            />
          </div>
        </div>
        {stage.next_action_date && (
          <div className="flex items-center text-sm text-gray-500">
            <CalendarIcon className="w-4 h-4 mr-1" />
            <span>{formatDate(stage.next_action_date)}</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <section className="space-y-6" aria-labelledby="legislative-progress-heading">
      <header className="flex items-center justify-between">
        <h3 id="legislative-progress-heading" className="text-lg font-semibold text-gray-900 flex items-center">
          <ClockIcon className="w-5 h-5 mr-2" />
          立法進捗
        </h3>
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <span>進捗率:</span>
          <span className="font-semibold text-blue-600">{getProgressPercentage()}%</span>
        </div>
      </header>

      {/* Current Status */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
              <ClockIcon className="w-5 h-5 text-white" />
            </div>
          </div>
          <div className="flex-1">
            <h4 className="text-base font-medium text-blue-900">
              現在のステージ: {stage.current_stage}
            </h4>
            {stage.next_scheduled_action && (
              <p className="text-sm text-blue-700 mt-1">
                次の予定: {stage.next_scheduled_action}
              </p>
            )}
            {stage.next_action_date && (
              <div className="flex items-center mt-2 text-sm text-blue-600">
                <CalendarIcon className="w-4 h-4 mr-1" />
                <time dateTime={stage.next_action_date}>
                  {formatDate(stage.next_action_date)}
                </time>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="relative">
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200" aria-hidden="true" />
        
        <div className="space-y-6" role="list" aria-label="立法進捗のマイルストーン">
          {stage.milestones.map((milestone, index) => {
            const isCurrentStage = milestone.stage === stage.current_stage;
            
            return (
              <div key={index} className="relative flex items-start" role="listitem">
                {/* Timeline dot */}
                <div className="flex-shrink-0 w-12 h-12 flex items-center justify-center relative z-10">
                  {getStageIcon(milestone, isCurrentStage)}
                </div>

                {/* Content */}
                <div className={`flex-1 ml-4 pb-6 ${milestone.completed ? 'opacity-80' : ''}`}>
                  <div className={`p-4 rounded-lg border ${
                    milestone.completed 
                      ? 'bg-green-50 border-green-200' 
                      : isCurrentStage 
                        ? 'bg-blue-50 border-blue-200' 
                        : 'bg-gray-50 border-gray-200'
                  }`}>
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h4 className={`font-medium ${
                          milestone.completed 
                            ? 'text-green-900' 
                            : isCurrentStage 
                              ? 'text-blue-900' 
                              : 'text-gray-900'
                        }`}>
                          {milestone.stage}
                          {milestone.house && (
                            <span className="ml-2 text-sm font-normal text-gray-600">
                              ({milestone.house})
                            </span>
                          )}
                        </h4>
                        <p className={`text-sm mt-1 ${
                          milestone.completed 
                            ? 'text-green-700' 
                            : isCurrentStage 
                              ? 'text-blue-700' 
                              : 'text-gray-600'
                        }`}>
                          {milestone.description}
                        </p>
                        {milestone.date && (
                          <div className="flex items-center mt-2 text-sm text-gray-500">
                            <CalendarIcon className="w-4 h-4 mr-1" />
                            <time dateTime={milestone.date}>
                              {formatDate(milestone.date)}
                            </time>
                          </div>
                        )}
                      </div>
                      
                      {/* Status indicator */}
                      <div className="ml-4 flex-shrink-0">
                        {milestone.completed && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            <CheckCircleIcon className="w-3 h-3 mr-1" />
                            完了
                          </span>
                        )}
                        {isCurrentStage && !milestone.completed && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            <ClockIcon className="w-3 h-3 mr-1" />
                            進行中
                          </span>
                        )}
                        {!milestone.completed && !isCurrentStage && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                            予定
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mt-6">
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>全体進捗</span>
          <span>{getProgressPercentage()}% 完了</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-gradient-to-r from-blue-500 to-green-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${getProgressPercentage()}%` }}
            role="progressbar"
            aria-valuenow={getProgressPercentage()}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`立法進捗: ${getProgressPercentage()}%完了`}
          />
        </div>
      </div>
    </section>
  );
};

export default LegislativeProgressBar;