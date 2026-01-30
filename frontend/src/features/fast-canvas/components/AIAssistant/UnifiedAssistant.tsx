import React from 'react';
import { RealtimeMode } from './RealtimeMode';
import { CopilotChat } from './CopilotChat';
import { AssistantMode, AISuggestion, AuditResult, ChatMessage } from '../../types';
import { Sparkles, MessageSquare } from 'lucide-react';
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
    onSuggestionSelect?: (suggestion: AISuggestion) => void;
    selectedText?: string;
    // Chat Props
    chatHistory?: ChatMessage[];
    onSendMessage?: (text: string) => Promise<void>;
    // Status feedback
    lastCheckResult?: { message: string; timestamp: string; issueCount: number } | null;
    smartWrite?: (prompt: string) => Promise<{ content: string, sources: any[] }>;
    onInsert?: (text: string) => void;
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
    onSendMessage,
    onSuggestionSelect,
    lastCheckResult,
    smartWrite,
    onInsert
}) => {

    // State for View Mode: 'monitor' (default) or 'chat'.
    const [viewMode, setViewMode] = React.useState<'monitor' | 'chat'>('monitor');

    // Toggle function
    const toggleViewMode = () => {
        setViewMode(prev => prev === 'monitor' ? 'chat' : 'monitor');
    };

    console.log('[UnifiedAssistant] render, viewMode:', viewMode, 'history:', chatHistory.length);

    return (
        <div className="unified-assistant">
            {/* Header / Title Bar */}
            <div className="assistant-header-bar">
                <div className="agent-identity">
                    {viewMode === 'monitor' ? (
                        <>
                            <Sparkles size={16} className="text-blue-500" />
                            <span className="font-semibold">实时监察中</span>
                        </>
                    ) : (
                        <>
                            <MessageSquare size={16} className="text-purple-500" />
                            <span className="font-semibold">助手对话</span>
                        </>
                    )}
                </div>
                {/* Switcher Buttons */}
                <div className="header-actions" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>

                    {/* Simplified View Switcher */}
                    <button
                        onClick={toggleViewMode}
                        className="mode-switch-btn"
                        title={viewMode === 'monitor' ? "进入对话模式" : "返回实时模式"}
                    >
                        {viewMode === 'monitor' ? <MessageSquare size={14} /> : <Sparkles size={14} />}
                        {viewMode === 'monitor' ? "提问" : "监控"}
                    </button>

                    {/* View Mode Indicator */}
                    <span style={{ fontSize: '12px', color: '#6b7280' }}>
                        {viewMode === 'monitor' ? '审核模式' : '问答模式'}
                    </span>
                </div>
            </div>

            {/* Status Display - Only in monitor mode */}
            {viewMode === 'monitor' && (
                <div className="check-status-banner" style={{
                    padding: '10px 16px',
                    margin: '12px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    fontWeight: '500',
                    textAlign: 'center',
                    background: isAnalyzing ? '#fef3c7' : (lastCheckResult?.issueCount === 0 ? '#d1fae5' : '#dbeafe'),
                    color: isAnalyzing ? '#78350f' : (lastCheckResult?.issueCount === 0 ? '#065f46' : '#1e40af'),
                    transition: 'all 0.3s ease',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}>
                    {isAnalyzing ? (
                        <>⏳ 正在检查...</>
                    ) : lastCheckResult ? (
                        <>{lastCheckResult.message}</>
                    ) : (
                        <>💡 输入至少10个字后自动检查</>
                    )}
                </div>
            )}

            {/* Content Area */}
            <div className="assistant-content">
                {viewMode === 'monitor' ? (
                    <RealtimeMode
                        suggestions={suggestions}
                        isAnalyzing={isAnalyzing}
                        onApplySuggestion={onApplySuggestion}
                        onDismissSuggestion={onDismissSuggestion}
                        onSuggestionSelect={onSuggestionSelect}
                        selectedText={selectedText}
                    />
                ) : (
                    <CopilotChat
                        history={chatHistory}
                        onSend={async (text) => {
                            // Keyword Trigger Logic: "根据知识库"
                            if (text.includes('根据知识库') && smartWrite) {
                                await smartWrite(text);
                            } else if (onSendMessage) {
                                await onSendMessage(text);
                            }
                        }}
                        isLoading={isAnalyzing}
                        selectedText={selectedText}
                        onRunFullAudit={() => {
                            if (onRunAudit) onRunAudit(['proofread', 'logic', 'format', 'consistency', 'terminology']);
                        }}
                        onApplySuggestion={onApplySuggestion}
                        onDismissSuggestion={onDismissSuggestion}
                        // smartWrite prop removed from CopilotChat usage as it's handled here
                        // isWriteMode removed
                        // setIsWriteMode removed
                        onInsert={onInsert}
                    />
                )}
            </div>
        </div>
    );
};
