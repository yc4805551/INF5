import React, { useEffect, useRef, useState } from 'react';
import { UploadZone } from './UploadZone';
import { ChatPane } from './ChatPane'; // Reuse existing ChatPane
import { useWordCanvas } from './hooks/useWordCanvas';
import { ArrowLeft, FileText, RotateCcw, FilePlus, Download, Target, Trash2 } from 'lucide-react';
import './canvas.css'; // Reuse styles

export const WordCanvas: React.FC<{ onBack: () => void }> = ({ onBack }) => {
    const { state, handleFileUpload, handleReferenceUpload, handleSendMessage, handleSelection, clearSelection, reset, handleDownload, loadPage, toggleScope, handleRemoveReference, handleConfirm, handleDiscard } = useWordCanvas();
    const previewRef = useRef<HTMLDivElement>(null);
    const refFileInput = useRef<HTMLInputElement>(null);
    const [popupStyle, setPopupStyle] = useState<{ left: number, top: number } | null>(null);

    // ... (rest of useEffect)

    const totalPages = Math.ceil((state.totalParagraphs || 0) / (state.pageSize || 100));

    return (
        <div className="canvas-layout">
            {/* Sidebar for Structure */}
            {state.structure && state.structure.length > 0 && (
                <div className="canvas-toc-sidebar" style={{
                    width: '250px',
                    borderRight: '1px solid #ddd',
                    background: '#f9f9f9',
                    overflowY: 'auto',
                    padding: '10px'
                }}>
                    <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#666' }}>文档大纲</h3>
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                        {state.structure.map(item => {
                            const isActive = state.activeScope && state.activeScope.start === item.id;
                            return (
                                <li key={item.id} style={{
                                    padding: '4px 0',
                                    paddingLeft: `${(item.level - 1) * 12} px`,
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

            <div className="canvas-sidebar">
                <div className="canvas-header">
                    <div className="header-title-group">
                        <button onClick={onBack} className="back-btn" title="返回主页">
                            <ArrowLeft size={20} />
                        </button>
                        <h1 className="header-title">我的画布</h1>
                    </div>
                    <div className="header-actions" style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                        <button
                            className="action-btn"
                            onClick={reset}
                            title="重置画布"
                            style={{ padding: '4px 8px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                        >
                            <RotateCcw size={14} /> 重置
                        </button>
                        <button
                            className="action-btn"
                            onClick={handleDownload}
                            title="下载 Docx"
                            disabled={!state.hasFile}
                            style={{ padding: '4px 8px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                        >
                            <Download size={14} /> 下载
                        </button>
                        <button
                            className="action-btn"
                            onClick={() => refFileInput.current?.click()}
                            title={!state.hasFile ? "请先上传主文档" : "添加参考文件"}
                            disabled={!state.hasFile}
                            style={{ padding: '4px 8px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px', opacity: !state.hasFile ? 0.5 : 1 }}
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
                    <ChatPane
                        messages={state.messages}
                        onSendMessage={handleSendMessage}
                        isProcessing={state.isChatLoading || false}
                        selectionContext={state.selectionContext ? { text: state.selectionContext.text, ids: [state.selectionContext.id] } : null}
                        onClearSelection={() => { setPopupStyle(null); clearSelection(); }}
                        /* Confirmation Props */
                        isPendingConfirmation={state.isPendingConfirmation}
                        onConfirm={handleConfirm}
                        onDiscard={handleDiscard}
                    />
                )}
            </div>

            <div
                className="canvas-preview-area"
                style={{ position: 'relative', overflowY: 'auto' }}
                onScroll={(e) => {
                    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
                    // Trigger load more when near bottom (e.g., 50px threshold)
                    if (scrollHeight - scrollTop <= clientHeight + 50) {
                        if (!state.isProcessing && state.hasFile && (state.page * state.pageSize < state.totalParagraphs)) {
                            console.log("Loading more...", state.page + 1);
                            loadPage(state.page + 1, true); // Append
                        }
                    }
                }}
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
                            // Focus chat input or show hint
                            const chatInput = document.querySelector('textarea');
                            if (chatInput) (chatInput as HTMLElement).focus();
                        }}
                    >
                        <div className="ai-edit-btn">
                            ✨ AI 选中段落 {state.selectionContext.id}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
