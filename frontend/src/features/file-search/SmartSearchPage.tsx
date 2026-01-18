import React, { useState } from 'react';
import { smartSearch, openFileLocation, SmartSearchResult } from './smartSearchApi';
import './SmartSearchPage.css';

/**
 * AI 智能文件搜索页面 - 简洁版
 */
export const SmartSearchPage: React.FC = () => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SmartSearchResult[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [aiAnalysis, setAiAnalysis] = useState<string>('');
    const [intent, setIntent] = useState<string>('');

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

        try {
            const response = await smartSearch(query, {
                maxResults: 20,
            });

            if (response.success) {
                setResults(response.results);
                setAiAnalysis(response.ai_analysis || '');
                setIntent(response.intent || '');
            } else {
                setError(response.error || '搜索失败');
            }
        } catch (err: any) {
            setError(err.message || '搜索出错');
        } finally {
            setIsLoading(false);
        }
    };

    // 获取文件的完整路径 (兼容 Everything 返回 path 为目录的情况)
    const getFullPath = (file: SmartSearchResult) => {
        if (!file.path) return '';
        // 如果 path 已经包含 name (某些 API 变体)，则直接返回
        if (file.path.endsWith(file.name)) return file.path;

        // 否则拼接 (简单处理 Windows 路径分隔符)
        const separator = file.path.includes('/') ? '/' : '\\';
        return file.path.endsWith(separator)
            ? file.path + file.name
            : file.path + separator + file.name;
    };

    // 复制路径 (增强版: 支持 fallback)
    const handleCopyPath = async (path: string) => {
        if (!path) return;

        try {
            await navigator.clipboard.writeText(path);
        } catch (err) {
            console.error('Clipboard API failed, trying fallback', err);
            // Fallback for non-secure contexts or older browsers
            try {
                const textArea = document.createElement("textarea");
                textArea.value = path;

                // Ensure it's not visible but part of DOM
                textArea.style.position = "fixed";
                textArea.style.left = "-9999px";
                textArea.style.top = "0";
                document.body.appendChild(textArea);

                textArea.focus();
                textArea.select();

                document.execCommand('copy');
                document.body.removeChild(textArea);
            } catch (fallbackErr) {
                console.error('Copy failed completely', fallbackErr);
                alert('❌ 无法自动复制，请手动复制');
            }
        }
    };

    // 打开所在位置
    const handleOpenFolder = async (path: string) => {
        if (!path) return;
        try {
            const success = await openFileLocation(path);
            if (!success) {
                alert('无法打开文件夹，可能文件不存在');
            }
        } catch (e) {
            console.error(e);
            alert('打开文件夹失败');
        }
    };

    // 格式化文件大小
    const formatFileSize = (bytes?: number): string => {
        if (!bytes) return '-';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    return (
        <div className="smart-search-page">
            {/* 标题 */}
            <div className="search-header">
                <h1>🤖 AI 文件搜索助手</h1>
                <p className="subtitle">用自然语言描述您要找的文件</p>
            </div>

            {/* 搜索框 */}
            <form onSubmit={handleSearch} className="search-box">
                <input
                    type="text"
                    className="search-input"
                    placeholder="例如：帮我找最近修改的关于吴军的课程PPT"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    disabled={isLoading}
                />
                <button
                    type="submit"
                    className="search-button"
                    disabled={isLoading || !query.trim()}
                >
                    {isLoading ? '搜索中...' : '🔍 搜索'}
                </button>
            </form>

            {/* AI 分析提示 */}
            {aiAnalysis && (
                <div className="ai-analysis">
                    💡 {aiAnalysis}
                    {intent && <span className="intent-tag">意图：{intent}</span>}
                </div>
            )}

            {/* 错误提示 */}
            {error && (
                <div className="error-box">
                    ⚠️ {error}
                </div>
            )}

            {/* 加载状态 */}
            {isLoading && (
                <div className="loading-box">
                    <div className="spinner"></div>
                    <p>AI 正在分析并筛选文件...</p>
                </div>
            )}

            {/* 结果列表 - 简化版 */}
            {!isLoading && results.length > 0 && (
                <div className="simple-results-list">
                    {results.map((file, index) => (
                        <div key={index} className="simple-result-card">
                            <div className="result-main">
                                <div className="result-header">
                                    <span className="file-icon">📄</span>
                                    <span className="file-name" title={file.name}>{file.name}</span>
                                    {file.score !== undefined && file.score >= 80 && (
                                        <span className="high-score-badge">推荐</span>
                                    )}
                                </div>
                                <div className="result-path" title={file.path}>
                                    📍 {file.path}
                                </div>
                                {file.reason && (
                                    <div className="result-reason">
                                        💡 {file.reason}
                                    </div>
                                )}
                            </div>

                            <div className="result-actions">
                                <button
                                    className="simple-action-btn"
                                    onClick={() => {
                                        const fullPath = getFullPath(file);
                                        handleOpenFolder(fullPath);
                                    }}
                                    title="打开所在文件夹"
                                >
                                    📂
                                </button>
                                <button
                                    className="simple-action-btn"
                                    onClick={() => {
                                        const fullPath = getFullPath(file);
                                        handleCopyPath(fullPath);
                                    }}
                                    title="复制完整路径"
                                >
                                    📋
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* 空状态 */}
            {!isLoading && !error && results.length === 0 && query && (
                <div className="empty-state">
                    <p className="empty-icon">🔍</p>
                    <p className="empty-text">未找到匹配的文件</p>
                    <p className="empty-hint">试试调整您的描述或使用不同的关键词</p>
                </div>
            )}

            {/* 初始提示 */}
            {!isLoading && !query && results.length === 0 && (
                <div className="tips-box">
                    <h3>💡 搜索提示</h3>
                    <ul>
                        <li>使用自然语言描述您要找的文件，例如：<br />
                            <code>"帮我找最近修改的期末作业"</code></li>
                        <li>可以指定时间范围：<br />
                            <code>"上周讨论的项目文档"</code></li>
                        <li>可以指定文件类型：<br />
                            <code>"关于机器学习的PPT"</code></li>
                        <li>AI 会自动理解您的意图并筛选出最相关的文件</li>
                    </ul>
                </div>
            )}
        </div>
    );
};
