import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, AlertCircle, Loader, Sparkles } from 'lucide-react';
import { ChatMessage } from '../../types';
import './ChatMode.css';

interface ChatModeProps {
    history: ChatMessage[];
    onSendMessage: (text: string) => Promise<void>;
    isLoading: boolean;
}

export const ChatMode: React.FC<ChatModeProps> = ({
    history,
    onSendMessage,
    isLoading
}) => {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [history, isLoading]);

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const text = input;
        setInput('');
        await onSendMessage(text);
    };

    return (
        <div className="chat-mode-container">
            <div className="chat-messages">
                {history.length === 0 && (
                    <div className="chat-welcome">
                        <div className="chat-welcome-icon">
                            <Sparkles size={40} color="white" />
                        </div>
                        <p>我是您的智能写作顾问，可以帮您解答问题、润色段落或提供灵感。</p>

                        <div className="chat-welcome-examples">
                            <button
                                className="example-question"
                                onClick={() => onSendMessage('帮我优化这段文字的表达')}
                            >
                                ✨ 帮我优化这段文字的表达
                            </button>
                            <button
                                className="example-question"
                                onClick={() => onSendMessage('这个段落的语气是否合适？')}
                            >
                                💡 这个段落的语气是否合适？
                            </button>
                            <button
                                className="example-question"
                                onClick={() => onSendMessage('如何让这段内容更专业？')}
                            >
                                🎯 如何让这段内容更专业？
                            </button>
                        </div>
                    </div>
                )}

                {history.map((msg, idx) => (
                    <div key={idx} className={`chat-message ${msg.role}`}>
                        <div className="avatar">
                            {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                        </div>
                        <div className="message-content">
                            {msg.parts.map((part, pIdx) => (
                                <p key={pIdx}>{part.text}</p>
                            ))}
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div className="chat-message model loading">
                        <div className="avatar"><Bot size={16} /></div>
                        <div className="message-content">
                            <Loader size={14} className="spinner" />
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <form className="chat-input-area" onSubmit={handleSend}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="输入问题或指令..."
                    disabled={isLoading}
                />
                <button type="submit" disabled={!input.trim() || isLoading}>
                    <Send size={16} />
                </button>
            </form>
        </div>
    );
};
