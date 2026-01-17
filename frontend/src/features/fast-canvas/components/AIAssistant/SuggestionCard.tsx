import React from 'react';
import { AISuggestion } from '../../types';
import { Check, X, AlertTriangle, Sparkles, Brain, FileCheck, BookOpen, Palette } from 'lucide-react';
import './SuggestionCard.css';

interface SuggestionCardProps {
    suggestion: AISuggestion;
    onApply: (suggestion: AISuggestion) => void;
    onDismiss: (suggestionId: string) => void;
}

const TYPE_CONFIG = {
    proofread: { label: '纠错', color: '#ef4444', icon: AlertTriangle },
    polish: { label: '润色', color: '#3b82f6', icon: Sparkles },
    logic: { label: '逻辑', color: '#f59e0b', icon: Brain },
    format: { label: '格式', color: '#8b5cf6', icon: FileCheck },
    terminology: { label: '术语', color: '#10b981', icon: BookOpen },
    style: { label: '风格', color: '#6366f1', icon: Palette }
};

const SEVERITY_CONFIG = {
    high: { label: '严重', bgColor: '#fee2e2', textColor: '#991b1b' },
    medium: { label: '建议', bgColor: '#fef3c7', textColor: '#92400e' },
    low: { label: '提示', bgColor: '#dbeafe', textColor: '#1e40af' }
};

export const SuggestionCard: React.FC<SuggestionCardProps> = ({
    suggestion,
    onApply,
    onDismiss
}) => {
    const typeConfig = TYPE_CONFIG[suggestion.type] || TYPE_CONFIG.proofread;
    const severityConfig = SEVERITY_CONFIG[suggestion.severity];
    const Icon = typeConfig.icon;

    return (
        <div className="suggestion-card" style={{ borderLeftColor: typeConfig.color }}>
            <div className="suggestion-header">
                <div className="suggestion-type" style={{ color: typeConfig.color }}>
                    <Icon size={14} />
                    <span>{typeConfig.label}</span>
                </div>
                <div
                    className="suggestion-severity"
                    style={{
                        background: severityConfig.bgColor,
                        color: severityConfig.textColor
                    }}
                >
                    {severityConfig.label}
                </div>
            </div>

            <div className="suggestion-content">
                <div className="suggestion-original">
                    <span className="label">原文:</span>
                    <span className="text">{suggestion.original}</span>
                </div>
                <div className="suggestion-arrow">→</div>
                <div className="suggestion-new">
                    <span className="label">建议:</span>
                    <span className="text">{suggestion.suggestion}</span>
                </div>
            </div>

            {suggestion.reason && (
                <div className="suggestion-reason">
                    💡 {suggestion.reason}
                </div>
            )}

            <div className="suggestion-actions">
                <button
                    className="suggestion-btn apply"
                    onClick={() => onApply(suggestion)}
                    disabled={!suggestion.original}
                    title={!suggestion.original ? "无法自动应用：缺少原文定位" : "采纳建议"}
                >
                    <Check size={14} />
                    <span>采纳</span>
                </button>
                <button
                    className="suggestion-btn dismiss"
                    onClick={() => onDismiss(suggestion.id)}
                >
                    <X size={14} />
                    <span>忽略</span>
                </button>
            </div>
        </div>
    );
};
