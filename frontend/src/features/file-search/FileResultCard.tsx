import React from 'react';
import { FileSearchResult } from './fileSearchApi';

interface FileResultCardProps {
    file: FileSearchResult;
    index: number;
}

/**
 * 文件结果卡片组件
 */
export const FileResultCard: React.FC<FileResultCardProps> = ({ file, index }) => {
    // 格式化文件大小
    const formatFileSize = (bytes?: number): string => {
        if (!bytes) return 'N/A';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    };

    // 获取文件图标
    const getFileIcon = (fileName: string): string => {
        const ext = fileName.toLowerCase().split('.').pop();
        switch (ext) {
            case 'docx':
            case 'doc':
                return '📄';
            case 'xlsx':
            case 'xls':
            case 'csv':
                return '📊';
            case 'pdf':
                return '📕';
            case 'txt':
            case 'md':
                return '📝';
            case 'pptx':
            case 'ppt':
                return '📽️';
            case 'zip':
            case 'rar':
                return '📦';
            case 'jpg':
            case 'jpeg':
            case 'png':
            case 'gif':
                return '🖼️';
            default:
                return '📁';
        }
    };

    // 打开文件所在文件夹
    const handleOpenFolder = () => {
        // 在前端无法直接打开文件夹，可以复制路径
        navigator.clipboard.writeText(file.path);
        alert(`路径已复制到剪贴板：\n${file.path}`);
    };

    // 复制文件路径
    const handleCopyPath = () => {
        navigator.clipboard.writeText(file.path);
    };

    return (
        <div className={`file-result-card ${file.is_recommended ? 'recommended' : ''}`}>
            <div className="file-result-header">
                <span className="file-icon">{getFileIcon(file.name)}</span>
                <div className="file-info">
                    <div className="file-name-row">
                        <span className="file-index">#{index}</span>
                        <span className="file-name">{file.name}</span>
                        {file.is_recommended && (
                            <span className="recommended-badge">⭐ 推荐</span>
                        )}
                    </div>
                    {file.ai_score !== undefined && (
                        <div className="ai-score">
                            相关度: <span className="score-value">{file.ai_score}</span>
                        </div>
                    )}
                </div>
            </div>

            <div className="file-result-body">
                <div className="file-path-row">
                    <span className="label">路径:</span>
                    <span className="file-path" title={file.path}>{file.path}</span>
                </div>

                <div className="file-metadata">
                    <span className="metadata-item">
                        大小: {formatFileSize(file.size)}
                    </span>
                    {file.date_modified && (
                        <span className="metadata-item">
                            修改: {file.date_modified}
                        </span>
                    )}
                </div>

                {file.ai_reason && (
                    <div className="ai-reason">
                        <span className="label">推荐理由:</span>
                        <span className="reason-text">{file.ai_reason}</span>
                    </div>
                )}
            </div>

            <div className="file-result-actions">
                <button
                    className="btn btn-sm btn-outline"
                    onClick={handleCopyPath}
                    title="复制路径"
                >
                    📋 复制路径
                </button>
                <button
                    className="btn btn-sm btn-outline"
                    onClick={handleOpenFolder}
                    title="显示路径（复制到剪贴板）"
                >
                    📂 复制路径
                </button>
            </div>
        </div>
    );
};
