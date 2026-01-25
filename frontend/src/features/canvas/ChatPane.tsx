import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { Send, Sparkles, Check, X, User, Bot, ChevronDown } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ModelConfig, Message } from './types';
import { getAvailableModels, MODEL_DISPLAY_NAMES, frontendApiConfig } from '../../services/ai';
import { SuggestionStream } from './SuggestionStream';
import { AdvisorSuggestion } from './hooks/useAdvisor';

interface ChatPaneProps {
    onSendMessage: (message: string, modelConfig: ModelConfig) => void;
    isProcessing: boolean;
    isPendingConfirmation?: boolean;
    onConfirm?: () => void;
    onDiscard?: () => void;
    onFormat?: (modelConfig: ModelConfig, scope?: 'all' | 'layout' | 'body', processor?: 'local' | 'ai') => void;
    showBodyFormatDialog?: boolean;
    onBodyFormatConfirm?: () => void;
    onBodyFormatCancel?: () => void;
    messages?: Message[];
    selectionContext?: { text: string; ids: number[] } | null;
    onClearSelection?: () => void;

    // Advisor Props
    advisorSuggestions?: AdvisorSuggestion[];
    isAdvising?: boolean;
    onApplySuggestion?: (text: string) => void;
}

export interface ChatPaneHandle {
    setInput: (text: string) => void;
    focus: () => void;
}

