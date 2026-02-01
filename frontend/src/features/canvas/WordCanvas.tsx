import React, { useEffect, useRef, useState } from 'react';
import { UploadZone } from './UploadZone';
import { ChatPane, ChatPaneHandle } from './ChatPane'; // Reuse existing ChatPane
import { useWordCanvas } from './hooks/useWordCanvas';
import { useAdvisor } from './hooks/useAdvisor';
import { AuditPanel } from '../audit/AuditPanel';
import { useAudit } from '../audit/useAudit';
import { FillerPanel } from '../smart-filler/FillerPanel';
import { ArrowLeft, FileText, RotateCcw, FilePlus, Download, Target, Trash2, PanelLeft } from 'lucide-react';
import { ModelProvider } from '../../types';
import './canvas.css'; // Reuse styles

export const WordCanvas: React.FC<{ onBack: () => void, initialContent?: string, modelProvider?: ModelProvider }> = ({ onBack, initialContent, modelProvider = 'free' }) => {
    const { state, handleFileUpload, loadFromText, handleReferenceUpload, handleSendMessage, handleSelection, clearSelection, reset, handleDownload, loadPage, toggleScope, handleRemoveReference, handleConfirm, handleDiscard, handleFormat } = useWordCanvas();
    const previewRef = useRef<HTMLDivElement>(null);
    const chatPaneRef = useRef<ChatPaneHandle>(null);
    const refFileInput = useRef<HTMLInputElement>(null);
    const sidebarRef = useRef<HTMLDivElement>(null);
    const [popupStyle, setPopupStyle] = useState<{ left: number, top: number } | null>(null);
    const [showToc, setShowToc] = useState(false); // Default hidden as per user feedback
    const [activeTab, setActiveTab] = useState<'chat' | 'audit' | 'filler'>('chat');
    const [auditModel, setAuditModel] = useState<string>(modelProvider);

    // Advisor Hook
    const { suggestions, isAdvising, getSuggestions, clearSuggestions } = useAdvisor();

    // Auto-trigger Advisor on selection
    useEffect(() => {
        if (state.selectionContext && state.selectionContext.text.length > 5 && activeTab === 'chat') {
            const timer = setTimeout(() => {
                // Use global model provider
                const config = { provider: modelProvider, apiKey: '', endpoint: '', model: '' };
                getSuggestions(state.selectionContext!.text, state.htmlPreview, config);
            }, 800); // 800ms debounce
            return () => clearTimeout(timer);
        } else {
            clearSuggestions();
        }
    }, [state.selectionContext, activeTab, modelProvider]);

    const handleApplyAdvisorSuggestion = (text: string) => {
        // Use Chat flow to apply change: "Replace selection with [text]"
        // This ensures it goes through the Diff/Confirm flow
        handleSendMessage(`请将选中的内容修改为：\n${text}`, { provider: modelProvider });
    };

    // Audit Hook
    const { isAuditing, auditResults, runAudit: handleRunAudit } = useAudit();

    // Auto-load initial content
    const hasLoadedInitial = useRef(false);
    useEffect(() => {
        if (initialContent && !state.hasFile && !hasLoadedInitial.current) {
            hasLoadedInitial.current = true;
            loadFromText(initialContent);
        }
    }, [initialContent, state.hasFile, loadFromText]);

    // Sidebar Resizing
    const [sidebarWidth, setSidebarWidth] = useState(400);
    const [isResizing, setIsResizing] = useState(false);

    const startResizing = React.useCallback(() => {
        setIsResizing(true);
    }, []);

    const stopResizing = React.useCallback(() => {
        setIsResizing(false);
    }, []);

    const resize = React.useCallback(
        (mouseMoveEvent: MouseEvent) => {
            if (isResizing) {
                // Determine width based on relative position or explicit clientX
                // Assuming standard left-to-right layout where sidebar follows TOC
                let offset = 0;
                // If TOC is visible (width 250px)
                if (state.structure && state.structure.length > 0) offset += 250;

                // Calculate new width relative to the window/container
                const newWidth = mouseMoveEvent.clientX - offset;

                if (newWidth > 200 && newWidth < 800) {
                    setSidebarWidth(newWidth);
                }
            }
        },
        [isResizing, state.structure]
    );

    useEffect(() => {
        window.addEventListener("mousemove", resize);
        window.addEventListener("mouseup", stopResizing);
        return () => {
            window.removeEventListener("mousemove", resize);
            window.removeEventListener("mouseup", stopResizing);
        };
    }, [resize, stopResizing]);

    // Push Update Listener (Plan A)
    useEffect(() => {
        const handleRefreshSignal = () => {
            // Retrieve current page, force refresh with bust cache
            loadPage(state.page, false);
        };
        window.addEventListener('canvas-refresh', handleRefreshSignal);
        return () => window.removeEventListener('canvas-refresh', handleRefreshSignal);
    }, [state.page, loadPage]);

    // Text Selection Handler (Replaces Click)
    const handleTextSelection = (e: React.MouseEvent) => {
        const selection = window.getSelection();
        if (selection && selection.toString().trim().length > 0) {
            // Check if selection is within the document preview area
            const range = selection.getRangeAt(0);
            const container = range.commonAncestorContainer;

            // Find the closest parent with class 'docx-content'
            let parent: Node | null = container;
            let isInDocument = false;

            while (parent) {
                if (parent instanceof Element && parent.classList.contains('docx-content')) {
                    isInDocument = true;
                    break;
                }
                parent = parent.parentNode;
            }

            // Only process selection if it's within the document preview
            if (!isInDocument) {
                setPopupStyle(null);
                clearSelection();
                return;
            }

            const text = selection.toString().trim();
            const rect = range.getBoundingClientRect();

            // Calculate position relative to the container
            const wrapper = (e.currentTarget as HTMLElement).closest('.canvas-preview-area');
            if (wrapper) {
                const wrapperRect = wrapper.getBoundingClientRect();
                setPopupStyle({
                    left: rect.left + rect.width / 2 - wrapperRect.left,
                    top: rect.top - wrapperRect.top + wrapper.scrollTop - 40
                });

                // Use temp ID for context
                handleSelection(-1, text);
            }
        } else {
            // Clicked without selection -> Clear popup
            setPopupStyle(null);
            clearSelection();
        }
    };

    // Throttled Scroll Handler
    const handleScroll = React.useCallback((e: React.UIEvent<HTMLDivElement>) => {
        const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
        if (scrollHeight - scrollTop <= clientHeight + 50) {
            if (!state.isProcessing && state.hasFile && ((state.page * state.pageSize) < state.totalParagraphs)) {
                // Debounce/Throttle check
                const now = Date.now();
                // @ts-ignore
                if (now - (window.lastLoadTime || 0) > 1000) {
                    // console.log("Loading more...", state.page + 1);
                    loadPage(state.page + 1, true);
                    // @ts-ignore
                    window.lastLoadTime = now;
                }
            }
        }
    }, [state.isProcessing, state.hasFile, state.page, state.pageSize, state.totalParagraphs, loadPage]);

    return (
        <div className="canvas-layout">
            {/* Sidebar for Structure */}
            {showToc && state.structure && state.structure.length > 0 && (
                <div className="canvas-toc-sidebar" style={{
                    width: '250px',
                    borderRight: '1px solid #ddd',
                    background: '#f9f9f9',
                    overflowY: 'auto',
                    padding: '10px',
                    flexShrink: 0
                }}>
                    <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#666' }}>文档大纲</h3>
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                        {state.structure.map(item => {
                            const isActive = state.activeScope && state.activeScope.start === item.id;
                            return (
                                <li key={item.id} style={{
                                    padding: '4px 0',
                                    paddingLeft: `${(item.level - 1) * 12}px`,
                                    fontSize: '13px',
                                    color: isActive ? '#1890ff' : '#333',
                                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                    background: isActive ? '#e6f7ff' : 'transparent',
                                    borderRadius: '4px'
                                }}
                                    className="toc-item"
                                >
                                    <span
                                        style={{ cursor: 'pointer', flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
                                        onClick={() => loadPage(item.page)}
                                        title={item.title}
                                    >
                                        {item.title}
                                    </span>

                                    <button
                                        onClick={() => toggleScope(item)}
                                        title={isActive ? "取消聚焦" : "聚焦此章节 (AI处理范围)"}
                                        style={{
                                            background: 'none', border: 'none', cursor: 'pointer', padding: '0 4px',
                                            color: isActive ? '#1890ff' : '#ccc', display: 'flex', alignItems: 'center'
                                        }}
                                    >
                                        <Target size={14} />
                                    </button>
                                </li>
                            );
                        })}
                    </ul>
                </div>
            )}

            <div className="canvas-sidebar" ref={sidebarRef} style={{ width: sidebarWidth, position: 'relative', flexShrink: 0 }}>
                <div
                    className="sidebar-resizer"
                    onMouseDown={startResizing}
                    style={{
                        position: 'absolute',
                        right: 0,
                        top: 0,
                        width: '6px',
                        height: '100%',
                        cursor: 'col-resize',
                        zIndex: 100,
                    }}
                />
                <div className="canvas-header">
                    <div className="header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <div className="header-title-group" style={{ display: 'flex', alignItems: 'center' }}>
                            <button onClick={onBack} className="back-btn" title="返回主页">
                                <ArrowLeft size={20} />
                            </button>
                            <button
                                onClick={() => setShowToc(!showToc)}
                                className={`action-btn ${showToc ? 'active' : ''}`}
                                title={showToc ? "隐藏大纲" : "显示大纲"}
                                style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: '4px', marginLeft: '4px', color: showToc ? '#1890ff' : '#666' }}
                            >
                                <PanelLeft size={20} />
                            </button>
                            <h1 className="header-title" style={{ margin: '0 0 0 8px', fontSize: '16px' }}>我的画布</h1>
                        </div>
                        <div className="header-actions" style={{ display: 'flex', gap: '8px' }}>
                            <button
                                className="action-btn"
                                onClick={reset}
                                title="重置画布"
                                style={{ padding: '4px 8px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', border: '1px solid #ddd', borderRadius: '4px', background: '#fff' }}
                            >
                                <RotateCcw size={14} /> 重置
                            </button>
                            <button
                                className="action-btn"
                                onClick={handleDownload}
                                title="下载 Docx"
                                disabled={!state.hasFile}
                                style={{ padding: '4px 8px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', border: '1px solid #ddd', borderRadius: '4px', background: '#fff' }}
                            >
                                <Download size={14} /> 下载
                            </button>
                            <button
                                className="action-btn"
                                onClick={() => refFileInput.current?.click()}
                                title={!state.hasFile ? "请先上传主文档" : "添加参考文件"}
                                disabled={!state.hasFile}
                                style={{ padding: '4px 8px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', opacity: !state.hasFile ? 0.5 : 1, border: '1px solid #ddd', borderRadius: '4px', background: '#fff' }}
                            >
                                <FilePlus size={14} /> 添加参考
                            </button>
                            <input
                                type="file"
                                ref={refFileInput}
                                style={{ display: 'none' }}
                                onChange={(e) => {
                                    if (e.target.files && e.target.files[0]) {
                                        handleReferenceUpload(e.target.files[0]);
                                        e.target.value = ''; // Reset
                                    }
                                }}
                            />
                        </div>
                    </div>
                    {state.referenceFiles && state.referenceFiles.length > 0 && (
                        <div className="reference-list" style={{ marginTop: '8px', padding: '4px', borderTop: '1px solid #eee' }}>
                            <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>已加载:</div>
                            {state.referenceFiles.map((file, index) => (
                                <div key={`${file}-${index}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', background: '#f5f5f5', padding: '2px 6px', borderRadius: '4px', marginBottom: '2px' }}>
                                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '180px' }} title={file}>{`参考文件${index + 1}`}</span>
                                    <button onClick={() => handleRemoveReference(file)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#999', padding: '2px' }} title="移除">
                                        <Trash2 size={12} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
                {!state.hasFile ? (
                    <div className="upload-container">
                        <UploadZone onFileSelect={handleFileUpload} isUploading={state.isUploading} />
                    </div>
                ) : (
                    <>
                        <div className="sidebar-tabs" style={{ display: 'flex', borderBottom: '1px solid #eee', padding: '0 8px' }}>
                            <button
                                onClick={() => setActiveTab('chat')}
                                style={{
                                    padding: '8px 16px',
                                    border: 'none',
                                    background: 'none',
                                    borderBottom: activeTab === 'chat' ? '2px solid #0284c7' : 'none',
                                    color: activeTab === 'chat' ? '#0284c7' : '#666',
                                    fontWeight: activeTab === 'chat' ? 500 : 400,
                                    cursor: 'pointer'
                                }}
                            >
                                写作助手
                            </button>
                            <button
                                onClick={() => setActiveTab('audit')}
                                style={{
                                    padding: '8px 16px',
                                    border: 'none',
                                    background: 'none',
                                    borderBottom: activeTab === 'audit' ? '2px solid #0284c7' : 'none',
                                    color: activeTab === 'audit' ? '#0284c7' : '#666',
                                    fontWeight: activeTab === 'audit' ? 500 : 400,
                                    cursor: 'pointer'
                                }}
                            >
                                审阅润色
                            </button>
                            <button
                                onClick={() => setActiveTab('filler')}
                                style={{
                                    padding: '8px 16px',
                                    border: 'none',
                                    background: 'none',
                                    borderBottom: activeTab === 'filler' ? '2px solid #0284c7' : 'none',
                                    color: activeTab === 'filler' ? '#0284c7' : '#666',
                                    fontWeight: activeTab === 'filler' ? 500 : 400,
                                    cursor: 'pointer'
                                }}
                            >
                                智能填充
                            </button>
                        </div>

                        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                            {activeTab === 'chat' ? (
                                <ChatPane
                                    ref={chatPaneRef}
                                    onSendMessage={handleSendMessage}
                                    isProcessing={state.isProcessing || state.isChatLoading || false}
                                    isPendingConfirmation={state.isPendingConfirmation}
                                    onConfirm={handleConfirm}
                                    onDiscard={handleDiscard}
                                    onFormat={handleFormat}
                                    showBodyFormatDialog={false} // Todo
                                    messages={state.messages}
                                    selectionContext={state.selectionContext ? { text: state.selectionContext.text, ids: [state.selectionContext.id] } : null}
                                    onClearSelection={clearSelection}
                                    // Advisor
                                    advisorSuggestions={suggestions}
                                    isAdvising={isAdvising}
                                    onApplySuggestion={handleApplyAdvisorSuggestion}
                                />
                            ) : activeTab === 'audit' ? (
                                <AuditPanel
                                    referenceFiles={state.referenceFiles || []}
                                    onRunAudit={(rules) => handleRunAudit(rules, auditModel)}
                                    isAuditing={isAuditing}
                                    results={auditResults}
                                    selectedModel={auditModel}
                                    onModelChange={setAuditModel}
                                />
                            ) : (
                                <FillerPanel
                                    onRefresh={() => loadPage(state.page, false)}
                                    onUploadReference={handleReferenceUpload}
                                />
                            )}
                        </div>
                    </>
                )}
            </div>

            <div
                className="canvas-preview-area"
                style={{ position: 'relative', overflowY: 'auto', flex: 1 }}
                onScroll={handleScroll}
            >
                {/* Scroll Status / Loading Indicator */}
                {state.isProcessing && (
                    <div style={{ position: 'sticky', top: 0, width: '100%', background: '#fff9c4', textAlign: 'center', fontSize: '12px', padding: '2px', zIndex: 10 }}>
                        加载中... (第 {state.page + 1} 页)
                    </div>
                )}

                {state.htmlPreview ? (
                    <div
                        ref={previewRef}
                        className="docx-content"
                        dangerouslySetInnerHTML={{ __html: state.htmlPreview }}
                        onMouseUp={handleTextSelection}
                        style={{ cursor: 'text' }}
                    />
                ) : (
                    <div className="document-empty">
                        <p>请上传文档进行预览</p>
                    </div>
                )}

                {state.selectionContext && popupStyle && (
                    <div
                        className="ai-edit-popup"
                        style={{
                            position: 'absolute',
                            left: popupStyle.left,
                            top: popupStyle.top,
                            transform: 'translateX(-50%)',
                            background: '#333',
                            color: 'white',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '12px',
                            cursor: 'pointer',
                            zIndex: 1000
                        }}
                        onClick={() => {
                            if (chatPaneRef.current) {
                                chatPaneRef.current.setInput(`请优化这段内容：\n> ${state.selectionContext?.text}\n\n我的修改意见：`);
                                chatPaneRef.current.focus();
                            }
                        }}
                    >
                        <div className="ai-edit-btn">
                            ✨ AI 精修 (选区)
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
