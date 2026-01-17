import React, { useState } from 'react';
import { ShieldCheck, AlertTriangle, CheckCircle, FileText, ChevronRight, XCircle } from 'lucide-react';
import { marked } from 'marked';
import { getAvailableModels, MODEL_DISPLAY_NAMES } from '../../services/ai';

interface AuditIssue {
    severity: 'high' | 'medium' | 'low';
    description: string;
    location: string;
    suggestion: string;
}

interface AuditResult {
    status: 'PASS' | 'FAIL' | 'WARNING';
    issues: AuditIssue[];
    summary: string;
    error?: string;
}

interface AuditPanelProps {
    referenceFiles: string[];
    onRunAudit: (rules: string) => Promise<AuditResult | null>;
    isAuditing: boolean;
    results: AuditResult | null;
    selectedModel: string;
    onModelChange: (model: string) => void;
}

export const AuditPanel: React.FC<AuditPanelProps> = ({ referenceFiles, onRunAudit, isAuditing, results, selectedModel, onModelChange }) => {
    const [rules, setRules] = useState("Check for consistency in dates, amounts, and names.");
    const [expandedIssue, setExpandedIssue] = useState<number | null>(null);
    const [isConfigExpanded, setIsConfigExpanded] = useState(true);
    const availableModels = getAvailableModels();

    // Auto-collapse when results return, auto-expand if cleared
    React.useEffect(() => {
        if (results) {
            setIsConfigExpanded(false);
        } else {
            setIsConfigExpanded(true);
        }
    }, [results]);

    const handleRun = () => {
        if (isAuditing) return;
        onRunAudit(rules);
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'high': return '#ef4444';
            case 'medium': return '#f59e0b';
            case 'low': return '#3b82f6';
            default: return '#6b7280';
        }
    };

    return (
        <div className="audit-panel" style={{ padding: '12px', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Header & Model Selector */}
            <div className="audit-header" style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '6px', margin: 0, fontSize: '15px' }}>
                    <ShieldCheck size={18} color="#0284c7" />
                    <span>智能审核</span>
                </h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {/* Collapsed State Summary */}
                    {!isConfigExpanded && results && (
                        <span
                            onClick={() => setIsConfigExpanded(true)}
                            style={{
                                fontSize: '11px',
                                color: '#0ea5e9',
                                cursor: 'pointer',
                                background: '#e0f2fe',
                                padding: '2px 8px',
                                borderRadius: '10px'
                            }}
                        >
                            显示配置
                        </span>
                    )}
                    <select
                        value={selectedModel}
                        onChange={(e) => onModelChange(e.target.value)}
                        className="model-selector"
                        style={{ width: '90px', padding: '2px', fontSize: '11px', borderRadius: '4px', border: '1px solid #ddd' }}
                    >
                        {availableModels.map(modelKey => (
                            <option key={modelKey} value={modelKey}>
                                {MODEL_DISPLAY_NAMES[modelKey] || modelKey}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Collapsible Config Section */}
            {isConfigExpanded && (
                <div style={{ marginBottom: '12px', flexShrink: 0, borderBottom: '1px solid #eee', paddingBottom: '12px' }}>
                    {/* Reference Files */}
                    <div style={{ marginBottom: '10px' }}>
                        <div style={{ fontSize: '12px', fontWeight: '500', marginBottom: '4px', color: '#555' }}>
                            依据文件 ({referenceFiles.length})
                        </div>
                        {referenceFiles.length === 0 ? (
                            <div style={{ fontSize: '11px', color: '#999', padding: '6px', background: '#f9f9f9', borderRadius: '4px' }}>
                                暂无文件 (请点击上方上传)
                            </div>
                        ) : (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', maxHeight: '60px', overflowY: 'auto' }}>
                                {referenceFiles.map((f, i) => (
                                    <div key={i} style={{ fontSize: '10px', background: '#e0f2fe', color: '#0369a1', padding: '1px 5px', borderRadius: '3px', display: 'flex', alignItems: 'center', maxWidth: '100%' }}>
                                        <FileText size={9} style={{ marginRight: '3px' }} />
                                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Rules */}
                    <div style={{ marginBottom: '10px' }}>
                        <div style={{ fontSize: '12px', fontWeight: '500', marginBottom: '4px', color: '#555' }}>审核规则</div>
                        <textarea
                            value={rules}
                            onChange={(e) => setRules(e.target.value)}
                            className="audit-input"
                            placeholder="输入审核规则..."
                            style={{
                                width: '100%',
                                height: '60px',
                                padding: '6px',
                                fontSize: '11px',
                                border: '1px solid #ddd',
                                borderRadius: '4px',
                                resize: 'none',
                                background: '#fafafa'
                            }}
                        />
                    </div>

                    <button
                        onClick={handleRun}
                        disabled={isAuditing || referenceFiles.length === 0}
                        className="audit-run-btn"
                        style={{
                            width: '100%',
                            padding: '6px',
                            background: isAuditing ? '#94a3b8' : '#0ea5e9',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: isAuditing || referenceFiles.length === 0 ? 'not-allowed' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '6px',
                            fontWeight: '500',
                            fontSize: '12px'
                        }}
                    >
                        {isAuditing ? '审核中...' : '开始审核'}
                    </button>

                    {results && (
                        <div
                            onClick={() => setIsConfigExpanded(false)}
                            style={{ textAlign: 'center', fontSize: '10px', color: '#999', marginTop: '6px', cursor: 'pointer' }}
                        >
                            收起配置 ▲
                        </div>
                    )}
                </div>
            )}

            {/* Results Section - Optimized for Density */}
            <div className="audit-results" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
                {results ? (
                    <>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', position: 'sticky', top: 0, background: '#fff', padding: '4px 0', zIndex: 10 }}>
                            <span style={{ fontSize: '12px', fontWeight: 'bold' }}>审核结果</span>
                            <span style={{
                                fontSize: '10px',
                                padding: '1px 6px',
                                borderRadius: '8px',
                                fontWeight: 'bold',
                                background: results.status === 'PASS' ? '#dcfce7' : results.status === 'FAIL' ? '#fee2e2' : '#fef9c3',
                                color: results.status === 'PASS' ? '#166534' : results.status === 'FAIL' ? '#991b1b' : '#854d0e'
                            }}>
                                {results.status}
                            </span>
                        </div>

                        {results.summary && (
                            <div style={{ fontSize: '11px', lineHeight: '1.4', color: '#444', marginBottom: '10px', background: '#f8fafc', padding: '6px 8px', borderRadius: '4px', border: '1px solid #f1f5f9' }}>
                                {results.summary}
                            </div>
                        )}

                        {results.error && (
                            <div style={{ fontSize: '11px', color: '#dc2626', marginBottom: '10px' }}>
                                Error: {results.error}
                            </div>
                        )}

                        <div className="issues-list" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {results.issues.map((issue, idx) => (
                                <div key={idx} className="audit-issue" style={{ border: '1px solid #eee', borderRadius: '4px', overflow: 'hidden' }}>
                                    <div
                                        onClick={() => setExpandedIssue(expandedIssue === idx ? null : idx)}
                                        style={{
                                            padding: '8px', // Reduced padding
                                            background: '#fff',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'flex-start',
                                            gap: '8px'
                                        }}
                                    >
                                        <AlertTriangle size={12} color={getSeverityColor(issue.severity)} style={{ marginTop: '2px', flexShrink: 0 }} />
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <div style={{
                                                fontSize: '11px', // Smaller font
                                                fontWeight: '500',
                                                color: '#333',
                                                lineHeight: '1.4',
                                                marginBottom: '2px'
                                            }}>
                                                {issue.description}
                                            </div>
                                            <div style={{ fontSize: '10px', color: '#999', display: 'flex', justifyContent: 'space-between' }}>
                                                <span>{issue.location}</span>
                                            </div>
                                        </div>
                                        <ChevronRight size={12} color="#ccc" style={{ transform: expandedIssue === idx ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }} />
                                    </div>

                                    {expandedIssue === idx && (
                                        <div style={{ padding: '6px 8px', background: '#f8fafc', borderTop: '1px solid #f1f5f9', fontSize: '11px' }}>
                                            <div style={{ display: 'flex', gap: '4px', color: '#334155' }}>
                                                <span style={{ fontWeight: '600', flexShrink: 0 }}>建议:</span>
                                                <span style={{ lineHeight: '1.4' }}>{issue.suggestion}</span>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </>
                ) : (
                    <div style={{ textAlign: 'center', color: '#ccc', fontSize: '11px', marginTop: '40px' }}>
                        {!isConfigExpanded && <p>点击上方"显示配置"以开始新的审核</p>}
                    </div>
                )}
            </div>
        </div>
    );
};
