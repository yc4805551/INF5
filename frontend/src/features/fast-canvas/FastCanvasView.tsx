import React, { useEffect, useState, useCallback, useRef } from 'react';
import { UnifiedAssistant } from './components/AIAssistant/UnifiedAssistant';
import { useFastCanvas } from './hooks/useFastCanvas';
import { useUnifiedAssistant } from './hooks/useUnifiedAssistant';
import { TiptapEditor, TiptapEditorRef } from './components/Editor/TiptapEditor';
import { AISuggestion } from './types';
import {
    ArrowLeft,
    Save,
    Download,
    FileText,
    CheckCircle,
    Clock
} from 'lucide-react';
import './FastCanvasView.css';

interface FastCanvasViewProps {
    onBack?: () => void;
    documentId?: string;
    modelProvider?: string;
}

export const FastCanvasView: React.FC<FastCanvasViewProps> = ({
    onBack,
    documentId,
    modelProvider
}) => {
    const [selectedText, setSelectedText] = useState<string>('');
    const [editorHtml, setEditorHtml] = useState<string>('');
    const [editorText, setEditorText] = useState<string>(''); // Plain text for AI

    // Ref for Tiptap Editor to access replaceText method
    const editorRef = useRef<TiptapEditorRef>(null);

    const {
        mode: assistantMode,
        setMode: setAssistantMode,
        isAnalyzing,
        suggestions,
        auditResult,
        analyzeRealtime,
        runAudit,
        clearSuggestions,
        removeSuggestion,
        chatHistory,
        sendChatMessage,
        lastCheckResult,
        smartWrite
    } = useUnifiedAssistant(modelProvider);

    const {
        document,
        isDirty,
        isSaving,
        createDocument,
        loadDocument,
        updateBlock,
        updateTitle,
        saveDocument,
        exportSmartDocx
    } = useFastCanvas();

    const [assistantWidth, setAssistantWidth] = useState(380);
    const [isResizing, setIsResizing] = useState(false);
    const sidebarRef = useRef<HTMLDivElement>(null);

    const startResizing = useCallback((e: React.MouseEvent) => {
        setIsResizing(true);
        e.preventDefault(); // Prevent text selection
    }, []);

    const stopResizing = useCallback(() => {
        setIsResizing(false);
    }, []);

    const resize = useCallback((e: MouseEvent) => {
        if (isResizing) {
            // Calculate new width: Window Width - Mouse X
            // This assumes right sidebar
            const newWidth = window.innerWidth - e.clientX;
            // Constraints
            if (newWidth > 200 && newWidth < 800) {
                setAssistantWidth(newWidth);
            }
        }
    }, [isResizing]);

    useEffect(() => {
        if (isResizing) {
            window.addEventListener('mousemove', resize);
            window.addEventListener('mouseup', stopResizing);
        }
        return () => {
            window.removeEventListener('mousemove', resize);
            window.removeEventListener('mouseup', stopResizing);
        };
    }, [isResizing, resize, stopResizing]);

    // 初始化
    useEffect(() => {
        if (documentId) {
            loadDocument(documentId);
        } else {
            createDocument();
        }
    }, [documentId, loadDocument, createDocument]);

    // 同步文档内容到编辑器 (Load initial content)
    useEffect(() => {
        if (document && document.content.length > 0 && !editorHtml) {
            // Document content is joined for the editor
            const content = document.content.map(b => b.text).join('<br/>');
            setEditorHtml(content);
            setEditorText(document.content.map(b => b.text).join('\n'));
        }
    }, [document, editorHtml]);

    // Handle Tiptap Updates
    const handleEditorChange = (html: string, text: string) => {
        setEditorHtml(html);
        setEditorText(text);

        // Auto-save logic (update first block)
        if (document?.content[0]) {
            updateBlock(document.content[0].id, { text: html });
        }
    };

    // Auto-trigger AI analysis
    useEffect(() => {
        // Only clear if switching OUT of realtime mode
        if (assistantMode !== 'realtime') {
            clearSuggestions();
            return;
        }

        if (!editorText || editorText.length < 10) return;

        // If there are pending suggestions, do NOT re-analyze.
        // Wait for the user to handle them (Apply/Dismiss) until the list is empty.
        if (suggestions.length > 0) return;

        const timer = setTimeout(() => {
            analyzeRealtime(editorText, editorText);
        }, 3000); // 3\u79d2\u9632\u6296\uff0c\u7528\u6237\u8981\u6c42\u505c\u987f\u540e\u518d\u68c0\u67e5

        return () => clearTimeout(timer);
    }, [editorText, assistantMode, analyzeRealtime, clearSuggestions, suggestions.length]);

    // Handlers
    const handleSave = () => saveDocument();

    // Call Smart Export
    const handleExportDocx = () => {
        exportSmartDocx();
    };

    const handleApplySuggestion = useCallback((suggestion: AISuggestion) => {
        if (editorRef.current) {
            if (!suggestion.original) {
                alert("无法定位原文：建议中缺少原文信息。");
                return;
            }
            const success = editorRef.current.replaceText(suggestion.original, suggestion.suggestion);
            if (success) {
                removeSuggestion(suggestion.id);
            } else {
                console.warn('Could not find text to replace:', suggestion.original);
                alert("无法定位原文，可能原文已被修改。已忽略该建议。");
                removeSuggestion(suggestion.id);
            }
        } else {
            console.warn('Editor ref not available');
        }
    }, [removeSuggestion]);

    const handleSuggestionClick = useCallback((id: string) => {
        // Find the card in the sidebar
        const element = window.document.getElementById(`suggestion-${id}`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            // Add a temporary highlight class
            element.classList.add('highlight-flash');
            setTimeout(() => {
                element.classList.remove('highlight-flash');
            }, 1000);
        } else {
            console.warn(`Suggestion card ${id} not found in sidebar.`);
        }
    }, []);

    const handleSuggestionSelect = useCallback((suggestion: AISuggestion) => {
        if (editorRef.current && suggestion.original) {
            editorRef.current.selectText(suggestion.original);
        }
    }, []);

    if (!document) {
        return <div className="fast-canvas-loading"><div className="loading-spinner" /><p>加载中...</p></div>;
    }

    return (
        <div className="fast-canvas-view">
            {/* Header */}
            <div className="fast-canvas-header">
                <div className="header-left">
                    {onBack && (
                        <button className="back-btn" onClick={onBack} title="返回">
                            <ArrowLeft size={20} />
                        </button>
                    )}
                    <FileText size={20} color="#3b82f6" />
                    <input
                        type="text"
                        className="document-title"
                        value={document.title}
                        onChange={(e) => updateTitle(e.target.value)}
                        placeholder="无标题文档"
                    />
                </div>

                <div className="header-right">
                    <div className="save-status">
                        {isSaving ? (
                            <><Clock size={14} /><span>保存中...</span></>
                        ) : isDirty ? (
                            <><Clock size={14} color="#f59e0b" /><span>未保存</span></>
                        ) : (
                            <><CheckCircle size={14} color="#10b981" /><span>已保存</span></>
                        )}
                    </div>

                    <button className="action-btn" onClick={handleSave} disabled={!isDirty || isSaving}>
                        <Save size={16} /><span>保存</span>
                    </button>

                    <button className="action-btn" onClick={handleExportDocx} title="导出为智能公文格式 (黑体/楷体/仿宋)">
                        <Download size={16} /><span>导出DOCX</span>
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="fast-canvas-body">
                {/* Tiptap Single Pane Editor */}
                <div className="fast-canvas-editor">
                    <TiptapEditor
                        ref={editorRef}
                        value={editorHtml}
                        onChange={handleEditorChange}
                        suggestions={suggestions}
                        onApplySuggestion={handleApplySuggestion}
                        onDismissSuggestion={removeSuggestion}
                        onSuggestionClick={handleSuggestionClick}
                    />
                </div>

                {/* AI Assistant */}
                <div
                    className="resize-handle"
                    onMouseDown={startResizing}
                    title="拖动调整宽度"
                />
                <div
                    className="fast-canvas-assistant"
                    ref={sidebarRef}
                    style={{ width: assistantWidth }}
                >
                    <UnifiedAssistant
                        mode={assistantMode}
                        onModeChange={setAssistantMode}
                        isAnalyzing={isAnalyzing}
                        suggestions={suggestions}
                        auditResult={auditResult}
                        onApplySuggestion={handleApplySuggestion}
                        onDismissSuggestion={removeSuggestion}
                        onRunAudit={(agents) => runAudit(editorText, undefined, undefined, agents)}
                        onSuggestionSelect={handleSuggestionSelect}
                        selectedText={selectedText}
                        chatHistory={chatHistory}
                        onSendMessage={(text) => sendChatMessage(text, editorText)}
                        lastCheckResult={lastCheckResult}
                        smartWrite={smartWrite}
                        onInsert={(text) => {
                            // Append text to editor
                            const newText = editorText + '\n\n' + text;
                            setEditorText(newText);
                            setEditorHtml(newText.replace(/\n/g, '<br/>'));
                            // Optional: notify success
                        }}
                    />
                </div>
            </div>

            <div className="fast-canvas-footer">
                <div className="stats">
                    <span>{editorText.split(/\s+/).filter(Boolean).length} 字</span>
                    <span className="divider">|</span>
                    <span>{editorText.length} 字符</span>
                </div>
            </div>
        </div>
    );
};
