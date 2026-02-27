import React, { useRef, useEffect, useState } from 'react';
import { Send, Square } from 'lucide-react';
import { ChatMessage, AuditResult, AISuggestion } from '../../types';
import './CopilotChat.css'; // We'll keep the CSS import but override with inline styles
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './ChatMode.css';

interface CopilotChatProps {
    history: ChatMessage[];
    onSend: (text: string) => void;
    isLoading: boolean;
    onApplySuggestion: (suggestion: AISuggestion) => void;
    onDismissSuggestion: (suggestionId: string) => void;
    onRunFullAudit?: () => void;
    selectedText?: string;
    onInsert?: (text: string) => void;
}

export const CopilotChat: React.FC<CopilotChatProps> = ({
    history,
    onSend,
    isLoading,
    onApplySuggestion,
    onDismissSuggestion,
    onRunFullAudit,
    selectedText,
    onInsert
}) => {
    const [inputValue, setInputValue] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [history, isLoading]);

    const handleSend = () => {
        if (!inputValue.trim()) return;
        onSend(inputValue);
        setInputValue('');
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    // Robust Message Renderer
    const renderMessageContent = (msg: ChatMessage) => {
        return msg.parts.map((part, pIdx) => {
            // Check if it's our special JSON audit report
            if (part.text.trim().startsWith('{"type":"audit_report"')) {
                try {
                    const parsed = JSON.parse(part.text);
                    if (parsed.type === 'audit_report') {
                        return (
                            <div key={pIdx} style={{ background: '#0f172a', padding: '10px', borderRadius: '8px', border: '1px solid #334155' }}>
                                <div style={{ color: '#60a5fa', fontWeight: 'bold', marginBottom: '8px' }}>🔍 深度体检报告</div>
                                <div style={{ color: '#cbd5e1', fontSize: '12px' }}>
                                    (报告数据已接收，请查看详细建议)
                                </div>
                            </div>
                        );
                    }
                } catch (e) { }
            }
            return (
                <div key={pIdx} className="chat-markdown-body">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {part.text}
                    </ReactMarkdown>
                </div>
            );
        });
    };

    return (
        <div className="copilot-chat-container" style={{ background: '#09090b', display: 'flex', flexDirection: 'column', height: '100%', minHeight: '400px' }}>
            {/* Quick Actions Toolbar */}
            <div className="copilot-toolbar" style={{ background: '#18181b', borderBottom: '1px solid #27272a', padding: '10px' }}>
                <button
                    className="action-btn audit-btn"
                    onClick={onRunFullAudit}
                    title="运行全文深度体检"
                    disabled={isLoading}
                    style={{ background: '#27272a', color: '#e4e4e7', border: '1px solid #3f3f46', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
                >
                    <span>🔍</span> 全文体检
                </button>
            </div>

            {/* Messages Area */}
            <div className="chat-messages" style={{ padding: '20px', flex: 1, overflowY: 'auto' }}>
                {history.length === 0 ? (
                    <div className="chat-welcome" style={{ textAlign: 'center', marginTop: '60px', color: '#71717a' }}>
                        <p>👋 我是您的 AI 助手，请告诉我有何指示。</p>
                    </div>
                ) : (
                    history.map((msg, idx) => (
                        <div key={idx} className={`chat-bubble ${msg.role}`} style={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                            maxWidth: '85%',
                            marginBottom: '16px'
                        }}>
                            <div className="bubble-content" style={{
                                padding: '12px 16px',
                                borderRadius: '12px',
                                background: msg.role === 'user' ? '#3f3f46' : '#27272a', // Lighter Zinc for User, Darker for AI
                                color: '#ffffff',
                                border: 'none', // Removed Border
                                boxShadow: '0 2px 4px rgba(0,0,0,0.3)', // Basic Shadow
                                fontSize: '14px',
                                lineHeight: '1.6'
                            }}>
                                {renderMessageContent(msg)}
                            </div>

                            {/* Insert Button for Model Messages */}
                            {msg.role === 'model' && onInsert && (
                                <div style={{ marginTop: '6px' }}>
                                    <button
                                        onClick={() => onInsert(msg.parts[0].text)}
                                        style={{
                                            fontSize: '11px',
                                            padding: '4px 8px',
                                            background: '#18181b',
                                            color: '#a1a1aa',
                                            border: '1px solid #27272a', // Darker border, less noticeable
                                            borderRadius: '6px',
                                            cursor: 'pointer',
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '4px'
                                        }}
                                        title="插入到文档"
                                    >
                                        📝 插入到文档
                                    </button>
                                </div>
                            )}
                        </div>
                    ))
                )}

                {isLoading && (
                    <div className="chat-bubble model" style={{ alignSelf: 'flex-start', background: 'transparent' }}>
                        <div className="bubble-content" style={{ background: '#27272a', padding: '12px 20px', borderRadius: '12px', color: '#e4e4e7', boxShadow: '0 2px 4px rgba(0,0,0,0.3)', border: 'none' }}>
                            <span>Thinking...</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="chat-input-area" style={{ background: '#18181b', borderTop: '1px solid #27272a', padding: '16px' }}>
                {selectedText && (
                    <div className="selected-context-preview" style={{ background: '#09090b', color: '#a1a1aa', padding: '8px', borderRadius: '6px', marginBottom: '8px', fontSize: '12px', border: '1px solid #27272a' }}>
                        <span className="sc-label" style={{ color: '#e4e4e7', fontWeight: 'bold', marginRight: '8px' }}>针对选段:</span>
                        <span className="sc-text">"{selectedText?.slice(0, 30)}..."</span>
                    </div>
                )}
                <div className="input-wrapper" style={{ background: '#09090b', border: '1px solid #27272a', borderRadius: '12px', padding: '10px', display: 'flex', gap: '8px', alignItems: 'flex-end', boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.3)' }}>
                    <textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={selectedText ? "针对选中的文本在问..." : "输入问题或指令..."}
                        disabled={isLoading}
                        style={{ color: '#fafafa', background: 'transparent', border: 'none', resize: 'none', flex: 1, outline: 'none', minHeight: '24px' }}
                    />
                    <button
                        className="send-btn"
                        onClick={handleSend}
                        disabled={!inputValue.trim() || isLoading}
                        style={{
                            background: !inputValue.trim() && !isLoading ? '#27272a' : '#fafafa', // Dark grey if disabled, White if active
                            color: !inputValue.trim() && !isLoading ? '#52525b' : '#18181b',      // Dim grey icon if disabled, Black icon if active
                            width: '32px',
                            height: '32px',
                            borderRadius: '8px',
                            border: 'none',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: (!inputValue.trim() || isLoading) ? 'not-allowed' : 'pointer',
                            transition: 'all 0.2s ease',
                            opacity: 1 // Force full opacity to control colors manually
                        }}
                    >
                        {isLoading ? <Square size={16} className="animate-spin" /> : <Send size={18} strokeWidth={2.5} />}
                    </button>
                </div>
            </div>
        </div>
    );
};
