import React, { useState, useEffect } from 'react';
import { searchFiles, FileSearchResult, quickSearch } from './fileSearchApi';
import { FileResultCard } from './FileResultCard';
import './SearchPage.css';

/**
 * 文件搜索页面组件
 */
export const SearchPage: React.FC = () => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<FileSearchResult[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [total, setTotal] = useState(0);

    // 搜索选项
    const [selectedFileTypes, setSelectedFileTypes] = useState<string[]>([]);
    const [dateRange, setDateRange] = useState<string>('');
    const [maxResults, setMaxResults] = useState(10);
    const [enableAiRanking] = useState(true);

    // 预定义的文件类型
    const FILE_TYPE_OPTIONS = [
        { label: '文档 (.docx, .pdf, .md)', value: ['.docx', '.pdf', '.md', '.txt'] },
        { label: '表格 (.xlsx, .xls)', value: ['.xlsx', '.xls', '.csv'] },
        { label: 'PPT (.pptx, .ppt)', value: ['.pptx', '.ppt'] },
        { label: '全部', value: [] }
    ];

    // 时间范围选项
    const DATE_RANGE_OPTIONS = [
        { label: '不限', value: '' },
        { label: '今天', value: 'today' },
        { label: '昨天', value: 'yesterday' },
        { label: '上周', value: 'lastweek' },
        { label: '上月', value: 'lastmonth' }
    ];

    // 执行搜索
    const handleSearch = async (e?: React.FormEvent) => {
        e?.preventDefault();

        if (!query.trim()) {
            setError('请输入搜索关键词');
            return;
        }

        setIsLoading(true);
        setError(null);
        setResults([]);

        try {
            const response = await searchFiles(query, {
                fileTypes: selectedFileTypes.length > 0 ? selectedFileTypes : undefined,
                dateRange: dateRange || undefined,
                maxResults,
                enableAiRanking
            });

            if (response.success) {
                setResults(response.results);
                setTotal(response.total);
            } else {
                setError(response.error || '搜索失败');
            }
        } catch (err: any) {
            setError(err.message || '搜索出错');
        } finally {
            setIsLoading(false);
        }
    };

    // 文件类型选择
    const handleFileTypeChange = (types: string[]) => {
        setSelectedFileTypes(types);
    };

    return (
        <div className="search-page-container">
            <div className="search-page-header">
                <h1>📁 智能文件搜索</h1>
                <p className="search-page-subtitle">
                    Everything + AI 智能排序，快速找到您需要的文件
                </p>
            </div>

            <div className="search-page-content">
                {/* 搜索控制区 */}
                <div className="search-control-panel">
                    <form onSubmit={handleSearch} className="search-form">
                        <div className="search-input-group">
                            <input
                                type="text"
                                className="search-input"
                                placeholder="输入文件名或关键词..."
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                disabled={isLoading}
                            />
                            <button
                                type="submit"
                                className="btn btn-primary search-btn"
                                disabled={isLoading || !query.trim()}
                            >
                                {isLoading ? (
                                    <>
                                        <span className="spinner small"></span>
                                        搜索中...
                                    </>
                                ) : (
                                    '🔍 搜索'
                                )}
                            </button>
                        </div>

                        {/* 过滤选项 */}
                        <div className="search-filters">
                            <div className="filter-group">
                                <label>文件类型:</label>
                                <div className="filter-buttons">
                                    {FILE_TYPE_OPTIONS.map((option, index) => (
                                        <button
                                            key={index}
                                            type="button"
                                            className={`filter-btn ${JSON.stringify(selectedFileTypes) === JSON.stringify(option.value)
                                                ? 'active'
                                                : ''
                                                }`}
                                            onClick={() => handleFileTypeChange(option.value)}
                                            disabled={isLoading}
                                        >
                                            {option.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="filter-group">
                                <label>时间范围:</label>
                                <select
                                    className="filter-select"
                                    value={dateRange}
                                    onChange={(e) => setDateRange(e.target.value)}
                                    disabled={isLoading}
                                >
                                    {DATE_RANGE_OPTIONS.map((option, index) => (
                                        <option key={index} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div className="filter-group">
                                <label>结果数量:</label>
                                <select
                                    className="filter-select"
                                    value={maxResults}
                                    onChange={(e) => setMaxResults(Number(e.target.value))}
                                    disabled={isLoading}
                                >
                                    <option value={5}>5 个</option>
                                    <option value={10}>10 个</option>
                                    <option value={20}>20 个</option>
                                    <option value={50}>50 个</option>
                                    <option value={100}>100 个</option>
                                </select>
                            </div>
                        </div>
                    </form>
                </div>

                {/* 搜索结果区 */}
                <div className="search-results-panel">
                    {error && (
                        <div className="error-message">
                            ⚠️ {error}
                        </div>
                    )}

                    {!error && !isLoading && total > 0 && (
                        <div className="results-header">
                            <span className="results-count">
                                找到 <strong>{total}</strong> 个相关文件
                            </span>
                            {enableAiRanking && (
                                <span className="ai-ranking-badge">
                                    ⭐ AI 智能排序
                                </span>
                            )}
                        </div>
                    )}

                    {isLoading && (
                        <div className="spinner-container">
                            <div className="spinner large"></div>
                            <p>正在搜索中...</p>
                        </div>
                    )}

                    {!error && !isLoading && results.length === 0 && query && (
                        <div className="empty-state">
                            <p className="empty-icon">📂</p>
                            <p className="empty-text">未找到匹配的文件</p>
                            <p className="empty-hint">
                                试试调整搜索关键词或过滤条件
                            </p>
                        </div>
                    )}

                    {!error && !isLoading && results.length === 0 && !query && (
                        <div className="empty-state">
                            <p className="empty-icon">🔍</p>
                            <p className="empty-text">开始搜索文件</p>
                            <p className="empty-hint">
                                输入文件名或关键词，支持中文和英文
                            </p>
                        </div>
                    )}

                    <div className="results-list">
                        {results.map((file, index) => (
                            <FileResultCard
                                key={`${file.path}-${index}`}
                                file={file}
                                index={index + 1}
                            />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
