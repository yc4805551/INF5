import { FileSearchResult } from './fileSearchApi';

// 基础 API URL
// 自动适配
const API_BASE_URL = '/api';

/**
 * 智能搜索结果
 */
export interface SmartSearchResult {
    name: string;
    path: string;
    size?: number;
    date_modified?: string;
    score?: number;
    reason?: string;
    is_dir?: boolean;
    _strategy_desc?: string; // 内部用于调试
}

export interface SmartSearchResponse {
    success: boolean;
    query: string;
    intent?: string;
    strategies_used?: string[];
    results: SmartSearchResult[];
    ai_analysis?: string;
    error?: string;
}

/**
 * 智能搜索 API (Deprecated: use stream instead)
 */
export const smartSearch = async (
    query: string,
    options: { maxResults?: number; modelProvider?: string; modelConfig?: any } = {}
): Promise<SmartSearchResponse> => {
    try {
        const response = await fetch(`${API_BASE_URL}/file-search/smart`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query,
                maxResults: options.maxResults || 20,
                modelProvider: options.modelProvider || 'gemini',
                modelConfig: options.modelConfig
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Smart search error:', error);
        return {
            success: false,
            query,
            results: [],
            error: error instanceof Error ? error.message : String(error)
        };
    }
};

/**
 * Streaming Smart Search
 * Callbacks for progressive updates
 */
export const smartSearchStream = async (
    query: string,
    callbacks: {
        onIntent?: (data: any) => void;
        onLog?: (message: string) => void;
        onStatus?: (message: string, step: string) => void;
        onResultChunk?: (results: SmartSearchResult[], strategy: string) => void;
        onFinalResults?: (results: SmartSearchResult[]) => void;
        onAnalysis?: (text: string) => void;
        onError?: (error: string) => void;
    },
    options: { maxResults?: number; modelProvider?: string; modelConfig?: any } = {}
) => {
    try {
        const response = await fetch(`${API_BASE_URL}/file-search/smart`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query,
                maxResults: options.maxResults || 20,
                maxCandidates: 3000,
                modelProvider: options.modelProvider || 'gemini',
                modelConfig: options.modelConfig
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        if (!response.body) {
            throw new Error('Response body is null');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // 处理粘包 (lines)
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // 保留最后一行（如果不完整）

            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const event = JSON.parse(line);

                    switch (event.type) {
                        case 'status':
                            callbacks.onStatus?.(event.message, event.step);
                            break;
                        case 'log':
                            callbacks.onLog?.(event.message);
                            break;
                        case 'intent':
                            callbacks.onIntent?.(event.data);
                            break;
                        case 'result_chunk':
                            callbacks.onResultChunk?.(event.data, event.strategy);
                            break;
                        case 'final_results':
                            callbacks.onFinalResults?.(event.data);
                            break;
                        case 'analysis':
                            callbacks.onAnalysis?.(event.data);
                            break;
                        case 'error':
                            callbacks.onError?.(event.message);
                            break;
                    }
                } catch (e) {
                    console.warn("Failed to parse stream line:", line, e);
                }
            }
        }

    } catch (error) {
        console.error('Stream search error:', error);
        callbacks.onError?.(error instanceof Error ? error.message : String(error));
    }
};

export const openFileLocation = async (path: string): Promise<boolean> => {
    try {
        const response = await fetch(`${API_BASE_URL}/file-search/open`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ path }),
        });
        const data = await response.json();
        return data.success;
    } catch (error) {
        console.error('Open file error:', error);
        return false;
    }
};

export const copyTextToClipboard = async (text: string): Promise<boolean> => {
    try {
        const response = await fetch(`${API_BASE_URL}/file-search/copy`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text }),
        });
        const data = await response.json();
        return data.success;
    } catch (error) {
        console.error('Copy error:', error);
        return false;
    }
};
