import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Check, X, User, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ModelConfig, Message } from '../types';

interface ChatPaneProps {
    onSendMessage: (message: string, modelConfig: ModelConfig) => void;
    isProcessing: boolean;
    isPendingConfirmation?: boolean;
    onConfirm?: () => void;
    onDiscard?: () => void;
    onFormat?: (modelConfig: ModelConfig, scope?: 'all' | 'layout' | 'body') => void;
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
        <div className="flex flex-col h-full bg-white border-r border-gray-200 shadow-[4px_0_24px_rgba(0,0,0,0.02)] z-10 relative">
            {/* Body Format Confirmation Dialog */}
            {showBodyFormatDialog && (
                <div className="absolute inset-0 z-50 bg-black/50 flex items-center justify-center p-4 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm border border-gray-100 transform transition-all scale-100">
                        <h3 className="text-lg font-bold text-gray-900 mb-2">Format Body Text?</h3>
                        <p className="text-sm text-gray-600 mb-6 leading-relaxed">
                            Layout formatting is complete. Do you want to proceed with formatting the body text?
                            <span className="block mt-2 text-xs text-gray-500 bg-gray-50 p-2 rounded border border-gray-100">
                                This will apply standard fonts and spacing to the main content.
                            </span>
                        </p>
                        <div className="flex gap-3">
                            <button
                                onClick={onBodyFormatCancel}
                                className="flex-1 px-4 py-2.5 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors font-medium text-sm"
                            >
                                No, Skip
                            </button>
                            <button
                                onClick={onBodyFormatConfirm}
                                className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors font-medium text-sm shadow-lg shadow-blue-600/20"
                            >
                                Yes, Format Body
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <div className="flex-1 p-6 overflow-y-auto space-y-4">
                {messages.length === 0 && (
                    <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                            <Sparkles size={16} className="text-blue-600" />
                        </div>
                        <div className="bg-gray-100 p-4 rounded-2xl rounded-tl-none text-sm text-gray-700 leading-relaxed shadow-sm">
                            Hello! I'm your AI editor. Upload a document and tell me what you'd like to change.
                        </div>
                    </div>
                )}

                {messages.map((msg, idx) => {
                    if (!msg) return null;
                    return (
                        <div key={idx} className={`flex items-start gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-gray-200' : 'bg-blue-100'}`}>
                                {msg.role === 'user' ? <User size={16} className="text-gray-600" /> : <Bot size={16} className="text-blue-600" />}
                            </div>
                            <div className={`p-4 rounded-2xl text-xs leading-relaxed shadow-sm max-w-[85%] ${msg.role === 'user'
                                ? 'bg-blue-600 text-white rounded-tr-none'
                                : 'bg-gray-100 text-gray-700 rounded-tl-none'
                                }`}>
                                <div className={`prose prose-sm max-w-none break-words ${msg.role === 'user'
                                    ? 'prose-invert prose-p:text-white prose-headings:text-white prose-strong:text-white prose-ul:text-white prose-ol:text-white'
                                    : 'prose-headings:text-gray-800 prose-p:text-gray-700 prose-strong:text-gray-900'
                                    }`}>
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                                            ul: ({ node, ...props }) => <ul className="list-disc pl-4 mb-2 last:mb-0" {...props} />,
                                            ol: ({ node, ...props }) => <ol className="list-decimal pl-4 mb-2 last:mb-0" {...props} />,
                                            li: ({ node, ...props }) => <li className="mb-1" {...props} />,
                                            h1: ({ node, ...props }) => <h1 className="text-lg font-bold mb-2" {...props} />,
                                            h2: ({ node, ...props }) => <h2 className="text-base font-bold mb-2" {...props} />,
                                            h3: ({ node, ...props }) => <h3 className="text-sm font-bold mb-1" {...props} />,
                                            code: ({ node, ...props }) => <code className="bg-black/10 rounded px-1 py-0.5 text-xs font-mono" {...props} />,
                                            pre: ({ node, ...props }) => <pre className="bg-gray-800 text-white p-2 rounded-lg overflow-x-auto mb-2 text-xs" {...props} />,
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
                    <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                            <Sparkles size={16} className="text-blue-600" />
                        </div>
                        <div className="bg-gray-100 p-4 rounded-2xl rounded-tl-none text-sm text-gray-700 leading-relaxed shadow-sm">
                            I've drafted some changes. Please review the preview on the right. Click 'Confirm' to save or 'Discard' to revert.
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>
            <div className="p-6 border-t border-gray-100 bg-white">
                {isPendingConfirmation ? (
                    <div className="flex gap-3">
                        <button
                            onClick={onDiscard}
                            className="flex-1 flex items-center justify-center gap-2 p-3 bg-red-50 text-red-600 rounded-xl hover:bg-red-100 transition-colors font-medium"
                        >
                            <X size={18} />
                            Discard
                        </button>
                        <button
                            onClick={onConfirm}
                            className="flex-1 flex items-center justify-center gap-2 p-3 bg-green-600 text-white rounded-xl hover:bg-green-700 transition-colors font-medium shadow-md shadow-green-600/20"
                        >
                            <Check size={18} />
                            Confirm
                        </button>
                    </div>
                ) : (
                    <>
                        <div className="mb-3 flex gap-2 justify-between items-center">
                            <select
                                value={selectedModel}
                                onChange={(e) => setSelectedModel(e.target.value as any)}
                                className="text-xs border border-gray-200 rounded-lg p-1 bg-gray-50 text-gray-600 focus:outline-none focus:border-blue-500"
                            >
                                <option value="gemini">Google Gemini</option>
                                <option value="openai">OpenAI (GPT-5.1)</option>
                                <option value="deepseek">DeepSeek</option>
                                <option value="aliyun">Aliyun Qwen3</option>
                            </select>
                            <button
                                onClick={() => onFormat && onFormat(getModelConfig(selectedModel), 'layout')}
                                disabled={isProcessing}
                                className="text-xs px-3 py-1 bg-indigo-50 text-indigo-600 rounded-lg hover:bg-indigo-100 transition-colors font-medium border border-indigo-100"
                            >
                                公文格式处理
                            </button>
                        </div>
                        {selectionContext && (
                            <div className="mb-2 p-2 bg-blue-50 border border-blue-100 rounded-lg flex items-center justify-between text-xs text-blue-700">
                                <span className="truncate max-w-[200px] font-medium">
                                    Editing: "{selectionContext.text.substring(0, 30)}..."
                                </span>
                                <button
                                    type="button"
                                    onClick={onClearSelection}
                                    className="text-blue-400 hover:text-blue-600 p-1"
                                >
                                    <X size={12} />
                                </button>
                            </div>
                        )}
                        <form onSubmit={handleSubmit} className="relative">
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="Describe your changes..."
                                className="w-full pl-4 pr-12 py-4 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-gray-700 placeholder-gray-400"
                                disabled={isProcessing}
                            />
                            <button
                                type="submit"
                                disabled={isProcessing || !input.trim()}
                                className="absolute right-2 top-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors shadow-md shadow-blue-600/20"
                            >
                                <Send size={18} />
                            </button>
                        </form>
                        <div className="text-center mt-3">
                            <p className="text-xs text-gray-400">AI can make mistakes. Please review changes.</p>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};
