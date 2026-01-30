import React, { useState } from 'react';
import { smartSearch, openFileLocation, copyTextToClipboard, SmartSearchResult } from './smartSearchApi';
import './SmartSearchPage.css';

/**
 * AI 智能文件搜索页面 - 增强版
 */
interface SmartSearchPageProps {
    modelProvider?: string;
}

export const SmartSearchPage: React.FC<SmartSearchPageProps> = ({ modelProvider }) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SmartSearchResult[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [aiAnalysis, setAiAnalysis] = useState<string>('');
    const [intent, setIntent] = useState<string>('');
    const [strategies, setStrategies] = useState<string[]>([]);

    // 执行搜索
    const handleSearch = async (e?: React.FormEvent) => {
        e?.preventDefault();

        if (!query.trim()) {
            setError('请输入搜索内容');
            return;
        }

        setIsLoading(true);
        setError(null);
        setResults([]);
        setAiAnalysis('');
        setIntent('');
        setStrategies([]);

        try {
            // 模拟 AI 思考过程 (可选：实际 API 也不慢，但加一点延迟让用户感觉"在思考"体验更好？不，直接调)
            const response = await smartSearch(query, {
                maxResults: 100,
                modelProvider: modelProvider
            });

            if (response.success) {
                setResults(response.results);
                setAiAnalysis(response.ai_analysis || '');
                setIntent(response.intent || '');
                setStrategies(response.strategies_used || []);
            } else {
                setError(response.error || '搜索失败');
            }
        } catch (err: any) {
            setError(err.message || '搜索出错');
        } finally {
            setIsLoading(false);
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
            // 如果是 openfolder，后端目前的 api 是 /open (select)
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
        if (success) {
            // 可以加一个 toast 提示，这里先忽略
        } else {
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

    return (
        <div className="smart-search-page">
            <div className="search-header">
                <h1>AI 文件深度搜索</h1>
                <p className="subtitle">多策略并行检索 · 智能语义理解 · 自动聚合结果</p>
            </div>

            <form onSubmit={handleSearch} className="search-box">
                <input
                    type="text"
                    className="search-input"
                    placeholder="描述你要找的文件，例如：'找一下最近关于大模型落地的PPT'..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    disabled={isLoading}
                    autoFocus
                />
                <button type="submit" className="search-button" disabled={isLoading || !query.trim()}>
                    {isLoading ? '搜索中...' : '开始搜索'}
                </button>
            </form>

            <div className="ai-analysis-container" style={{ display: (aiAnalysis || isLoading) ? 'block' : 'none' }}>
                {isLoading ? (
                    <div className="analysis-text">
                        <div className="spinner" style={{ width: '20px', height: '20px', borderWidth: '2px', margin: 0 }}></div>
                        <span>AI 正在分析您的意图并尝试不同搜索策略...</span>
                    </div>
                ) : (
                    <>
                        <div className="analysis-text">
                            <span>💡 {aiAnalysis}</span>
                        </div>
                        {strategies.length > 0 && (
                            <div className="strategies-tag">
                                已尝试策略：{strategies.join('、')}
                            </div>
                        )}
                    </>
                )}
            </div>

            {error && <div className="error-box">⚠️ {error}</div>}

            <div className="results-grid">
                {results.map((file, index) => (
                    <div key={index} className="result-card">
                        {file.score && file.score > 85 && <div className="score-badge">✨ 强相关</div>}

                        <div className="card-header">
                            <div className="file-icon">
                                {file.name.endsWith('.ppt') || file.name.endsWith('.pptx') ? '📊' :
                                    file.name.endsWith('.doc') || file.name.endsWith('.docx') ? '📝' :
                                        file.name.endsWith('.pdf') ? '📕' :
                                            file.name.endsWith('.xls') || file.name.endsWith('.xlsx') ? '📗' : '📄'}
                            </div>
                            <div className="file-info">
                                <div className="file-name" title={file.name}>{file.name}</div>
                                <div className="file-meta">
                                    <span>{formatSize(file.size)}</span>
                                    <span>•</span>
                                    <span>{file.date_modified?.split(' ')[0]}</span>
                                </div>
                            </div>
                        </div>

                        {file.reason && <div className="ai-reason">🎯 {file.reason}</div>}

                        <div className="card-actions">
                            <button className="action-btn primary" onClick={() => handleOpen(file, 'open')}>
                                📂 打开位置
                            </button>
                            <button className="action-btn" onClick={() => handleCopy(file)}>
                                📋 复制路径
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            {!isLoading && results.length === 0 && query && !error && (
                <div className="loading-box">
                    <p>未找到相关文件，请尝试更换关键词。</p>
                </div>
            )}
        </div>
    );
};