export const ChatPane = forwardRef<ChatPaneHandle, ChatPaneProps>(({
    onSendMessage,
    isProcessing,
    isPendingConfirmation = false,
    onConfirm,
    onDiscard,
    onFormat,
    showBodyFormatDialog = false,
    onBodyFormatConfirm,
    onBodyFormatCancel,
    messages = [],
    selectionContext,
    onClearSelection,
    advisorSuggestions = [],
    isAdvising = false,
    onApplySuggestion
}, ref) => {
    const [input, setInput] = useState('');
    const availableModels = getAvailableModels();
    const [selectedModel, setSelectedModel] = useState<string>(availableModels[0] || 'free');
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    useImperativeHandle(ref, () => ({
        setInput: (text: string) => setInput(text),
        focus: () => inputRef.current?.focus()
    }));

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isPendingConfirmation]);

    const getModelConfig = (model: string): ModelConfig => {
        const config = frontendApiConfig[model];
        if (!config) return { provider: 'free' };

        return {
            provider: model as any,
            apiKey: config.apiKey,
            endpoint: config.endpoint,
            model: config.model
        };
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim() && !isProcessing) {
            onSendMessage(input, getModelConfig(selectedModel));
            setInput('');
        }
    };

    return (
        <div className="chat-container">
            {/* Body Format Confirmation Dialog */}
            {showBodyFormatDialog && (
                <div className="modal-overlay">
                    <div className="modal-content">
                        <h3>Format Body Text?</h3>
                        <p>Layout formatting is complete. Do you want to proceed with formatting the body text?</p>
                        <div className="modal-actions">
                            <button onClick={onBodyFormatCancel} className="btn btn-secondary">No, Skip</button>
                            <button onClick={onBodyFormatConfirm} className="btn btn-primary">Yes, Format Body</button>
                        </div>
                    </div>
                </div>
            )}

            <div className="chat-messages" style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Advisor Stream Section */}
                {(isAdvising || advisorSuggestions.length > 0) && onApplySuggestion && (
                    <SuggestionStream
                        suggestions={advisorSuggestions}
                        isLoading={isAdvising}
                        onApply={onApplySuggestion}
                    />
                )}

                {messages.length === 0 && advisorSuggestions.length === 0 && !isAdvising && (
                    <div className="chat-welcome">
                        <div className="avatar bot">
                            <Sparkles size={16} />
                        </div>
                        <div className="message-bubble bot">
                            Hello! I'm your AI editor. Upload a document and tell me what you'd like to change.
                        </div>
                    </div>
                )}

                {messages.map((msg, idx) => {
                    if (!msg) return null;
                    return (
                        <div key={idx} className={`chat-message ${msg.role === 'user' ? 'user-message' : 'bot-message'}`} style={{ display: 'flex', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row', gap: '12px' }}>
                            <div className={`avatar ${msg.role === 'user' ? 'user' : 'bot'}`}>
                                {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                            </div>
                            <div className={`message-bubble ${msg.role === 'user' ? 'user' : 'bot'}`}>
                                <div className="prose">
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            code: ({ node, ...props }) => <code {...props} />,
                                            pre: ({ node, ...props }) => <pre {...props} />,
                                        }}
                                    >
                                        {msg.content || ''}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        </div>
                    );
                })}

                {isPendingConfirmation && (
                    <div className="chat-welcome">
                        <div className="avatar bot">
                            <Sparkles size={16} />
                        </div>
                        <div className="message-bubble bot">
                            I've drafted some changes. Please review the preview on the right. Click 'Confirm' to save or 'Discard' to revert.
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-area">
                {isPendingConfirmation ? (
                    <div className="confirmation-bar">
                        <button onClick={onDiscard} className="discard-btn" disabled={isProcessing}>
                            <X size={18} /> Discard
                        </button>
                        <button onClick={onConfirm} className="confirm-btn" disabled={isProcessing}>
                            <Check size={18} /> Confirm
                        </button>
                    </div>
                ) : (
                    <>
                        <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
                            <select
                                value={selectedModel}
                                onChange={(e) => setSelectedModel(e.target.value)}
                                className="model-selector"
                                style={{ flex: '1' }}
                            >
                                {availableModels.map(modelKey => (
                                    <option key={modelKey} value={modelKey}>
                                        {MODEL_DISPLAY_NAMES[modelKey] || modelKey}
                                    </option>
                                ))}
                            </select>
                            <select
                                className="model-selector"
                                style={{ flex: '0 0 auto', minWidth: '120px' }}
                                onChange={(e) => {
                                    const value = e.target.value;
                                    if (value === 'local') {
                                        onFormat && onFormat(getModelConfig(selectedModel), 'layout', 'local');
                                    } else if (value === 'ai') {
                                        onFormat && onFormat(getModelConfig(selectedModel), 'layout', 'ai');
                                    }
                                    e.target.value = ''; // Reset selection
                                }}
                                disabled={isProcessing}
                                defaultValue=""
                            >
                                <option value="" disabled>格式处理</option>
                                <option value="local">⚡ 本地</option>
                                <option value="ai">🤖 AI</option>
                            </select>
                        </div>

                        {selectionContext && (
                            <div style={{ marginBottom: '8px', padding: '8px', backgroundColor: 'rgba(0, 120, 212, 0.1)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: 'var(--accent-color)' }}>
                                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '200px' }}>
                                    Editing: "{selectionContext.text.substring(0, 30)}..."
                                </span>
                                <button onClick={onClearSelection} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}>
                                    <X size={12} />
                                </button>
                            </div>
                        )}

                        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '8px', alignItems: 'flex-end', width: '100%' }}>
                            <textarea
                                ref={inputRef}
                                value={input}
                                onChange={(e) => {
                                    setInput(e.target.value);
                                    // Auto-height
                                    e.target.style.height = 'auto';
                                    e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSubmit(e);
                                    }
                                }}
                                placeholder="输入您的修改建议... (Shift+Enter 换行)"
                                className="chat-text-input"
                                disabled={isProcessing}
                                style={{
                                    resize: 'none',
                                    minHeight: '40px',
                                    maxHeight: '150px',
                                    overflowY: 'auto',
                                    flex: 1,
                                    padding: '8px 12px',
                                    lineHeight: '1.5'
                                }}
                            />
                            <button
                                onClick={handleSubmit}
                                disabled={isProcessing || !input.trim()}
                                className="send-button"
                                style={{ height: '40px', position: 'static', transform: 'none' }}
                            >
                                <Send size={18} />
                            </button>
                        </form>
                        <div style={{ textAlign: 'center', marginTop: '8px' }}>
                            <p style={{ fontSize: '12px', color: '#666', margin: 0 }}>AI can make mistakes. Please review changes.</p>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
});
