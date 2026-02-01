import React, { useState } from 'react';
import { AuditResult, AISuggestion } from '../../types';
import { AlertTriangle, CheckCircle, ChevronDown, ChevronUp, Shield } from 'lucide-react';
import { SuggestionCard } from './SuggestionCard';
import './AuditReportMessage.css';

interface AuditReportMessageProps {
    result: AuditResult;
    onApplySuggestion: (suggestion: AISuggestion) => void;
    onDismissSuggestion: (id: string) => void;
}

export const AuditReportMessage: React.FC<AuditReportMessageProps> = ({
    result,
    onApplySuggestion,
    onDismissSuggestion
}) => {
    const [isExpanded, setIsExpanded] = useState(false);

    // Safe checks
    const safeIssues = Array.isArray(result.issues) ? result.issues : [];
    const safeScore = typeof result.score === 'number' ? result.score : 0;

    // Calculate stats
    const criticalCount = safeIssues.filter(i => i.severity === 'high' || i.severity === 'critical').length;
    const mediumCount = safeIssues.filter(i => i.severity === 'medium').length;

    // Status color
    const getScoreColor = (score: number) => {
        if (score >= 90) return '#10b981'; // Green
        if (score >= 70) return '#f59e0b'; // Orange
        return '#ef4444'; // Red
    };

    return (
        <div className="audit-report-card">
            {/* Header Section */}
            <div className="report-header">
                <div className="score-badge" style={{ borderColor: getScoreColor(safeScore), color: getScoreColor(safeScore) }}>
                    <span className="score-val">{safeScore}</span>
                    <span className="score-unit">分</span>
                </div>
                <div className="report-meta">
                    <h4>审阅润色报告</h4>
                    <div className="meta-stats">
                        {criticalCount > 0 && <span className="stat-tag critical">Found {criticalCount} Critical</span>}
                        <span className="stat-tag">Total {safeIssues.length} Issues</span>
                    </div>
                </div>
            </div>

            {/* Summary Text */}
            <div className="report-summary">
                {result.summary || "审阅完成。"}
            </div>

            {/* Action Area */}
            <div className="report-actions">
                <button
                    className="toggle-details-btn"
                    onClick={() => setIsExpanded(!isExpanded)}
                >
                    {isExpanded ? "收起详情" : "查看详情 & 修复"}
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
            </div>

            {/* Expanded Details (Re-using SuggestionCard logic) */}
            {isExpanded && (
                <div className="report-details-list">
                    {safeIssues.length === 0 ? (
                        <div className="empty-issues">
                            <Shield size={24} color="#10b981" />
                            <p>文档很完美，无需修复！</p>
                        </div>
                    ) : (
                        safeIssues.map(issue => (
                            <SuggestionCard
                                key={issue.id}
                                suggestion={issue}
                                onApply={onApplySuggestion}
                                onDismiss={onDismissSuggestion}
                                compact={true} // Add compact mode to SuggestionCard if needed, or just use default
                            />
                        ))
                    )}
                </div>
            )}
        </div>
    );
};
