import React from 'react';
import { SuggestionCard } from './SuggestionCard';
import { AISuggestion } from '../../types';
import { Sparkles, Loader } from 'lucide-react';
import './RealtimeMode.css';

interface RealtimeModeProps {
    suggestions: AISuggestion[];
    isAnalyzing: boolean;
    onApplySuggestion: (suggestion: AISuggestion) => void;
    onDismissSuggestion: (suggestionId: string) => void;
    selectedText?: string;
}

export const RealtimeMode: React.FC<RealtimeModeProps> = ({
    suggestions,
    isAnalyzing,
    onApplySuggestion,
    onDismissSuggestion,
    selectedText
}) => {
    if (isAnalyzing) {
        return (
            <div className="realtime-loading">
                <Loader size={20} className="spinner" />
                <p>⚡ AI正在分析中...</p>
                <div className="analyzing-indicators">
                    <span className="indicator">语法检查</span>
                    <span className="indicator">拼写校对</span>
                    <span className="indicator">风格润色</span>
                </div>
            </div>
        );
    }

    if (!isAnalyzing && suggestions.length === 0) {
        return (
            <div className="realtime-empty">
                <Sparkles size={32} color="#10b981" />
                <p>AI实时分析已启用</p>
                <div className="hint-text">
                    <span>💡 停止输入3秒后自动分析</span>
                    <span>📋 分析：语法、错别字、搭配、逻辑</span>
                </div>
            </div>
        );
    }

    return (
        <div className="realtime-suggestions">
            <div className="suggestions-header">
                <Sparkles size={16} color="#3b82f6" />
                <span>实时建议 ({suggestions.length})</span>
            </div>

            <div className="suggestions-list">
                {suggestions.map(suggestion => (
                    <SuggestionCard
                        key={suggestion.id}
                        suggestion={suggestion}
                        onApply={onApplySuggestion}
                        onDismiss={onDismissSuggestion}
                    />
                ))}
            </div>
        </div>
    );
};
