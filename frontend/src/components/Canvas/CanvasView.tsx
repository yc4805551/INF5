import React from 'react';
import { UploadZone } from './UploadZone';
import { PreviewPane } from './PreviewPane';
import { ChatPane } from './ChatPane';
import { Download, FileText, ArrowLeft } from 'lucide-react';
import { useDocxEditor } from './hooks/useDocxEditor';
import './canvas.css'; // We will create this file for specific styles

export const CanvasView: React.FC<{ onBack: () => void }> = ({ onBack }) => {
    const {
        state,
        handleFileUpload,
        handleSendMessage,
        handleConfirm,
        handleDiscard,
        handleFormat,
        handleDownload,
        reset,
        handleBodyFormatConfirm,
        handleBodyFormatCancel,
        handleSelectionEdit,
        handleClearSelection,
        handleReferenceUpload
    } = useDocxEditor();

    const { previewData, isUploading, isProcessing, hasFile, isPendingConfirmation } = state;

    return (
        <div className="canvas-layout">
            {/* Sidebar / Chat */}
            <div className="canvas-sidebar">
                <div className="canvas-header">
                    <div className="header-title-group">
                        <button onClick={onBack} className="back-btn" title="返回主页">
                            <ArrowLeft size={20} />
                        </button>
                        <div className="icon-wrapper">
                            <FileText className="text-white" size={20} />
                        </div>
                        <h1 className="header-title">智能画布</h1>
                    </div>
                    {hasFile && (
                        <div className="header-actions">
                            <label className="icon-btn secondary" title="上传参考资料">
                                <input
                                    type="file"
                                    accept=".docx"
                                    style={{ display: 'none' }}
                                    onChange={(e) => {
                                        if (e.target.files?.[0]) {
                                            handleReferenceUpload(e.target.files[0]);
                                            e.target.value = ''; // Reset
                                        }
                                    }}
                                />
                                <span style={{ fontSize: '12px', fontWeight: 'bold' }}>+参考</span>
                            </label>
                            <button
                                onClick={reset}
                                className="icon-btn danger"
                                title="重新上传"
                            >
                                <FileText size={20} />
                            </button>
                            <button
                                onClick={handleDownload}
                                className="icon-btn primary"
                                title="下载文档"
                            >
                                <Download size={20} />
                            </button>
                        </div>
                    )}
                </div>

                {!hasFile ? (
                    <div className="upload-container">
                        <UploadZone onFileSelect={handleFileUpload} isUploading={isUploading} />
                    </div>
                ) : (
                    <ChatPane
                        onSendMessage={handleSendMessage}
                        isProcessing={isProcessing}
                        isPendingConfirmation={isPendingConfirmation}
                        onConfirm={handleConfirm}
                        onDiscard={handleDiscard}
                        onFormat={handleFormat}
                        showBodyFormatDialog={state.showBodyFormatDialog}
                        onBodyFormatConfirm={handleBodyFormatConfirm}
                        onBodyFormatCancel={handleBodyFormatCancel}
                        messages={state.messages}
                        selectionContext={state.selectionContext}
                        onClearSelection={handleClearSelection}
                    />
                )}
            </div>

            {/* Main Preview Area */}
            <div className="canvas-preview-area">
                <PreviewPane
                    paragraphs={previewData}
                    onSelectionEdit={handleSelectionEdit}
                />
            </div>
        </div>
    );
};
