import React, { useState } from 'react';
import { smartSearch, smartSearchStream, openFileLocation, copyTextToClipboard, SmartSearchResult } from './smartSearchApi';
import './SmartSearchPage.css';

/**
 * AI 智能文件搜索页面 - 增强版
 */
interface SmartSearchPageProps {
    modelProvider?: string;
}

export const SmartSearchPage: React.FC<SmartSearchPageProps> = ({ modelProvider }) => {
    const [query, setQuery] = useState('');
    const [rawResults, setRawResults] = useState<SmartSearchResult[]>([]);
    const [finalResults, setFinalResults] = useState<SmartSearchResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [searchStep, setSearchStep] = useState<'idle' | 'intent' | 'searching' | 'filtering' | 'done'>('idle');
    const [statusMessage, setStatusMessage] = useState('');
    const [logs, setLogs] = useState<string[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [aiAnalysis, setAiAnalysis] = useState<string>('');
    const [intentData, setIntentData] = useState<any>(null);

    // UI State
    const [hasSearched, setHasSearched] = useState(false);

    const logsEndRef = React.useRef<HTMLDivElement>(null);

    // Auto scroll logs
    React.useEffect(() => {
        if (logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs]);

    // 执行搜索
    const handleSearch = async (e?: React.FormEvent) => {
        e?.preventDefault();

        if (!query.trim()) return;

        // Reset State
        setIsSearching(true);
        setHasSearched(true);
        setSearchStep('intent');
        setRawResults([]);
        setFinalResults([]);
        setLogs([]);
        setError(null);
        setAiAnalysis('');
        setIntentData(null);
        setStatusMessage('正在初始化 AI 搜索助手...');

        try {
            await smartSearchStream(query, {
                onStatus: (msg, step) => {
                    setStatusMessage(msg);
                    setSearchStep(step as any);
                },
                onLog: (msg) => {
                    setLogs(prev => [...prev, msg].slice(-5)); // Keep last 5 logs
                },
                onIntent: (data) => {
                    setIntentData(data);
                },
                onResultChunk: (chunk, strategy) => {
                    // 立即展示结果
                    setRawResults(prev => {
                        // 去重
                        const newPaths = new Set(chunk.map(c => c.path));
                        const existing = prev.filter(p => !newPaths.has(p.path));
                        return [...existing, ...chunk];
                    });
                },
                onFinalResults: (results) => {
                    setFinalResults(results);
                    setSearchStep('done');
                },
                onAnalysis: (text) => {
                    setAiAnalysis(text);
                },
                onError: (err) => {
                    setError(err);
                    setIsSearching(false);
                }
            }, {
                modelProvider,
                maxResults: 500 // Increased from default 20
            });

        } catch (err: any) {
            setError(err.message || '搜索出错');
        } finally {
            setIsSearching(false);
        }
    };

    // 获取路径分隔符
    const getSeparator = (path: string) => path.includes('/') ? '/' : '\\';

    // 获取完整路径
    const getFullPath = (file: SmartSearchResult) => {
        if (!file.path) return '';
        if (file.path.endsWith(file.name)) return file.path;
        const sep = getSeparator(file.path);
        return file.path.endsWith(sep) ? file.path + file.name : file.path + sep + file.name;
    };

    // 打开文件/文件夹
    const handleOpen = async (file: SmartSearchResult, type: 'folder' | 'open') => {
        try {
            const fullPath = getFullPath(file);
            const success = await openFileLocation(fullPath);
            if (!success) alert('无法打开位置');
        } catch (e) {
            console.error(e);
        }
    };

    // 复制路径
    const handleCopy = async (file: SmartSearchResult) => {
        const fullPath = getFullPath(file);
        const success = await copyTextToClipboard(fullPath);
        if (!success) {
            try {
                await navigator.clipboard.writeText(fullPath);
            } catch (e) {
                alert('复制失败，请手动复制');
            }
        }
    };

    // 格式化文件大小
    const formatSize = (bytes?: number) => {
        if (!bytes) return '';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    // 格式化日期 (兼容 Windows FileTime 和普通字符串)
    const formatFileDate = (dateStr?: string | number) => {
        if (!dateStr) return '';
        const str = String(dateStr);

        // 这是一个 Windows FileTime (100-ns intervals since 1601-01-01)
        // 比如 133680757884374872
        // 通常是 18 位数字
        if (/^\d{17,19}$/.test(str)) {
            try {
                // Windows FileTime to Unix Timestamp (milliseconds)
                // (FileTime - 116444736000000000) / 10000
                const fileTime = BigInt(str);
                const unixMs = Number((fileTime - 116444736000000000n) / 10000n);
                const date = new Date(unixMs);

                // 格式化为 YYYY-MM-DD
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                return `${year}-${month}-${day}`;
            } catch (e) {
                return str;
            }
        }

        // 也是常见的 Unix timestamp (milliseconds) 13位
        if (/^\d{13}$/.test(str)) {
            try {
                const date = new Date(Number(str));
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                return `${year}-${month}-${day}`;
            } catch (e) {
                return str;
            }
        }

        // 默认处理: 2024-01-01 12:00:00 -> 2024-01-01
        return str.split(' ')[0];
    };

    // 结果列表：如果有最终结果，显示最终结果，否则显示实时结果
    const displayResults = finalResults.length > 0 ? finalResults : rawResults;

    return (
        <div className={`smart-search-page ${hasSearched ? 'results-mode' : 'landing-mode'}`}>

            {/* Header / Search Bar Transition */}
            <div className="search-section">
                <div className="title-area">
                    <h1>AI 文件深度搜索</h1>
                    {!hasSearched && <p className="subtitle">多策略并行检索 · 智能语义理解 · 自动聚合结果</p>}
                </div>

                <form onSubmit={handleSearch} className="search-box-wrapper">
                    <div className="search-input-container">
                        <input
                            type="text"
                            className="search-input"
                            placeholder="描述你要找的文件，例如：'找一下最近关于大模型落地的PPT'..."
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            disabled={isSearching && searchStep === 'intent'} // Only disable during init
                            autoFocus
                        />
                        <button type="submit" className="search-button" disabled={!query.trim()}>
                            {isSearching ? <span className="spinner small"></span> : '🔍'}
                        </button>
                    </div>
                </form>

                {/* Real-time Status Log */}
                {(isSearching || logs.length > 0) && (
                    <div className="status-log-container">
                        <div className="status-header">
                            <span className={`status-dot ${isSearching ? 'pulsing' : ''}`}></span>
                            <span className="status-text">{statusMessage}</span>
                        </div>
                        {logs.length > 0 && (
                            <div className="logs-scroller">
                                {logs.map((log, i) => (
                                    <div key={i} className="log-item">
                                        <span className="log-arrow">›</span> {log}
                                    </div>
                                ))}
                                <div ref={logsEndRef} />
                            </div>
                        )}
                    </div>
                )}
            </div>

            {hasSearched && (
                <div className="results-section">
                    {/* AI Analysis Card (Compact) */}
                    {(aiAnalysis || intentData) && (
                        <div className="ai-insight-card compact">
                            <div className="insight-content">
                                {aiAnalysis ? (
                                    <span className="analysis-text">💡 {aiAnalysis}</span>
                                ) : (
                                    <span className="analysis-text">🚀 正在全力搜索中... 已发现 {rawResults.length} 个文件</span>
                                )}
                                {intentData && (
                                    <div className="intent-tags inline">
                                        {intentData.strategies?.map((s: any, i: number) => (
                                            <span key={i} className="strategy-tag">{s.desc}</span>
                                        ))}
                                        {intentData.file_types?.length > 0 && (
                                            <span className="strategy-tag file-type-tag">
                                                Types: {intentData.file_types.join(', ')}
                                            </span>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {error && <div className="error-box">⚠️ {error}</div>}

                    {/* Results List View */}
                    <div className="results-list-header">
                        <div className="col-icon">类型</div>
                        <div className="col-name">名称 / 路径</div>
                        <div className="col-date">修改日期</div>
                        <div className="col-size">大小</div>
                        <div className="col-actions">操作</div>
                    </div>

                    <div className="results-list">
                        {displayResults.map((file, index) => (
                            <div key={`${file.path}-${index}`} className={`result-row ${file.score && file.score > 80 ? 'high-score' : ''}`}>

                                <div className="col-icon">
                                    {file.name.endsWith('.ppt') || file.name.endsWith('.pptx') ? '📊' :
                                        file.name.endsWith('.doc') || file.name.endsWith('.docx') ? '📝' :
                                            file.name.endsWith('.pdf') ? '📕' :
                                                file.name.endsWith('.xls') || file.name.endsWith('.xlsx') ? '📗' :
                                                    file.name.endsWith('.zip') || file.name.endsWith('.rar') ? '📦' : '📄'}
                                </div>

                                <div className="col-name">
                                    <div className="file-name-row">
                                        <span
                                            className="file-name"
                                            title={file.name}
                                            dangerouslySetInnerHTML={{
                                                __html: file.name.replace(new RegExp(`(${query.split('').join('|')})`, 'gi'), '<mark>$1</mark>')
                                            }}
                                        />
                                        {file.score && file.score > 80 && <span className="score-badge">✨ 推荐</span>}
                                        {file.reason && <span className="ai-reason-badge" title={file.reason}>🎯 AI</span>}
                                    </div>
                                    <div className="file-path" title={file.path}>{getFullPath(file)}</div>
                                </div>

                                <div className="col-date">
                                    {formatFileDate(file.date_modified)}
                                </div>

                                <div className="col-size">
                                    {formatSize(file.size)}
                                </div>

                                <div className="col-actions">
                                    <button onClick={() => handleOpen(file, 'open')} title="在服务器打开 (Open on Server)">📂</button>
                                    <button onClick={() => {
                                        // 远程预览/下载
                                        const encodedPath = encodeURIComponent(file.path);
                                        window.open(`/api/file-search/preview?path=${encodedPath}`, '_blank');
                                    }} title="预览/下载 (Preview/Download)">👁️</button>
                                    <button onClick={() => handleCopy(file)} title="复制路径">📋</button>
                                </div>
                            </div>
                        ))}
                    </div>

                    {!isSearching && displayResults.length === 0 && (
                        <div className="empty-state">
                            <p>🔍 这里空空如也...</p>
                        </div>
                    )}
                </div>

            )}
        </div>
    );
};
