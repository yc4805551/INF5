
import React, { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../../services/ai';
import { marked } from 'marked';

interface SmartFileViewProps {
    files: FileList | null;
    cleaningModelConfig: any; // { provider, model, apiKey, endpoint }
    ocrProvider?: string; // New prop for OCR selection
    onBack: () => void;
}

interface LogEntry {
    type: 'log' | 'result';
    message?: string;
    text?: string;
    timestamp: string;
}

export const SmartFileView: React.FC<SmartFileViewProps> = ({ files, cleaningModelConfig, ocrProvider, onBack }) => {
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [finalResult, setFinalResult] = useState<string>("");
    const [isProcessing, setIsProcessing] = useState(false);
    const logsEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (files && files.length > 0) {
            setSelectedFiles(prev => {
                const newFiles = Array.from(files);
                const existingNames = new Set(prev.map(f => f.name));
                const uniqueNewFiles = newFiles.filter(f => !existingNames.has(f.name));
                return [...prev, ...uniqueNewFiles];
            });
        }
    }, [files]);

    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const handleLocalFileSelect = (newFiles: FileList) => {
        const arr = Array.from(newFiles);
        setSelectedFiles(prev => {
            const existingNames = new Set(prev.map(f => f.name));
            const uniqueNewFiles = arr.filter(f => !existingNames.has(f.name));
            return [...prev, ...uniqueNewFiles];
        });
    };

    const startProcessing = async () => {
        if (selectedFiles.length === 0) return;
        setIsProcessing(true);
        setLogs([{ type: 'log', message: 'Starting upload and processing...', timestamp: new Date().toLocaleTimeString() }]);
        setFinalResult(""); // Clear previous results to prevent duplication

        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
            // Note: webkitdirectory uploads relative paths, but standard File object usually just has name.
            // For flat merging, filename is enough.
        });

        if (ocrProvider) {
            cleaningModelConfig.ocrProvider = ocrProvider;
        }
        formData.append('config', JSON.stringify(cleaningModelConfig));

        try {
            const response = await fetch(`${API_BASE_URL}/smart-file/process`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            if (!response.body) throw new Error("No response body");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const data = JSON.parse(line);
                        if (data.type === 'log') {
                            setLogs(prev => [...prev, { type: 'log', message: data.message, timestamp: new Date().toLocaleTimeString() }]);
                        } else if (data.type === 'result') {
                            setFinalResult(prev => prev + data.text);
                        }
                    } catch (e) {
                        console.error("Error parsing NDJSON:", e);
                    }
                }
            }

        } catch (err: any) {
            setLogs(prev => [...prev, { type: 'log', message: `Error: ${err.message}`, timestamp: new Date().toLocaleTimeString() }]);
        } finally {
            setIsProcessing(false);
            setLogs(prev => [...prev, { type: 'log', message: 'Processing finished.', timestamp: new Date().toLocaleTimeString() }]);
        }
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(finalResult);
        alert("已复制到剪贴板");
    };

    const handleDownload = () => {
        const blob = new Blob([finalResult], { type: 'text/markdown;charset=utf-8' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `Smart_Process_${new Date().toISOString().split('T')[0]}.md`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleDownloadTxt = () => {
        const blob = new Blob([finalResult], { type: 'text/plain;charset=utf-8' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `Smart_Process_${new Date().toISOString().split('T')[0]}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleReset = () => {
        setLogs([]);
        setFinalResult("");
        setSelectedFiles([]);
    };

    // Render Upload UI if no files are processing/processed yet
    if (logs.length === 0 && !isProcessing && finalResult === "") {
        return (
            <div className="smart-file-view" style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2>📂 智能文件处理 / 文本识别</h2>
                    {/* duplicate back button removed, main layout handles it */}
                </div>
                <div
                    className="upload-container"
                    style={{
                        padding: '40px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        alignItems: 'center',
                        border: '2px dashed #444',
                        borderRadius: '8px',
                        color: '#888',
                        gap: '20px'
                    }}
                    onDragOver={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = '#007bff'; }}
                    onDragLeave={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = '#444'; }}
                    onDrop={(e) => {
                        e.preventDefault();
                        e.currentTarget.style.borderColor = '#444';
                        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                            handleLocalFileSelect(e.dataTransfer.files);
                        }
                    }}
                >
                    <div style={{ fontSize: '3em' }}>☁️</div>
                    <p>拖放文件或文件夹到此处添加</p>
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <label className="btn btn-primary" style={{ cursor: 'pointer' }}>
                            添加文件
                            <input type="file" multiple style={{ display: 'none' }} onChange={(e) => { if (e.target.files) handleLocalFileSelect(e.target.files); e.target.value = ''; }} />
                        </label>
                        <label className="btn btn-secondary" style={{ cursor: 'pointer' }}>
                            添加文件夹
                            <input
                                type="file"
                                style={{ display: 'none' }}
                                onChange={(e) => { if (e.target.files) handleLocalFileSelect(e.target.files); e.target.value = ''; }}
                                ref={(el) => {
                                    if (el) {
                                        el.setAttribute('webkitdirectory', '');
                                        el.setAttribute('directory', '');
                                    }
                                }}
                            />
                        </label>
                    </div>
                </div>

                {selectedFiles.length > 0 && (
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '10px', overflow: 'hidden' }}>
                        <h3>已添加待处理的文件 ({selectedFiles.length})</h3>
                        <div style={{ flex: 1, overflowY: 'auto', background: '#1e1e1e', padding: '10px', borderRadius: '8px' }}>
                            <ul style={{ margin: 0, paddingLeft: '20px' }}>
                                {selectedFiles.slice(0, 100).map((f, i) => (
                                    <li key={i} style={{ color: '#ccc', marginBottom: '5px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.name}</li>
                                ))}
                                {selectedFiles.length > 100 && (
                                    <li style={{ color: '#888', fontStyle: 'italic', marginTop: '10px', listStyleType: 'none', marginLeft: '-20px', paddingLeft: '20px' }}>
                                        ...等其余 {selectedFiles.length - 100} 个文件
                                    </li>
                                )}
                            </ul>
                        </div>
                        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                            <button className="btn btn-secondary" onClick={() => setSelectedFiles([])}>清空列表</button>
                            <button className="btn btn-primary" onClick={startProcessing}>开始处理</button>
                        </div>
                    </div>
                )}
            </div>
        )
    }

    return (
        <div className="smart-file-view" style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>📂 智能文件处理 / 文本识别</h2>
                <div style={{ fontSize: '0.9em', color: '#888', display: 'flex', alignItems: 'center', gap: '15px' }}>
                    <span>Cleaning: {cleaningModelConfig?.provider || 'Default'} | OCR: Server Configured</span>
                    {!isProcessing && <button className="btn btn-secondary" onClick={handleReset}>继续添加 / 重新开始</button>}
                </div>
            </div>

            <div className="content-container" style={{ display: 'flex', gap: '20px', flex: 1, overflow: 'hidden' }}>
                {/* Left Panel: Logs */}
                <div className="logs-panel" style={{ flex: 1, background: '#1e1e1e', color: '#00ff00', padding: '15px', borderRadius: '8px', overflowY: 'auto', fontFamily: 'monospace' }}>
                    <h3>运行日志</h3>
                    {logs.map((log, idx) => (
                        <div key={idx} className="log-entry">
                            <span style={{ color: '#888', marginRight: '10px' }}>[{log.timestamp}]</span>
                            {log.message}
                        </div>
                    ))}
                    <div ref={logsEndRef} />
                </div>

                {/* Right Panel: Result Preview */}
                <div className="params-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--panel-background)', padding: '15px', borderRadius: '8px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                        <h3>结果预览</h3>
                        <div style={{ gap: '10px', display: 'flex' }}>
                            <button className="btn btn-secondary" onClick={handleCopy} disabled={!finalResult}>复制</button>
                            <button className="btn btn-primary" onClick={handleDownload} disabled={!finalResult}>下载 Markdown</button>
                            <button className="btn btn-primary" onClick={handleDownloadTxt} disabled={!finalResult}>下载 TXT</button>
                        </div>
                    </div>
                    <textarea
                        value={finalResult}
                        readOnly
                        style={{ flex: 1, width: '100%', resize: 'none', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--background-color)', color: 'var(--text-color)' }}
                        placeholder="处理结果将显示在这里..."
                    />
                </div>
            </div>
        </div>
    );
};
