import React from 'react';
import { AISuggestion, AuditResult } from '../../types';
import { SuggestionCard } from './SuggestionCard';
import { VirtualScroll } from './VirtualScroll';
import { Shield, CheckCircle, AlertTriangle, PlayCircle, Loader } from 'lucide-react';

interface AuditModeProps {
    auditResult: AuditResult | null;
    isAnalyzing: boolean;
    onRunAudit: (agents?: string[]) => void;
    onApplySuggestion: (suggestion: AISuggestion) => void;
    onDismissSuggestion: (suggestionId: string) => void;
    onSuggestionSelect?: (suggestion: AISuggestion) => void;
}

export const AuditMode: React.FC<AuditModeProps> = ({
    auditResult,
    isAnalyzing,
    onRunAudit,
    onApplySuggestion,
    onDismissSuggestion,
    onSuggestionSelect
}) => {
    // Local state for selected agents
    const [selectedAgents, setSelectedAgents] = React.useState<string[]>(['proofread', 'logic', 'format', 'consistency']);

    const handleToggleAgent = (agent: string) => {
        setSelectedAgents(prev =>
            prev.includes(agent)
                ? prev.filter(a => a !== agent)
                : [...prev, agent]
        );
    };

    const handleRunAudit = () => {
        // Pass selected agents to parent
        // @ts-ignore - Temporary ignore until parent interface is updated
        onRunAudit(selectedAgents);
    };

    if (isAnalyzing) {
        return (
            <div className="assistant-placeholder">
                <Loader size={24} className="spinner" />
                <p>AI专家团队正在会诊中...</p>
                <div className="audit-progress-hint">
                    {selectedAgents.includes('proofread') && <span className="agent-tag">🩹 基础纠错</span>}
                    {selectedAgents.includes('logic') && <span className="agent-tag">🧠 逻辑检查</span>}
                    {selectedAgents.includes('format') && <span className="agent-tag">📏 格式规范</span>}
                    {selectedAgents.includes('consistency') && <span className="agent-tag">⚖️ 一致性</span>}
                    {selectedAgents.includes('terminology') && <span className="agent-tag">📚 术语审校</span>}
                </div>
            </div>
        );
    }

    if (!auditResult) {
        return (
            <div className="assistant-placeholder">
                <Shield size={48} color="#9ca3af" />
                <h3>全文档智能审核</h3>
                <p>请选择要启用的AI专家代理：</p>

                <div className="agent-selector">
                    <label className={`agent-option ${selectedAgents.includes('proofread') ? 'active' : ''}`}>
                        <input
                            type="checkbox"
                            checked={selectedAgents.includes('proofread')}
                            onChange={() => handleToggleAgent('proofread')}
                        />
                        <span className="agent-icon">🩹</span>
                        <div className="agent-info">
                            <strong>基础纠错</strong>
                            <small>错别字/语法/词句</small>
                        </div>
                    </label>

                    <label className={`agent-option ${selectedAgents.includes('logic') ? 'active' : ''}`}>
                        <input
                            type="checkbox"
                            checked={selectedAgents.includes('logic')}
                            onChange={() => handleToggleAgent('logic')}
                        />
                        <span className="agent-icon">🧠</span>
                        <div className="agent-info">
                            <strong>逻辑检查</strong>
                            <small>前后矛盾/时间线</small>
                        </div>
                    </label>

                    <label className={`agent-option ${selectedAgents.includes('format') ? 'active' : ''}`}>
                        <input
                            type="checkbox"
                            checked={selectedAgents.includes('format')}
                            onChange={() => handleToggleAgent('format')}
                        />
                        <span className="agent-icon">📏</span>
                        <div className="agent-info">
                            <strong>格式规范</strong>
                            <small>GB/T 9704标准</small>
                        </div>
                    </label>

                    <label className={`agent-option ${selectedAgents.includes('consistency') ? 'active' : ''}`}>
                        <input
                            type="checkbox"
                            checked={selectedAgents.includes('consistency')}
                            onChange={() => handleToggleAgent('consistency')}
                        />
                        <span className="agent-icon">⚖️</span>
                        <div className="agent-info">
                            <strong>一致性</strong>
                            <small>术语/风格统一</small>
                        </div>
                    </label>

                    <label className={`agent-option ${selectedAgents.includes('terminology') ? 'active' : ''}`}>
                        <input
                            type="checkbox"
                            checked={selectedAgents.includes('terminology')}
                            onChange={() => handleToggleAgent('terminology')}
                        />
                        <span className="agent-icon">📚</span>
                        <div className="agent-info">
                            <strong>术语审校</strong>
                            <small>排除口语/黑话</small>
                        </div>
                    </label>
                </div>

                <button
                    className="btn-primary"
                    onClick={handleRunAudit}
                    disabled={selectedAgents.length === 0}
                >
                    <PlayCircle size={16} />
                    开始审核
                </button>
            </div>
        );
    }

    return (
        <div className="audit-mode-container">
            {/* Header / Summary */}
            <div className={`audit-summary ${auditResult.status.toLowerCase()}`}>
                <div className="audit-score">
                    <div className="score-circle">
                        <span>{auditResult.score}</span>
                        <small>分</small>
                    </div>
                </div>
                <div className="audit-info">
                    <h4>
                        {auditResult.status === 'PASS' && <span className="status-pass"><CheckCircle size={16} /> 审核通过</span>}
                        {auditResult.status === 'WARNING' && <span className="status-warn"><AlertTriangle size={16} /> 发现问题</span>}
                        {auditResult.status === 'FAIL' && <span className="status-fail"><AlertTriangle size={16} /> 审核未通过</span>}
                    </h4>
                    <p>{auditResult.summary || '未发现严重问题'}</p>
                </div>
                <button className="btn-icon" onClick={() => onRunAudit(selectedAgents)} title="重新审核">
                    <PlayCircle size={16} />
                </button>
            </div>

            {/* Issues List with Virtual Scrolling */}
            <div className="audit-issues-list">
                <div className="section-title">
                    <span>待处理项 ({auditResult.issues.length})</span>
                </div>
                {auditResult.issues.length === 0 ? (
                    <div className="audit-empty">
                        <CheckCircle size={32} color="#10b981" />
                        <p>文档看起来很棒！</p>
                    </div>
                ) : auditResult.issues.length > 10 ? (
                    // Use VirtualScroll for long lists (>10 items)
                    <VirtualScroll
                        items={auditResult.issues}
                        itemHeight={120} // Approximate height of SuggestionCard
                        containerHeight={500} // Max height of scrollable area
                        renderItem={(issue) => (
                            <SuggestionCard
                                key={issue.id}
                                suggestion={issue}
                                onApply={onApplySuggestion}
                                onDismiss={onDismissSuggestion}
                                onSelect={onSuggestionSelect}
                            />
                        )}
                    />
                ) : (
                    // Regular rendering for short lists
                    auditResult.issues.map((issue) => (
                        <SuggestionCard
                            key={issue.id}
                            suggestion={issue}
                            onApply={onApplySuggestion}
                            onDismiss={onDismissSuggestion}
                            onSelect={onSuggestionSelect}
                        />
                    ))
                )}
            </div>
        </div>
    );
};
