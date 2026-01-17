import React from 'react';
import { RealtimeMode } from './RealtimeMode';
import { AuditMode } from './AuditMode';
import { ChatMode } from './ChatMode';
import { AssistantMode, AISuggestion, AuditResult, ChatMessage } from '../../types';
import { Sparkles, Shield, MessageSquare } from 'lucide-react';
import './UnifiedAssistant.css';

// Import ChatMessage type


interface UnifiedAssistantProps {
    mode: AssistantMode;
    onModeChange: (mode: AssistantMode) => void;
    isAnalyzing: boolean;
    suggestions: AISuggestion[];
    auditResult: AuditResult | null;
    onApplySuggestion: (suggestion: AISuggestion) => void;
    onDismissSuggestion: (suggestionId: string) => void;
    onRunAudit?: (agents?: string[]) => void;
    selectedText?: string;
    // Chat Props
    chatHistory?: ChatMessage[];
    onSendMessage?: (text: string) => Promise<void>;
}

export const UnifiedAssistant: React.FC<UnifiedAssistantProps> = ({
    mode,
    onModeChange,
    isAnalyzing,
    suggestions,
    auditResult,
    onApplySuggestion,
    onDismissSuggestion,
    onRunAudit,
    selectedText,
    chatHistory = [],
    onSendMessage
}) => {
    return (
        <div className="unified-assistant">
            {/* Mode Tabs */}
            <div className="assistant-tabs">
                <button
                    className={`tab ${mode === 'realtime' ? 'active' : ''}`}
                    onClick={() => onModeChange('realtime')}
                    title="实时建议"
                >
                    <Sparkles size={16} />
                    <span>实时</span>
                </button>
                <button
                    className={`tab ${mode === 'chat' ? 'active' : ''}`}
                    onClick={() => onModeChange('chat')}
                    title="顾问对话"
                >
                    <MessageSquare size={16} />
                    <span>顾问</span>
                </button>
                <button
                    className={`tab ${mode === 'audit' ? 'active' : ''}`}
                    onClick={() => onModeChange('audit')}
                    title="全 文 审 核"
                >
                    <Shield size={16} />
                    <span>审核</span>
                </button>
            </div>

            {/* Content */}
            <div className="assistant-content">
                {mode === 'realtime' && (
                    <RealtimeMode
                        suggestions={suggestions}
                        isAnalyzing={isAnalyzing}
                        onApplySuggestion={onApplySuggestion}
                        onDismissSuggestion={onDismissSuggestion}
                        selectedText={selectedText}
                    />
                )}

                {mode === 'chat' && (
                    <ChatMode
                        history={chatHistory}
                        onSendMessage={onSendMessage || (async () => { })}
                        isLoading={isAnalyzing} // Reuse isAnalyzing for chat loading? Or separate?
                    // Note: usually chat loading is separate. We might need to map isAnalyzing to chat loading state if shared.
                    />
                )}

                {mode === 'audit' && (
                    <AuditMode
                        auditResult={auditResult}
                        isAnalyzing={isAnalyzing}
                        onRunAudit={onRunAudit || (() => { })}
                        onApplySuggestion={onApplySuggestion}
                        onDismissSuggestion={onDismissSuggestion}
                    />
                )}
            </div>
        </div>
    );
};
