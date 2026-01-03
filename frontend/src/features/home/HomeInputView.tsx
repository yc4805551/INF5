import React, { useEffect, useRef } from 'react';
import mammoth from 'mammoth';
import { ModelProvider, ExecutionMode } from '../../types';
import { getAvailableModels, MODEL_DISPLAY_NAMES } from '../../services/ai';

interface HomeInputViewProps {
    inputText: string;
    setInputText: React.Dispatch<React.SetStateAction<string>>;
    onOrganize: () => void;
    onAudit: () => void;
    selectedModel: ModelProvider;
    setSelectedModel: (model: ModelProvider) => void;
    isProcessing: boolean;
    knowledgeBases: { id: string; name: string }[];
    isKbLoading: boolean;
    kbError: string | null;
    selectedKnowledgeBase: string | null;
    setSelectedKnowledgeBase: (id: string) => void;
    onKnowledgeChat: () => void;
    onWriting: () => void;
    onTextRecognition: () => void;
    onCoCreation: () => void;
    onWordCanvas: () => void;
    executionMode: ExecutionMode;
    setExecutionMode: (mode: ExecutionMode) => void;
}

export const HomeInputView: React.FC<HomeInputViewProps> = ({
    inputText,
    setInputText,
    onOrganize,
    onAudit,
    selectedModel,
    setSelectedModel,
    isProcessing,
    knowledgeBases,
    isKbLoading,
    kbError,
    selectedKnowledgeBase,
    setSelectedKnowledgeBase,
    onKnowledgeChat,
    onWriting,
    onTextRecognition,
    onCoCreation,
    onWordCanvas,
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
                        ref={fileInputRef}
                        style={{ display: 'none' }}
                        accept=".txt,.md,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        onChange={handleFileChange}
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
                    <div className="config-group">
                        <h4>执行模式</h4>
                        <div className="model-selector-group">
                            <button
                                className={`model-btn ${executionMode === 'backend' ? 'active' : ''}`}
                                onClick={() => setExecutionMode('backend')}
                                disabled={isProcessing}
                            >
                                后端代理
                            </button>
                            <button
                                className={`model-btn ${executionMode === 'frontend' ? 'active' : ''}`}
                                onClick={() => setExecutionMode('frontend')}
                                disabled={isProcessing}
                            >
                                前端直连
                            </button>
                        </div>
                        {executionMode === 'frontend' && (
                            <p className="instruction-text">前端直连模式将直接在浏览器中调用 AI 服务。请确保已在环境中配置了相应模型的 API Keys。</p>
                        )}
                    </div>
                    <div className="config-group">
                        <h4>选择模型</h4>
                        <select
                            className="home-select"
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value as ModelProvider)}
                            disabled={isProcessing}
                        >
                            {availableModels.map(modelKey => (
                                <option key={modelKey} value={modelKey}>
                                    {MODEL_DISPLAY_NAMES[modelKey] || modelKey}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="config-group">
                        <h4>选择知识库</h4>
                        {isKbLoading && <div className="spinner-container" style={{ padding: '10px 0' }}><p>正在加载知识库...</p></div>}
                        {kbError && <div className="error-message" style={{ textAlign: 'left' }}>{kbError}</div>}
                        {!isKbLoading && !kbError && (
                            knowledgeBases.length > 0 ? (
                                <select
                                    className="home-select"
                                    value={selectedKnowledgeBase || ''}
                                    onChange={(e) => setSelectedKnowledgeBase(e.target.value)}
                                    disabled={isProcessing}
                                >
                                    <option value="" disabled>-- 请选择知识库 --</option>
                                    {knowledgeBases.map(kb => (
                                        <option key={kb.id} value={kb.id}>
                                            {kb.name}
                                        </option>
                                    ))}
                                </select>
                            ) : (
                                <p className="instruction-text">未找到可用的知识库。请检查后端服务和 Milvus 连接。</p>
                            )
                        )}
                    </div>
                </div>
            </div>
            <div className="home-actions-bar">
                <button className="action-btn" onClick={onOrganize} disabled={!inputText || isProcessing}>
                    1. 整理笔记
                </button>
                <button className="action-btn" onClick={onAudit} disabled={!inputText || isProcessing}>
                    2. 审阅文本
                </button>
                <button className="action-btn" onClick={onKnowledgeChat} disabled={!inputText || isProcessing || !selectedKnowledgeBase}>
                    3. 内参对话
                </button>
                <button className="action-btn" onClick={onWriting} disabled={isProcessing}>
                    4. 沉浸写作
                </button>
                <button className="action-btn" onClick={onTextRecognition} disabled={isProcessing}>
                    5. 文本识别
                </button>
                <button className="action-btn" onClick={onCoCreation} disabled={isProcessing}>
                    6. 共创画布
                </button>
                <button className="action-btn" onClick={onWordCanvas} disabled={isProcessing}>
                    7. 我的画布
                </button>
            </div>
        </>
    );
};
