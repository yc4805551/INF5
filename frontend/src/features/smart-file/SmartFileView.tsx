
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
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [finalResult, setFinalResult] = useState<string>("");
    const [isProcessing, setIsProcessing] = useState(false);
    const logsEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (files && files.length > 0 && !isProcessing && logs.length === 0) {
            startProcessing();
        }
    }, [files]);

    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const startProcessing = async () => {
        setIsProcessing(true);
        setLogs([{ type: 'log', message: 'Starting upload and processing...', timestamp: new Date().toLocaleTimeString() }]);

        const formData = new FormData();
        Array.from(files!).forEach(file => {
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

    return (
        <div className="smart-file-view" style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>📂 智能文件处理 (Smart Agent)</h2>
                <div style={{ fontSize: '0.9em', color: '#888' }}>
                    OCR Engine: {ocrProvider || 'Default'} | Cleaning: {cleaningModelConfig?.provider || 'Default'}
                </div>
                <button className="btn btn-secondary" onClick={onBack} disabled={isProcessing}>
                    返回首页
                </button>
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
