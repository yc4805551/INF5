import React, { useRef, useState, useEffect } from 'react';
import { Database, ArrowUp, Bot, Paperclip, ChevronDown, ChevronRight, Activity, FileSpreadsheet, Play, X, ListTodo, Loader2, Bug } from 'lucide-react';
import { useFiller, FillerMessage, PlanStep } from './useFiller';
import ReactMarkdown from 'react-markdown';

interface FillerPanelProps {
    onRefresh?: () => void;
    onUploadReference?: (file: File) => Promise<void>;
}

export const FillerPanel: React.FC<FillerPanelProps> = ({ onRefresh, onUploadReference }) => {
    const {
        isUploading,
        isAnalyzing,
        sourceData,
        chatHistory,
        uploadSource,
        runAgentTask,
        generatePlan,
        updateMessage,
        isPlanning,
    } = useFiller();

    const fileInputRef = useRef<HTMLInputElement>(null);
    const chatContainerRef = useRef<HTMLDivElement>(null);
    const [inputValue, setInputValue] = useState('');
    const [pendingInstruction, setPendingInstruction] = useState('');

    // Debug Log State
    const [showLogs, setShowLogs] = useState(false);
    const [logContent, setLogContent] = useState('');
    const { getDebugLogs } = useFiller();

    const handleToggleLogs = async () => {
        if (!showLogs) {
            const content = await getDebugLogs();
            setLogContent(content);
        }
        setShowLogs(!showLogs);
    };

    // Auto-scroll to bottom of chat
    useEffect(() => {
        if (chatContainerRef.current) {
            chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
        }
    }, [chatHistory]);



    const handleSend = async () => {
        if (!inputValue.trim() || isAnalyzing || isPlanning) return;
        const text = inputValue;
        setInputValue(''); // Clear immediately
        setPendingInstruction(text);

        // Trigger Planning Phase first
        await generatePlan(text);
    };

    const handleUpdatePlan = (msgId: string, newPlan: PlanStep[]) => {
        updateMessage(msgId, { plan: newPlan });
    };

    const handleConfirmPlan = async (msgId: string, instruction: string | undefined, plan: PlanStep[]) => {
        const finalInstruction = instruction || "Execute Plan"; // Fallback

        // Mark as non-interactive immediately
        updateMessage(msgId, { isInteractive: false });

        await runAgentTask(finalInstruction, plan);
        onRefresh?.();
    };

    const handleCancelPlan = () => {
        setPendingInstruction('');
        // To clear plan, we might need a clear function from useFiller or just re-generate empty?
        // useFiller doesn't expose clean set. We can just ignore it or reload.
        // Actually, let's just run an empty generatePlan? No.
        // For MVP, we'll re-init via parent or just hide it.
        // Let's implement a 'clearPlan' in useFiller in next step if needed, 
        // but for now we can just let it sit or overwrite. 
        // Actually, simply ignoring it is fine, but UI will persist.
        // I will rely on the user typing a new command.
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="filler-panel" style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            background: '#ffffff',
            position: 'relative'
        }}>
            {/* Header */}
            <div style={{
                padding: '16px',
                borderBottom: '1px solid #f3f4f6',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: '#fff',
                zIndex: 10
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Bot size={20} color="#7c3aed" />
                    <span style={{ fontWeight: 600, color: '#111827' }}>智能填充 Agent</span>
                </div>
                {sourceData && (
                    <div style={{
                        fontSize: '11px',
                        padding: '2px 8px',
                        background: '#f3f4f6',
                        borderRadius: '12px',
                        color: '#6b7280',
                        maxWidth: '120px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                    }} title={sourceData.filename}>
                        {sourceData.filename}
                    </div>
                )}

                <button
                    onClick={handleToggleLogs}
                    title="查看调试日志"
                    style={{
                        padding: '4px',
                        borderRadius: '4px',
                        border: 'none',
                        background: 'transparent',
                        cursor: 'pointer',
                        color: '#9ca3af'
                    }}
                >
                    <Bug size={16} />
                </button>
            </div>

            {showLogs && (
                <div style={{
                    position: 'absolute',
                    top: '56px',
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: '#1e1e1e',
                    color: '#00ff00',
                    padding: '16px',
                    fontSize: '12px',
                    fontFamily: 'monospace',
                    overflowY: 'auto',
                    zIndex: 20,
                    opacity: 0.95
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', alignItems: 'center' }}>
                        <strong>Debug Logs</strong>
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <button
                                onClick={async () => {
                                    setLogContent("Refreshing...");
                                    const content = await getDebugLogs();
                                    setLogContent(content);
                                }}
                                style={{ background: '#374151', border: 'none', color: 'white', cursor: 'pointer', padding: '2px 8px', borderRadius: '4px' }}
                            >
                                Refresh
                            </button>
                            <button onClick={() => setShowLogs(false)} style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer' }}>Close</button>
                        </div>
                    </div>
                    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                        {logContent || "Loading..."}
                    </pre>
                </div>
            )}

            {/* Chat History Area */}
            <div ref={chatContainerRef} style={{
                flex: 1,
                overflowY: 'auto',
                padding: '20px 16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '24px'
            }}>
                {/* Initial Welcome State */}
                {chatHistory.length === 0 && (
                    <div style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                        color: '#9ca3af',
                        gap: '12px',
                        paddingBottom: '40px'
                    }}>
                        <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: '#f3f4f6', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Activity size={24} color="#d1d5db" />
                        </div>
                        <p style={{ fontSize: '14px' }}>告诉我你想怎么处理文档...</p>
                        <p style={{ fontSize: '12px', color: '#d1d5db' }}>
                            (请使用右上角 "添加参考" 按钮上传资料)
                        </p>
                    </div>
                )}

                {chatHistory.map((msg) => (
                    <MessageBubble
                        key={msg.id}
                        message={msg}
                        onUpdatePlan={handleUpdatePlan}
                        onConfirmPlan={handleConfirmPlan}
                    />
                ))}

                {isAnalyzing && chatHistory[chatHistory.length - 1]?.role !== 'agent' && (
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <div style={{
                            width: '28px', height: '28px', borderRadius: '50%',
                            background: '#7c3aed', display: 'flex', alignItems: 'center', justifyContent: 'center',
                            flexShrink: 0
                        }}>
                            <Bot size={16} color="white" />
                        </div>
                        <div style={{
                            background: '#f3f4f6', padding: '12px', borderRadius: '12px',
                            borderTopLeftRadius: '2px', color: '#374151', fontSize: '14px'
                        }}>
                            Thinking...
                        </div>
                    </div>
                )}
            </div>

            {/* Plan Preview Area */}
            {/* Plan Panel Removed - moved to MessageBubble */}

            {/* Input Area */}
            <div style={{ padding: '16px', background: 'white', borderTop: '1px solid #f3f4f6' }}>
                <div style={{
                    margin: '16px',
                    padding: '8px',
                    background: '#f9fafb',
                    borderRadius: '12px',
                    border: '1px solid #e5e7eb',
                    display: 'flex',
                    alignItems: 'flex-end',
                    gap: '8px'
                }}>


                    <textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="输入指令 (如：根据参考文档A填写企业简介)..."
                        style={{
                            flex: 1,
                            border: 'none',
                            background: 'transparent',
                            resize: 'none',
                            outline: 'none',
                            maxHeight: '120px',
                            padding: '8px 4px',
                            fontSize: '14px',
                            fontFamily: 'inherit',
                            lineHeight: '1.5'
                        }}
                        rows={1}
                        onInput={(e) => {
                            const target = e.target as HTMLTextAreaElement;
                            target.style.height = 'auto';
                            target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
                        }}
                    />

                    <button
                        onClick={handleSend}
                        disabled={!inputValue.trim() || isAnalyzing || isPlanning}
                        style={{
                            padding: '8px',
                            borderRadius: '8px',
                            border: 'none',
                            background: (!inputValue.trim() || isAnalyzing || isPlanning) ? '#e5e7eb' : '#7c3aed',
                            cursor: (!inputValue.trim() || isAnalyzing || isPlanning) ? 'not-allowed' : 'pointer',
                            color: 'white',
                            transition: 'background 0.2s'
                        }}
                    >
                        <ArrowUp size={20} />
                    </button>
                </div>
            </div>


        </div>
    );
};

interface MessageBubbleProps {
    message: FillerMessage;
    onUpdatePlan?: (msgId: string, plan: PlanStep[]) => void;
    onConfirmPlan?: (msgId: string, instruction: string | undefined, plan: PlanStep[]) => void;
}

const MessageBubble = ({ message, onUpdatePlan, onConfirmPlan }: MessageBubbleProps) => {
    const isUser = message.role === 'user';
    const isSystem = message.role === 'system';

    const handleStepChange = (idx: number, field: 'description' | 'tool_hint', value: string) => {
        if (!message.plan || !onUpdatePlan) return;
        const newPlan = [...message.plan];
        newPlan[idx] = { ...newPlan[idx], [field]: value };
        onUpdatePlan(message.id, newPlan);
    };

    const handleAddStep = (idx: number) => {
        if (!message.plan || !onUpdatePlan) return;
        const newPlan = [...message.plan];
        // Insert new step after current index
        newPlan.splice(idx + 1, 0, {
            step: 0, // Will reindex later
            description: "请在此输入步骤描述...",
            tool_hint: "execute_document_script"
        });
        // Reindex
        const reindexed = newPlan.map((s, i) => ({ ...s, step: i + 1 }));
        onUpdatePlan(message.id, reindexed);
    };

    const handleDeleteStep = (idx: number) => {
        if (!message.plan || !onUpdatePlan) return;
        const newPlan = [...message.plan];
        newPlan.splice(idx, 1);
        // Reindex
        const reindexed = newPlan.map((s, i) => ({ ...s, step: i + 1 }));
        onUpdatePlan(message.id, reindexed);
    };

    if (isSystem) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', fontSize: '12px', color: '#9ca3af' }}>
                {message.content}
            </div>
        );
    }

    const availableTools = [
        "execute_document_script",
        "find_anchor_in_word",
        "write_word_content",
        "read_source_content",
        "read_excel_summary",
        "copy_image_to_word"
    ];

    return (
        <div style={{
            display: 'flex',
            flexDirection: isUser ? 'row-reverse' : 'row',
            gap: '12px',
            alignItems: 'flex-start'
        }}>
            <div style={{
                width: '28px', height: '28px', borderRadius: '50%',
                background: isUser ? '#f3f4f6' : '#7c3aed',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
                color: isUser ? '#6b7280' : 'white',
                fontSize: '12px', fontWeight: 600
            }}>
                {isUser ? 'U' : <Bot size={16} />}
            </div>

            <div style={{ maxWidth: '85%', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{
                    padding: '12px',
                    borderRadius: '12px',
                    background: isUser ? '#7c3aed' : '#f3f4f6',
                    color: isUser ? 'white' : '#1f2937',
                    borderTopRightRadius: isUser ? '2px' : '12px',
                    borderTopLeftRadius: !isUser ? '2px' : '12px',
                    fontSize: '14px',
                    lineHeight: '1.5',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                }}>
                    <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>

                    {/* Review Critique */}
                    {message.status === 'review_failed' && (
                        <div style={{
                            marginTop: '8px',
                            padding: '8px',
                            background: '#fef2f2',
                            border: '1px solid #fecaca',
                            borderRadius: '6px',
                            color: '#991b1b',
                            fontSize: '13px'
                        }}>
                            <div style={{ fontWeight: 600, marginBottom: '4px' }}>⚠️ 质检不通过</div>
                            <div>{message.critique}</div>
                            {message.suggestion && (
                                <div style={{ marginTop: '4px', fontStyle: 'italic', color: '#b91c1c' }}>
                                    建议: {message.suggestion}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Plan Display in Bubble */}
                {message.plan && message.plan.length > 0 && (
                    <div style={{
                        marginTop: '8px',
                        padding: '12px',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        background: '#f9fafb',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px', fontSize: '13px', fontWeight: 600, color: '#374151' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <ListTodo size={14} />
                                <span>执行计划 {message.isInteractive ? '(可编辑)' : '(已确认)'}</span>
                            </div>
                            {message.isInteractive && (
                                <button
                                    onClick={() => handleAddStep(message.plan!.length - 1)}
                                    style={{
                                        fontSize: '11px', padding: '2px 8px', borderRadius: '4px',
                                        background: '#e0f2fe', color: '#0284c7', border: 'none', cursor: 'pointer'
                                    }}
                                >
                                    + 添加最后一步
                                </button>
                            )}
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {message.plan.map((step, idx) => (
                                <div key={idx} style={{
                                    display: 'flex', gap: '8px', fontSize: '13px',
                                    padding: '6px', borderRadius: '4px',
                                    background: 'white', border: '1px solid #f3f4f6',
                                    alignItems: 'start'
                                }}>
                                    <div style={{
                                        width: '16px', height: '16px', borderRadius: '50%',
                                        background: '#e0f2fe', color: '#0284c7',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        fontSize: '10px', flexShrink: 0, marginTop: '4px'
                                    }}>
                                        {step.step}
                                    </div>
                                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                        {message.isInteractive ? (
                                            <>
                                                <textarea
                                                    value={step.description}
                                                    onChange={(e) => handleStepChange(idx, 'description', e.target.value)}
                                                    placeholder="步骤描述"
                                                    style={{
                                                        width: '100%', border: '1px solid #e5e7eb',
                                                        borderRadius: '4px', padding: '4px',
                                                        minHeight: '24px', resize: 'vertical',
                                                        fontSize: '13px', fontFamily: 'inherit'
                                                    }}
                                                />
                                                <div style={{ display: 'flex', gap: '8px' }}>
                                                    <select
                                                        value={step.tool_hint}
                                                        onChange={(e) => handleStepChange(idx, 'tool_hint', e.target.value)}
                                                        style={{
                                                            fontSize: '11px', padding: '2px', border: '1px solid #e5e7eb',
                                                            borderRadius: '4px', background: '#f9fafb', color: '#4b5563',
                                                            maxWidth: '150px'
                                                        }}
                                                    >
                                                        {availableTools.map(t => (
                                                            <option key={t} value={t}>{t}</option>
                                                        ))}
                                                    </select>
                                                </div>
                                            </>
                                        ) : (
                                            <>
                                                <div style={{ color: '#4b5563' }}>{step.description}</div>
                                                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '2px' }}>
                                                    Tool: {step.tool_hint}
                                                </div>
                                            </>
                                        )}
                                    </div>

                                    {/* Action Buttons */}
                                    {message.isInteractive && (
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                            <button
                                                onClick={() => handleDeleteStep(idx)}
                                                title="删除此步骤"
                                                style={{
                                                    color: '#ef4444', background: 'none', border: 'none',
                                                    cursor: 'pointer', padding: '2px'
                                                }}
                                            >
                                                <X size={14} />
                                            </button>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>

                        {message.isInteractive && onConfirmPlan && (
                            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                                <button
                                    onClick={() => onConfirmPlan(message.id, message.instruction, message.plan!)}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: '4px',
                                        padding: '6px 12px', background: '#10b981', color: 'white',
                                        borderRadius: '6px', border: 'none', fontSize: '12px',
                                        cursor: 'pointer', fontWeight: 500
                                    }}
                                >
                                    <Play size={14} fill="currentColor" />
                                    确认执行
                                </button>
                            </div>
                        )}
                    </div>
                )}

                {/* Trace / Steps for Agent */}
                {message.trace && message.trace.length > 0 && (
                    <Trace logs={message.trace} />
                )}
            </div>
        </div>
    );
};

const Trace = ({ logs }: { logs: string[] }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    return (
        <div style={{ marginTop: '4px' }}>
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                style={{
                    display: 'flex', alignItems: 'center', gap: '4px',
                    background: 'none', border: 'none', padding: '0',
                    fontSize: '12px', color: '#6b7280', cursor: 'pointer'
                }}
            >
                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                查看执行步骤 ({logs.length})
            </button>

            {isExpanded && (
                <div style={{
                    marginTop: '4px',
                    padding: '8px',
                    background: '#f9fafb',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                    fontSize: '11px',
                    fontFamily: 'monospace',
                    color: '#4b5563',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px'
                }}>
                    {logs.map((log, idx) => (
                        <div key={idx} style={{ display: 'flex', gap: '6px', alignItems: 'flex-start' }}>
                            <span style={{ color: '#9ca3af', minWidth: '16px' }}>{idx + 1}.</span>
                            <span>{log}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};
