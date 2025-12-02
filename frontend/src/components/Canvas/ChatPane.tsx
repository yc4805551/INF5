import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Check, X, User, Bot, ChevronDown } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ModelConfig, Message } from './types';

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
}

export const ChatPane: React.FC<ChatPaneProps> = ({
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
    onClearSelection
}) => {
    const [input, setInput] = useState('');
    const [selectedModel, setSelectedModel] = useState<'gemini' | 'openai' | 'deepseek' | 'aliyun'>('gemini');
    const [showFormatMenu, setShowFormatMenu] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isPendingConfirmation]);

    const getModelConfig = (model: string): ModelConfig => {
        const env = import.meta.env;
        switch (model) {
            case 'gemini':
                return {
                    provider: 'gemini',
                    apiKey: env.VITE_GEMINI_API_KEY,
                    endpoint: env.VITE_GEMINI_ENDPOINT,
                    model: env.VITE_GEMINI_MODEL || 'gemini-2.5-flash'
                };
            case 'openai':
                return {
                    provider: 'openai',
                    apiKey: env.VITE_OPENAI_API_KEY,
                    endpoint: env.VITE_OPENAI_ENDPOINT,
                    model: env.VITE_OPENAI_MODEL
                };
            case 'deepseek':
                return {
                    provider: 'deepseek', // Treated as openai-compatible in backend
                    apiKey: env.VITE_DEEPSEEK_API_KEY,
                    endpoint: env.VITE_DEEPSEEK_ENDPOINT,
                    model: env.VITE_DEEPSEEK_MODEL
                };
            case 'aliyun':
                return {
                    provider: 'aliyun',
                    apiKey: env.VITE_ALI_API_KEY,
                    endpoint: env.VITE_ALI_ENDPOINT,
                    model: env.VITE_ALI_MODEL
                };
            default:
                return { provider: 'gemini' };
        }
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
            {/* Body Format Confirmation Dialog - Simplified for now, can be modalized properly later */}
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
                {messages.length === 0 && (
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
                        <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <select
                                value={selectedModel}
                                onChange={(e) => setSelectedModel(e.target.value as any)}
                                className="model-selector"
                            >
                                <option value="gemini">Google Gemini</option>
                                <option value="openai">OpenAI (GPT-5.1)</option>
                                <option value="deepseek">DeepSeek</option>
                                <option value="aliyun">Aliyun Qwen3</option>
                            </select>
                            <div style={{ position: 'relative' }}>
                                <button
                                    onClick={() => setShowFormatMenu(!showFormatMenu)}
                                    disabled={isProcessing}
                                    className="format-btn"
                                >
                                    <Sparkles size={12} />
                                    公文格式处理
                                    <ChevronDown size={12} />
                                </button>
                                {showFormatMenu && (
                                    <div className="format-menu">
                                        <button
                                            onClick={() => {
                                                onFormat && onFormat(getModelConfig(selectedModel), 'layout', 'local');
                                                setShowFormatMenu(false);
                                            }}
                                            className="format-menu-item"
                                        >
                                            ⚡ 本地快速处理 (推荐)
                                        </button>
                                        <button
                                            onClick={() => {
                                                onFormat && onFormat(getModelConfig(selectedModel), 'layout', 'ai');
                                                setShowFormatMenu(false);
                                            }}
                                            className="format-menu-item"
                                        >
                                            🤖 AI 智能处理
                                        </button>
                                    </div>
                                )}
                            </div>
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

                        <form onSubmit={handleSubmit} className="input-wrapper">
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="Describe your changes..."
                                className="chat-text-input"
                                disabled={isProcessing}
                            />
                            <button
                                type="submit"
                                disabled={isProcessing || !input.trim()}
                                className="send-button"
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
};
