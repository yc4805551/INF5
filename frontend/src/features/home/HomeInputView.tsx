import React, { useEffect, useRef } from 'react';
import mammoth from 'mammoth';
import { ModelProvider, ExecutionMode } from '../../types';
import { getAvailableModels, MODEL_DISPLAY_NAMES } from '../../services/ai';

interface HomeInputViewProps {
    inputText: string;
    setInputText: React.Dispatch<React.SetStateAction<string>>;
    onOrganize: () => void;
    selectedModel: ModelProvider;
    setSelectedModel: (model: ModelProvider) => void;
    isProcessing: boolean;
    knowledgeBases: { id: string; name: string }[];
    isKbLoading: boolean;
    kbError: string | null;
    selectedKnowledgeBase: string | null;
    setSelectedKnowledgeBase: (id: string) => void;
    onKnowledgeChat: () => void;
    onTextRecognition: () => void;
    onWordCanvas: () => void;
    onFastCanvas: () => void;
    onFileSearch: () => void;
    onConnectAnythingLLM: () => void;
    onConnectMilvus: () => void;
    isAnythingLoading?: boolean;
    isMilvusLoading?: boolean;
    executionMode: ExecutionMode;
    setExecutionMode: (mode: ExecutionMode) => void;
}

export const HomeInputView: React.FC<HomeInputViewProps> = ({
    inputText,
    setInputText,
    onOrganize,
    selectedModel,
    setSelectedModel,
    isProcessing,
    knowledgeBases,
    isKbLoading,
    kbError,
    selectedKnowledgeBase,
    setSelectedKnowledgeBase,
    onKnowledgeChat,
    onTextRecognition,
    onWordCanvas,
    onFastCanvas,
    onFileSearch,
    onConnectAnythingLLM,
    onConnectMilvus,
    isAnythingLoading,
    isMilvusLoading,
    executionMode,
    setExecutionMode,
}) => {
    const availableModels = getAvailableModels();
    const lastPastedText = useRef('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        const handleFocus = async () => {
            if (document.hasFocus()) {
                try {
                    const text = await navigator.clipboard.readText();
                    if (text && text !== lastPastedText.current && text !== inputText) {
                        setInputText(prev => prev ? `${prev}\n\n${text}` : text);
                        lastPastedText.current = text;
                    }
                } catch (err) {
                    // Clipboard permission denied or empty
                }
            }
        };

        window.addEventListener('focus', handleFocus);
        return () => {
            window.removeEventListener('focus', handleFocus);
        };
    }, [inputText, setInputText]);

    const processFile = async (file: File) => {
        if (!file) return;
        const reader = new FileReader();

        reader.onload = async (event) => {
            const fileContent = event.target?.result;
            let text = '';
            if (file.name.endsWith('.docx')) {
                try {
                    const result = await mammoth.extractRawText({ arrayBuffer: fileContent as ArrayBuffer });
                    text = result.value;
                } catch (err) {
                    console.error("Error reading docx file", err);
                    alert("无法解析 DOCX 文件。");
                    return;
                }
            } else {
                text = fileContent as string;
            }
            setInputText(prev => prev ? `${prev}\n\n--- ${file.name} ---\n${text}` : text);
        };

        if (file.name.endsWith('.docx')) {
            reader.readAsArrayBuffer(file);
        } else if (file.name.endsWith('.txt') || file.name.endsWith('.md')) {
            reader.readAsText(file);
        } else {
            alert("不支持的文件类型。请上传 .txt, .md 或 .docx 文件。");
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) {
            processFile(e.target.files[0]);
            e.target.value = '';
        }
    };

    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    const handleDragOver = (e: React.DragEvent<HTMLTextAreaElement>) => {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.add('drag-over');
    };

    const handleDragLeave = (e: React.DragEvent<HTMLTextAreaElement>) => {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.remove('drag-over');
    };

    const handleDrop = async (e: React.DragEvent<HTMLTextAreaElement>) => {
        e.preventDefault();
        e.stopPropagation();
        e.currentTarget.classList.remove('drag-over');

        if (e.dataTransfer.files?.[0]) {
            await processFile(e.dataTransfer.files[0]);
            e.dataTransfer.clearData();
        }
    };



    return (
        <>
            <div className="home-grid-layout">
                <div className="home-panel">
                    <h2>工作区</h2>
                    <textarea
                        className="text-area"
                        id="main-input-area"
                        name="mainInput"
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        placeholder="在此处输入或拖放 .txt, .md, .docx 文件...&#10;从别处复制后，返回此页面可自动粘贴"
                        disabled={isProcessing}
                        style={{ flexGrow: 1 }}
                    />
                    <input
                        type="file"
                        id="hidden-file-input"
                        name="hiddenFileInput"
                        ref={fileInputRef}
                        style={{ display: 'none' }}
                        accept=".txt,.md,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        onChange={handleFileChange}
                        title="Upload File"
                    />
                    <div className="utility-btn-group">
                        <button className="btn btn-secondary" onClick={() => setInputText('')} disabled={!inputText || isProcessing}>
                            清空内容
                        </button>
                        <button className="btn btn-secondary" onClick={handleUploadClick} disabled={isProcessing}>
                            上传文件
                        </button>
                    </div>
                </div>
                <div className="home-panel">
                    <h2>全局配置</h2>
                    {/* Execution Mode Toggle Removed - Defaulting to Backend for simplicity */}
                    {/* <div className="config-group">
                        <h4>执行模式</h4>
                        ...
                    </div> */}
                    <div className="config-group">
                        <h4>选择模型</h4>
                        <select
                            className="home-select"
                            id="model-selector"
                            name="modelSelect"
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value as ModelProvider)}
                            disabled={isProcessing}
                            title="选择模型"
                        >
                            {availableModels.map(modelKey => (
                                <option key={modelKey} value={modelKey}>
                                    {MODEL_DISPLAY_NAMES[modelKey] || modelKey}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="config-group">
                        <h4>知识库连接</h4>
                        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
                            <button
                                className="btn btn-secondary"
                                onClick={onConnectMilvus}
                                disabled={isMilvusLoading || isKbLoading}
                                style={{ flex: 1 }}
                            >
                                {isMilvusLoading ? '⏳ 连接中...' : '🗄️ 连接 Milvus'}
                            </button>
                            <button
                                className="btn btn-primary"
                                onClick={onConnectAnythingLLM}
                                disabled={isAnythingLoading || isKbLoading}
                                style={{ flex: 1 }}
                            >
                                {isAnythingLoading ? '⏳ 连接中...' : '🔌 连接 AnythingLLM'}
                            </button>
                        </div>

                        <h4>选择知识库</h4>
                        {kbError && !isKbLoading && <div className="error-message" style={{ textAlign: 'left', marginBottom: '5px' }}>{kbError}</div>}

                        <select
                            className="home-select"
                            id="kb-selector"
                            name="kbSelect"
                            value={selectedKnowledgeBase || ''}
                            onChange={(e) => setSelectedKnowledgeBase(e.target.value)}
                            disabled={isProcessing || knowledgeBases.length === 0}
                            title="选择知识库"
                        >
                            <option value="" disabled>-- 请选择知识库 --</option>
                            {knowledgeBases.map(kb => (
                                <option key={kb.id} value={kb.id}>
                                    {kb.name}
                                </option>
                            ))}
                        </select>
                        {knowledgeBases.length === 0 && !isKbLoading && (
                            <p className="instruction-text" style={{ marginTop: '5px' }}>暂无可用知识库，请先点击连接。</p>
                        )}
                    </div>
                </div>
            </div>
            <div className="home-actions-bar">
                <button className="action-btn" onClick={onOrganize} disabled={!inputText || isProcessing}>
                    1. 整理笔记
                </button>
                <button className="action-btn" onClick={onKnowledgeChat} disabled={!inputText || isProcessing || !selectedKnowledgeBase}>
                    2. 内参对话
                </button>
                <button className="action-btn" onClick={onTextRecognition} disabled={isProcessing}>
                    3. 文本识别
                </button>
                <button className="action-btn" onClick={onWordCanvas} disabled={isProcessing}>
                    4. 我的画布 (DOCX)
                </button>
                <button className="action-btn" onClick={onFastCanvas} disabled={isProcessing}>
                    5. 快速画布 ⚡
                </button>
                <button className="action-btn" onClick={onFileSearch} disabled={isProcessing}>
                    6. 文件搜索 🔍
                </button>
            </div>
        </>
    );
};
