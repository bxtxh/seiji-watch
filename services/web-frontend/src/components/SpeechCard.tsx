import React from "react";
import { Speech } from "@/types";

interface SpeechCardProps {
  speech: Speech;
  showSummary?: boolean;
  showTopics?: boolean;
  onTopicClick?: (topic: string) => void;
}

export default function SpeechCard({
  speech,
  showSummary = true,
  showTopics = true,
  onTopicClick,
}: SpeechCardProps) {
  const formatDuration = (seconds?: number) => {
    if (!seconds) return "";
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
  };

  const truncateText = (text: string, maxLength: number = 200) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + "...";
  };

  return (
    <div className="card hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center space-x-3">
            <h3 className="font-semibold text-gray-900">
              {speech.speaker_name || "不明"}
            </h3>
            {speech.speaker_title && (
              <span className="text-sm text-gray-600 bg-gray-100 px-2 py-1 rounded">
                {speech.speaker_title}
              </span>
            )}
            {speech.speech_type && (
              <span
                className={`text-xs px-2 py-1 rounded-full ${
                  speech.speech_type === "質問"
                    ? "bg-blue-100 text-blue-800"
                    : speech.speech_type === "答弁"
                      ? "bg-green-100 text-green-800"
                      : "bg-yellow-100 text-yellow-800"
                }`}
              >
                {speech.speech_type}
              </span>
            )}
          </div>

          {/* Metadata */}
          <div className="flex items-center space-x-4 mt-1 text-sm text-gray-500">
            <span>順番: {speech.speech_order}</span>
            {speech.duration_seconds && (
              <span>時間: {formatDuration(speech.duration_seconds)}</span>
            )}
            {speech.word_count && <span>{speech.word_count}文字</span>}
          </div>
        </div>
      </div>

      {/* AI-Generated Summary */}
      {showSummary && speech.summary && (
        <div className="mb-3 p-3 bg-blue-50 rounded-lg border-l-4 border-blue-400">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg
                className="h-4 w-4 text-blue-400 mt-0.5"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-2">
              <p className="text-sm font-medium text-blue-800 mb-1">AI要約</p>
              <p className="text-sm text-blue-700">{speech.summary}</p>
            </div>
          </div>
        </div>
      )}

      {/* Topics/Tags */}
      {showTopics && speech.topics && speech.topics.length > 0 && (
        <div className="mb-3">
          <p className="text-sm font-medium text-gray-700 mb-2">トピック</p>
          <div className="flex flex-wrap gap-2">
            {speech.topics.map((topic, index) => (
              <button
                key={index}
                onClick={() => onTopicClick?.(topic)}
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors ${
                  onTopicClick
                    ? "bg-green-100 text-green-800 hover:bg-green-200 cursor-pointer"
                    : "bg-green-100 text-green-800"
                }`}
                disabled={!onTopicClick}
              >
                {topic}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Original Text */}
      <div className="border-t pt-3">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-medium text-gray-700">発言内容</p>
          {speech.confidence_score && (
            <span className="text-xs text-gray-500">
              音声認識精度: {speech.confidence_score}
            </span>
          )}
        </div>
        <p className="text-sm text-gray-900 leading-relaxed">
          {truncateText(speech.original_text)}
        </p>

        {speech.original_text.length > 200 && (
          <button className="text-sm text-blue-600 hover:text-blue-800 mt-2 font-medium">
            続きを読む
          </button>
        )}
      </div>

      {/* Processing Status */}
      {!speech.is_processed && (
        <div className="mt-3 p-2 bg-yellow-50 rounded border-l-4 border-yellow-400">
          <p className="text-xs text-yellow-800">
            AI処理待ち - 要約とトピック抽出が完了していません
          </p>
        </div>
      )}

      {/* Stance/Sentiment (if available) */}
      {(speech.stance || speech.sentiment) && (
        <div className="mt-3 flex items-center space-x-4 text-sm">
          {speech.stance && (
            <span
              className={`px-2 py-1 rounded text-xs ${
                speech.stance === "賛成"
                  ? "bg-green-100 text-green-800"
                  : speech.stance === "反対"
                    ? "bg-red-100 text-red-800"
                    : "bg-gray-100 text-gray-800"
              }`}
            >
              立場: {speech.stance}
            </span>
          )}
          {speech.sentiment && (
            <span
              className={`px-2 py-1 rounded text-xs ${
                speech.sentiment === "positive"
                  ? "bg-blue-100 text-blue-800"
                  : speech.sentiment === "negative"
                    ? "bg-orange-100 text-orange-800"
                    : "bg-gray-100 text-gray-800"
              }`}
            >
              感情:{" "}
              {speech.sentiment === "positive"
                ? "ポジティブ"
                : speech.sentiment === "negative"
                  ? "ネガティブ"
                  : "中立"}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
