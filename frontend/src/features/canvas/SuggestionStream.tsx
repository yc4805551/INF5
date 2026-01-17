import React from 'react';
import { AdvisorSuggestion } from './hooks/useAdvisor';
import { Check, Sparkles, AlertTriangle, ArrowRight } from 'lucide-react';

interface SuggestionStreamProps {
    suggestions: AdvisorSuggestion[];
    onApply: (suggestion: string) => void;
    isLoading: boolean;
}

export const SuggestionStream: React.FC<SuggestionStreamProps> = ({ suggestions, onApply, isLoading }) => {
    if (isLoading) {
        return (
            <div style={{ padding: '20px', textAlign: 'center', color: '#666' }}>
                <div className="loading-spinner" style={{ marginBottom: '10px' }} />
                <p style={{ fontSize: '12px' }}>AI 参谋团正在分析上下文...</p>
                <div style={{ display: 'flex', gap: '5px', justifyContent: 'center', marginTop: '5px', fontSize: '10px', opacity: 0.7 }}>
                    <span>🕵️ 校对中</span>
                    <span>🎨 润色中</span>
                </div>
            </div>
        );
    }

    if (suggestions.length === 0) return null;

    return (
        <div className="suggestion-stream" style={{ padding: '10px', background: '#f8f9fa', borderBottom: '1px solid #eee' }}>
            <h4 style={{ fontSize: '12px', margin: '0 0 10px 0', color: '#666', display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Sparkles size={12} color="#6db33f" />
                <span>智能参谋建议 ({suggestions.length})</span>
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {suggestions.map((s, idx) => (
                    <div key={idx} className="suggestion-card" style={{
                        background: '#fff', borderRadius: '6px', padding: '10px',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.05)', borderLeft: `3px solid ${getColor(s.type)}`
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 'bold', color: getColor(s.type), display: 'flex', alignItems: 'center', gap: '4px' }}>
                                {getIcon(s.type)} {labels[s.type]}
                            </span>
                        </div>

                        <div style={{ fontSize: '12px', marginBottom: '8px', lineHeight: '1.4' }}>
                            <div style={{ color: '#999', textDecoration: 'line-through', fontSize: '11px' }}>{s.original}</div>
                            <div style={{ color: '#333', fontWeight: '500', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <ArrowRight size={10} color="#ccc" /> {s.suggestion}
                            </div>
                        </div>

                        {s.reason && (
                            <div style={{ fontSize: '11px', color: '#666', fontStyle: 'italic', marginBottom: '8px' }}>
                                💡 {s.reason}
                            </div>
                        )}

                        <button
                            onClick={() => onApply(s.suggestion)}
                            style={{
                                width: '100%', padding: '6px', background: '#e6f4ea', border: 'none',
                                color: '#1e7f34', borderRadius: '4px', cursor: 'pointer', fontSize: '12px',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px'
                            }}
                        >
                            <Check size={12} /> 采纳建议
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
};

const labels = {
    'proofread': '纠错建议',
    'polish': '润色优化',
    'logic': '逻辑检查'
};

const getColor = (type: string) => {
    switch (type) {
        case 'proofread': return '#d93025';
        case 'polish': return '#1a73e8';
        case 'logic': return '#f9ab00';
        default: return '#666';
    }
};

const getIcon = (type: string) => {
    switch (type) {
        case 'proofread': return <AlertTriangle size={12} />;
        case 'polish': return <Sparkles size={12} />;
        // case 'logic': return <GitCompare size={12} />;
        default: return <Sparkles size={12} />;
    }
};
