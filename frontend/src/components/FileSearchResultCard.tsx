import React from 'react';
import './FileSearchResultCard.css';
import { openFileLocation } from '../features/file-search/smartSearchApi';

export interface FileSearchFile {
    // ...
    name: string;
    path: string;
    score?: number;
    reason?: string;
    size?: number;
    date_modified?: string;
}

export interface FileSearchResultData {
    files: FileSearchFile[];
    ai_analysis: string;
    total_candidates?: number;
    intent?: string;
}

interface FileSearchResultCardProps {
    data: FileSearchResultData;
}

/**
 * 文件搜索结果卡片组件
 * 在聊天中展示文件搜索结果
 */
export const FileSearchResultCard: React.FC<FileSearchResultCardProps> = ({ data }) => {
    const { files, ai_analysis } = data;

    // 获取文件的完整路径
    const getFullPath = (file: FileSearchFile) => {
        if (!file.path) return '';
        if (file.path.endsWith(file.name)) return file.path;
        const separator = file.path.includes('/') ? '/' : '\\';
        return file.path.endsWith(separator)
            ? file.path + file.name
            : file.path + separator + file.name;
    };

    // 复制路径 (增强版)
    const handleCopyPath = async (path: string) => {
        if (!path) return;
        try {
            await navigator.clipboard.writeText(path);
            alert('路径已复制！');
        } catch (err) {
            console.error('Clipboard API failed', err);
            // Fallback
            try {
                const textArea = document.createElement("textarea");
                textArea.value = path;
                textArea.style.position = "fixed";
                textArea.style.left = "-9999px";
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                alert('路径已复制！(兼容模式)');
            } catch (e) {
                alert('复制失败，请手动复制');
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
        <div className="file-search-result-card">
            {/* AI 分析提示 */}
            <div className="search-analysis">
                📁 {ai_analysis}
            </div>

            {/* 文件列表 */}
            <div className="file-list">
                {files.map((file, index) => (
                    <div key={index} className="file-item">
                        <div className="file-header">
                            <span className="file-icon">📄</span>
                            <span className="file-name">{file.name}</span>
                        </div>

                        <div className="file-meta">
                            {file.score !== undefined && (
                                <span className={`score score-${Math.floor(file.score / 10) * 10}`}>
                                    ⭐ {file.score}/100
                                </span>
                            )}
                            {file.size && (
                                <span className="file-size">{formatFileSize(file.size)}</span>
                            )}
                            {file.date_modified && (
                                <span className="file-date">{file.date_modified}</span>
                            )}
                        </div>

                        {file.path && (
                            <div className="file-path">
                                📍 <code>{file.path}</code>
                            </div>
                        )}

                        {file.reason && (
                            <div className="file-reason">
                                💡 {file.reason}
                            </div>
                        )}

                        <div className="file-actions">
                            <button
                                className="action-btn"
                                onClick={() => handleOpenFolder(getFullPath(file))}
                                title="打开所在文件夹"
                            >
                                📂 打开位置
                            </button>
                            <button
                                className="action-btn"
                                onClick={() => handleCopyPath(getFullPath(file))}
                                title="复制完整路径"
                            >
                                📋 复制路径
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

/**
 * 从消息文本中解析文件搜索结果
 */
export function parseFileSearchResult(markdown: string): FileSearchResultData | null {
    try {
        // 提取 JSON 元数据
        const match = markdown.match(/<!-- FILE_SEARCH_RESULT -->\s*([\s\S]*?)\s*<!-- \/FILE_SEARCH_RESULT -->/);
        if (match && match[1]) {
            const data = JSON.parse(match[1]);
            return data as FileSearchResultData;
        }
    } catch (e) {
        console.error('Failed to parse file search result:', e);
    }
    return null;
}

/**
 * 检测消息是否包含文件搜索结果
 */
export function hasFileSearchResult(markdown: string): boolean {
    return markdown.includes('<!-- FILE_SEARCH_RESULT -->');
}
