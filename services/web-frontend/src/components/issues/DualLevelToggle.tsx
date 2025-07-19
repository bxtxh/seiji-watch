/**
 * Dual-Level Toggle Component
 * Allows users to switch between high school (Level 1) and general reader (Level 2) issue views
 */

import React, { useState, useCallback } from "react";
import { ChevronDownIcon, AcademicCapIcon, UserGroupIcon } from "@heroicons/react/24/outline";

export interface DualLevelToggleProps {
  currentLevel: 1 | 2;
  onLevelChange: (level: 1 | 2) => void;
  disabled?: boolean;
  className?: string;
}

export const DualLevelToggle: React.FC<DualLevelToggleProps> = ({
  currentLevel,
  onLevelChange,
  disabled = false,
  className = ""
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleToggle = useCallback(() => {
    if (!disabled) {
      setIsOpen(!isOpen);
    }
  }, [disabled, isOpen]);

  const handleLevelSelect = useCallback((level: 1 | 2) => {
    onLevelChange(level);
    setIsOpen(false);
  }, [onLevelChange]);

  const getLevelInfo = (level: 1 | 2) => {
    return level === 1 
      ? {
          icon: AcademicCapIcon,
          label: "高校生向け",
          description: "わかりやすい表現",
          color: "text-blue-600",
          bgColor: "bg-blue-50",
          borderColor: "border-blue-200"
        }
      : {
          icon: UserGroupIcon,
          label: "一般読者向け",
          description: "詳細な専門用語",
          color: "text-green-600",
          bgColor: "bg-green-50",
          borderColor: "border-green-200"
        };
  };

  const currentInfo = getLevelInfo(currentLevel);
  const otherLevel = currentLevel === 1 ? 2 : 1;
  const otherInfo = getLevelInfo(otherLevel);

  return (
    <div className={`relative inline-block text-left ${className}`}>
      {/* Toggle Button */}
      <button
        type="button"
        onClick={handleToggle}
        disabled={disabled}
        className={`
          inline-flex items-center justify-between w-full px-4 py-3 
          text-sm font-medium rounded-lg border-2 shadow-sm
          transition-all duration-200 ease-in-out
          ${currentInfo.color} ${currentInfo.bgColor} ${currentInfo.borderColor}
          ${disabled 
            ? "opacity-50 cursor-not-allowed" 
            : "hover:shadow-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          }
          min-w-[200px]
        `}
        aria-haspopup="true"
        aria-expanded={isOpen}
        aria-label={`現在のレベル: ${currentInfo.label}`}
      >
        <div className="flex items-center space-x-3">
          <currentInfo.icon className="w-5 h-5" aria-hidden="true" />
          <div className="text-left">
            <div className="font-semibold">{currentInfo.label}</div>
            <div className="text-xs opacity-75">{currentInfo.description}</div>
          </div>
        </div>
        <ChevronDownIcon 
          className={`w-4 h-4 transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
          aria-hidden="true"
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 z-10 mt-2 w-full bg-white rounded-lg shadow-lg ring-1 ring-black ring-opacity-5">
          <div className="py-1" role="menu" aria-orientation="vertical">
            {/* Current Level (Selected) */}
            <div
              className={`
                px-4 py-3 flex items-center space-x-3 cursor-default
                ${currentInfo.bgColor} ${currentInfo.color}
              `}
              role="menuitem"
            >
              <currentInfo.icon className="w-5 h-5" aria-hidden="true" />
              <div className="flex-1">
                <div className="font-semibold">{currentInfo.label}</div>
                <div className="text-xs opacity-75">{currentInfo.description}</div>
              </div>
              <div className="text-xs font-medium px-2 py-1 rounded bg-white bg-opacity-50">
                選択中
              </div>
            </div>

            {/* Divider */}
            <div className="border-t border-gray-100" />

            {/* Other Level Option */}
            <button
              onClick={() => handleLevelSelect(otherLevel)}
              className={`
                w-full px-4 py-3 flex items-center space-x-3 text-left
                hover:bg-gray-50 transition-colors duration-150
                ${otherInfo.color}
              `}
              role="menuitem"
            >
              <otherInfo.icon className="w-5 h-5" aria-hidden="true" />
              <div className="flex-1">
                <div className="font-semibold">{otherInfo.label}</div>
                <div className="text-xs opacity-75">{otherInfo.description}</div>
              </div>
              <div className="text-xs text-gray-400">
                切り替え
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Click outside to close */}
      {isOpen && (
        <div
          className="fixed inset-0 z-0"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}
    </div>
  );
};

/**
 * Compact version of the toggle for smaller spaces
 */
export const CompactDualLevelToggle: React.FC<DualLevelToggleProps> = ({
  currentLevel,
  onLevelChange,
  disabled = false,
  className = ""
}) => {
  const handleToggle = useCallback(() => {
    if (!disabled) {
      const newLevel = currentLevel === 1 ? 2 : 1;
      onLevelChange(newLevel);
    }
  }, [currentLevel, onLevelChange, disabled]);

  const currentInfo = currentLevel === 1 
    ? { label: "高校生", color: "text-blue-600", bgColor: "bg-blue-100" }
    : { label: "一般", color: "text-green-600", bgColor: "bg-green-100" };

  return (
    <button
      onClick={handleToggle}
      disabled={disabled}
      className={`
        inline-flex items-center px-3 py-2 text-sm font-medium rounded-md
        border border-gray-300 shadow-sm transition-all duration-200
        ${currentInfo.color} ${currentInfo.bgColor}
        ${disabled 
          ? 'opacity-50 cursor-not-allowed' 
          : 'hover:shadow-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
        }
        ${className}
      `}
      aria-label={`レベル切り替え: ${currentInfo.label}向け`}
    >
      <span className="font-semibold">レベル{currentLevel}</span>
      <span className="ml-1 text-xs">({currentInfo.label})</span>
    </button>
  );
};

/**
 * Helper hook for managing dual-level state
 */
export const useDualLevel = (initialLevel: 1 | 2 = 1) => {
  const [level, setLevel] = useState<1 | 2>(initialLevel);

  const toggleLevel = useCallback(() => {
    setLevel(prev => prev === 1 ? 2 : 1);
  }, []);

  const setLevel1 = useCallback(() => setLevel(1), []);
  const setLevel2 = useCallback(() => setLevel(2), []);

  return {
    level,
    setLevel,
    toggleLevel,
    setLevel1,
    setLevel2,
    isLevel1: level === 1,
    isLevel2: level === 2
  };
};

export default DualLevelToggle;