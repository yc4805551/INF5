// 使用相对路径导入配置
const API_BASE_URL = 'http://localhost:5179';  // 默认后端地址

export interface SmartSearchResult {
    name: string;
    path: string;
    score?: number;
    reason?: string;
    size?: number;
    date_modified?: string;
}

export interface SmartSearchResponse {
    success: boolean;
    query: string;
    intent?: string;
    total_candidates?: number;
    results: SmartSearchResult[];
    ai_analysis?: string;
    error?: string;
}

/**
 * AI 智能搜索 - 支持自然语言
 */
export async function smartSearch(
    query: string,
    options?: {
        maxResults?: number;
        modelProvider?: string;
    }
): Promise<SmartSearchResponse> {
    const response = await fetch(`${API_BASE_URL}/api/file-search/smart`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            query,
            maxResults: options?.maxResults || 10,
            modelProvider: options?.modelProvider || 'gemini',
        }),
    });

    if (!response.ok) {
        throw new Error(`Smart search failed: ${response.statusText}`);
    }

    return response.json();
}

/**
 * 复制文本到剪贴板 (服务器端)
 */
export async function copyTextToClipboard(text: string): Promise<boolean> {
    try {
        const response = await fetch(`${API_BASE_URL}/api/file-search/copy`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text }),
        });
        return response.ok;
    } catch (e) {
        console.error('Failed to copy text:', e);
        return false;
    }
}

/**
 * 打开文件所在位置
 */
export async function openFileLocation(path: string): Promise<boolean> {
    try {
        const response = await fetch(`${API_BASE_URL}/api/file-search/open`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ path }),
        });
        return response.ok;
    } catch (e) {
        console.error('Failed to open file location:', e);
        return false;
    }
}
