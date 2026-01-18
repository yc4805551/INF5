/**
 * 文件搜索 API 客户端
 */

const API_BASE_URL = 'http://localhost:5179/api';

export interface FileSearchResult {
    name: string;
    path: string;
    size?: number;
    date_modified?: string;
    ai_score?: number;
    ai_reason?: string;
    is_recommended?: boolean;
}

export interface SearchResponse {
    success: boolean;
    query: string;
    total: number;
    results: FileSearchResult[];
    error?: string;
}

/**
 * 智能文件搜索
 */
export async function searchFiles(
    query: string,
    options?: {
        fileTypes?: string[];
        dateRange?: string;
        maxResults?: number;
        enableAiRanking?: boolean;
    }
): Promise<SearchResponse> {
    const response = await fetch(`${API_BASE_URL}/file-search/search`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            query,
            fileTypes: options?.fileTypes,
            dateRange: options?.dateRange,
            maxResults: options?.maxResults || 10,
            enableAiRanking: options?.enableAiRanking !== false
        })
    });

    if (!response.ok) {
        throw new Error(`搜索失败: ${response.statusText}`);
    }

    return response.json();
}

/**
 * 快速搜索（不启用 AI 排序）
 */
export async function quickSearch(query: string, limit = 10): Promise<SearchResponse> {
    const response = await fetch(
        `${API_BASE_URL}/file-search/quick-search?q=${encodeURIComponent(query)}&limit=${limit}`
    );

    if (!response.ok) {
        throw new Error(`快速搜索失败: ${response.statusText}`);
    }

    return response.json();
}

/**
 * 搜索文档
 */
export async function searchDocuments(query: string, maxResults = 10): Promise<SearchResponse> {
    const response = await fetch(`${API_BASE_URL}/file-search/search/documents`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query, maxResults })
    });

    if (!response.ok) {
        throw new Error(`文档搜索失败: ${response.statusText}`);
    }

    return response.json();
}

/**
 * 搜索表格
 */
export async function searchSpreadsheets(query: string, maxResults = 10): Promise<SearchResponse> {
    const response = await fetch(`${API_BASE_URL}/file-search/search/spreadsheets`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query, maxResults })
    });

    if (!response.ok) {
        throw new Error(`表格搜索失败: ${response.statusText}`);
    }

    return response.json();
}

/**
 * 检查 Everything 服务状态
 */
export async function checkHealthStatus(): Promise<{
    status: string;
    everything_connected: boolean;
    message: string;
}> {
    const response = await fetch(`${API_BASE_URL}/file-search/health`);
    return response.json();
}
