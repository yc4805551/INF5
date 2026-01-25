import React from 'react';
import { Send, Upload, Square } from 'lucide-react';
import { ChatMessage, AISuggestion } from '../../types';
import { AuditReportMessage } from './AuditReportMessage';
import './CopilotChat.css';

interface CopilotChatProps {
    history: ChatMessage[];
    onSendMessage: (text: string) => Promise<void>;
    isLoading: boolean;
    selectedText?: string;
    onRunFullAudit?: () => void;

    // Suggestion Actions for Audit Cards
    onApplySuggestion: (suggestion: AISuggestion) => void;
    onDismissSuggestion: (id: string) => void;
}

export const CopilotChat: React.FC<CopilotChatProps> = ({
    history,
    onSendMessage,
    isLoading,
    selectedText,
    onRunFullAudit,
    onApplySuggestion,
    onDismissSuggestion
}) => {
    const [inputValue, setInputValue] = React.useState('');
    const messagesEndRef = React.useRef<HTMLDivElement>(null);

    // Auto-scroll
    React.useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [history]);

    const handleSend = () => {
        if (!inputValue.trim() || isLoading) return;
        onSendMessage(inputValue);
        setInputValue('');
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const renderMessageContent = (msg: ChatMessage) => {
        // Simple heuristic: check if content looks like our special audit report text
        // In useUnifiedAssistant, we formatted it as text but also passed the raw data via state?
        // Wait, standard ChatMessage structure (from Gemini SDK) is parts[{ text: "..." }]
        // We need a way to detect Structured Data in the message history.
        // Option 1: Try parsing the text part as JSON if it starts with { "type": "audit_report" }
        // Option 2: Look for specific markers.

        return msg.parts.map((part, pIdx) => {
            // Try to see if this part is a HIDDEN structured data payload
            // Current backend behavior (from useUnifiedAssistant hook modification):
            // It creates a text message: "✅ [审核完成] ... \n\n(详细...)"
            // BUT we want to pass the DATA.

            // Let's enhance the Hook to serialize the DATA into the text part 
            // in a way we can detect, OR (better) use a custom property on ChatMessage if TypeScript allowed.
            // Since TypeScript types for ChatMessage might be strict, let's try to parse text IF it looks like JSON.

            let content = part.text;
            let auditData = null;

            // Hacky way to embed data: <StructuredData json="..." /> or just JSON string
            // Let's assume the hook passed JSON string for audit report
            if (content.trim().startsWith('{"type":"audit_report"')) {
                try {
                    const parsed = JSON.parse(content);
                    if (parsed.type === 'audit_report') {
                        return (
                            <AuditReportMessage
                                key={pIdx}
                                result={parsed.data}
                                onApplySuggestion={onApplySuggestion}
                                onDismissSuggestion={onDismissSuggestion}
                            />
                        );
                    }
                } catch (e) {
                    // Not valid JSON, render as text
                }
            }

            // Render standard text
            return <div key={pIdx} style={{ whiteSpace: 'pre-wrap' }}>{content}</div>;
        });
    };

    return (
        <div className="copilot-chat-container">
            {/* Quick Actions Toolbar */}
            <div className="copilot-toolbar">
                <button
                    className="action-btn audit-btn"
                    onClick={onRunFullAudit}
                    title="运行全文深度体检"
                    disabled={isLoading}
                >
                    🔍 全文体检
                </button>
            </div>

            {/* Messages Area */}
            <div className="chat-messages">
                {history.length === 0 ? (
                    <div className="chat-welcome">
                        <h3>👋 我是您的写作 Copilot</h3>
                        <p>我可以帮您润色文字、检查逻辑，或者进行全文审核。</p>
                        <div className="quick-starters">
                            <button onClick={() => onSendMessage("帮我还原子弹笔记风格")}>🎭 风格模仿</button>
                            <button onClick={() => onSendMessage("这段话逻辑通顺吗？")}>🧠 逻辑检查</button>
                            <button onClick={() => onSendMessage("使语言更正式")}>👔 润色语气</button>
                        </div>
                    </div>
                ) : (
                    history.map((msg, idx) => (
                        <div key={idx} className={`chat-bubble ${msg.role} ${msg.role === 'model' && msg.parts[0].text.includes('audit_report') ? 'audit-message' : ''}`}>
                            <div className="bubble-content">
                                {renderMessageContent(msg)}
                            </div>
                        </div>
                    ))
                )}

                {isLoading && (
                    <div className="chat-bubble model loading">
                        <div className="typing-dot"></div>
                        <div className="typing-dot"></div>
                        <div className="typing-dot"></div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="chat-input-area">
                {selectedText && (
                    <div className="selected-context-preview">
                        <span className="sc-label">针对选段:</span>
                        <span className="sc-text">"{selectedText.slice(0, 30)}..."</span>
                    </div>
                )}
                <div className="input-wrapper">
                    <textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={selectedText ? "针对选中的文本在问..." : "输入问题或指令..."}
                        disabled={isLoading}
                    />
                    <button
                        className="send-btn"
                        onClick={handleSend}
                        disabled={!inputValue.trim() || isLoading}
                    >
                        {isLoading ? <Square size={16} /> : <Send size={16} />}
                    </button>
                </div>
            </div>
        </div>
    );
};
