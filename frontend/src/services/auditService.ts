import { API_BASE_URL } from './ai';
import { AISuggestion, AuditResult } from '../features/fast-canvas/types';

/**
 * 实时改错 API 调用
 */
export const performRealtimeCheck = async (
    content: string,
    source: string,
    modelConfig: any
): Promise<{ issues: any[] }> => {
    const response = await fetch(`${API_BASE_URL}/audit/realtime`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            content,
            source,
            model_config: modelConfig
        })
    });

    if (!response.ok) {
        throw new Error(`Realtime check failed: ${response.statusText}`);
    }

    return await response.json();
};

/**
 * 全量审核 API 调用 (Stream & Non-Stream supported via parameter, mostly stream used in frontend)
 */
export const performFullAudit = async (
    content: string,
    source: string,
    rules: string[],
    modelConfig: any,
    agents: string[],
    onChunk?: (issue: AISuggestion) => void,
    onSummary?: (summary: any) => void,
    onError?: (error: string) => void
): Promise<void> => {

    try {
        const response = await fetch(`${API_BASE_URL}/audit/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content,
                source,
                agents,
                rules,
                stream: true,
                model_config: modelConfig
            })
        });

        if (!response.ok) {
            throw new Error(`Audit failed: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error('Stream not supported');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const obj = JSON.parse(line);
                    if (obj.type === 'issue') {
                        // Standardize Issue format if needed
                        const issue = {
                            id: `audit-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
                            blockId: '',
                            type: obj.data.type || 'proofread',
                            severity: obj.data.severity || 'medium',
                            original: obj.data.problematicText || obj.data.original,
                            suggestion: obj.data.suggestion,
                            reason: obj.data.explanation || obj.data.reason
                        } as AISuggestion;
                        onChunk?.(issue);
                    } else if (obj.type === 'summary') {
                        onSummary?.(obj.data);
                    } else if (obj.type === 'error') {
                        onError?.(obj.data.message);
                    }
                } catch (e) {
                    console.warn('Error parsing ndjson line:', line);
                }
            }
        }
    } catch (e: any) {
        onError?.(e.message || 'Network Error');
    }
};
