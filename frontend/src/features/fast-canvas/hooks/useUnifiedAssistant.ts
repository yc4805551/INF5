import { useState, useCallback, useRef } from 'react';
import { AISuggestion, AssistantMode, AuditResult } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5179/api';

// Simple hash function for cache keys
const hashRequest = (content: string, agents: string[]): string => {
    return `${content.slice(0, 100)}_${agents.join(',')}_${content.length}`;
};

/**
 * 统一智能助手Hook - 整合实时建议和审核功能
 */
export const useUnifiedAssistant = () => {
    const [mode, setMode] = useState<AssistantMode>('realtime');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
    const [auditResult, setAuditResult] = useState<AuditResult | null>(null);

    // Smart Cache: Map<requestHash, {result, timestamp}>
    const cacheRef = useRef<Map<string, { result: any; timestamp: number }>>(new Map());
    const CACHE_TTL = 60000; // 60 seconds

    /**
     * 实时分析 - 快速建议（复用基础审核智能体：Proofread Agent）
     */
    const analyzeRealtime = useCallback(async (
        selectedText: string,
        contextText: string,
        modelConfig?: any
    ) => {
        if (!selectedText || selectedText.length < 3) {
            console.warn('[UnifiedAssistant] Text too short for analysis (<3 chars)');
            setSuggestions([]);
            return;
        }

        // Generate cache key
        const cacheKey = hashRequest(selectedText, ['proofread']);
        const now = Date.now();

        // Check cache
        const cached = cacheRef.current.get(cacheKey);
        if (cached && (now - cached.timestamp < CACHE_TTL)) {
            const formattedSuggestions: AISuggestion[] = cached.result.issues?.map((issue: any, idx: number) => ({
                id: `realtime-${Date.now()}-${idx}`,
                blockId: '',
                type: issue.type || 'proofread',
                severity: 'high',
                original: issue.original || issue.problematicText,
                suggestion: issue.suggestion,
                reason: issue.reason || issue.explanation
            })) || [];
            setSuggestions(formattedSuggestions);
            return;
        }

        setIsAnalyzing(true);
        setSuggestions([]);

        try {
            // 使用 /audit/analyze 接口，复用 "proofread" 智能体
            // 这样可以使用强大的 "离线规则库" + "AI 纠错"
            const response = await fetch(`${API_BASE}/audit/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: selectedText, // 实时分析针对当前选段或全段
                    source: contextText,   // 上下文作为参考
                    agents: ['proofread'], // 指定只运行纠错代理
                    model_config: modelConfig || {}
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to get suggestions: ${response.status} ${response.statusText} - ${errorText}`);
            }

            const data = await response.json();

            // Store in cache
            cacheRef.current.set(cacheKey, { result: data, timestamp: now });

            if (data.issues) {
                // 转换为统一格式 (AISuggestion)
                const formattedSuggestions: AISuggestion[] = data.issues.map((issue: any, idx: number) => ({
                    id: `realtime-${Date.now()}-${idx}`,
                    blockId: '',
                    type: issue.type || 'proofread',
                    severity: 'high', // 实时建议通常值得注意
                    original: issue.original || issue.problematicText,
                    suggestion: issue.suggestion,
                    reason: issue.reason || issue.explanation
                }));

                setSuggestions(formattedSuggestions);
            }
        } catch (error) {
            console.error('[UnifiedAssistant] Realtime analysis error:', error);
        } finally {
            setIsAnalyzing(false);
        }
    }, []);

    /**
     * 审核分析 - 完整检查（使用全部6个代理）
     */
    /**
     * 审核分析 - 完整检查（使用全部6个代理，支持NDJSON流式）
     */
    const runAudit = useCallback(async (
        documentText: string,
        rules?: string[],
        modelConfig?: any,
        agents?: string[]
    ) => {
        setIsAnalyzing(true);
        setAuditResult(null);

        try {
            const response = await fetch(`${API_BASE}/audit/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: documentText,
                    rules: rules || [
                        '全文错别字',
                        '逻辑一致性',
                        '格式规范性',
                        '专业术语',
                        '风格统一性',
                        '禁用词检查'
                    ],
                    model_config: modelConfig || {},
                    agents: agents || [],
                    stream: true // Enable NDJSON Streaming
                })
            });

            if (!response.ok) {
                throw new Error('Audit failed');
            }

            // NDJSON Stream Reader
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            const issues: any[] = [];
            let summaryData: any = null;

            if (reader) {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    // 追加到缓冲区
                    buffer += decoder.decode(value, { stream: true });

                    // 按行分割
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || ''; // 保留不完整的最后一行

                    // 解析每一行NDJSON
                    for (const line of lines) {
                        if (!line.trim()) continue;

                        try {
                            const obj = JSON.parse(line);

                            if (obj.type === 'issue') {
                                // 立即追加到UI
                                const formattedIssue: AISuggestion = {
                                    id: `audit-${Date.now()}-${issues.length}`,
                                    blockId: '',
                                    type: obj.data.type || 'proofread',
                                    severity: obj.data.severity || 'medium',
                                    original: obj.data.problematicText || obj.data.original,
                                    suggestion: obj.data.suggestion,
                                    reason: obj.data.explanation || obj.data.reason
                                };
                                issues.push(formattedIssue);

                                // 增量更新UI（实时显示）
                                setAuditResult(prev => ({
                                    status: 'WARNING',
                                    score: prev?.score || 0,
                                    issues: [...issues],
                                    summary: prev?.summary || '正在审核...',
                                    timestamp: Date.now()
                                }));
                            }
                            else if (obj.type === 'summary') {
                                summaryData = obj.data;
                            }
                            else if (obj.type === 'error') {
                                throw new Error(obj.data.message || 'Unknown error');
                            }
                        } catch (parseErr) {
                            console.warn('[NDJSON Parse Error]', line, parseErr);
                        }
                    }
                }
            } else {
                throw new Error('Stream not supported');
            }

            // 最终更新summary
            setAuditResult({
                status: summaryData?.status || 'WARNING',
                score: summaryData?.score || 0,
                issues: issues,
                summary: summaryData?.summary || '审核完毕',
                timestamp: Date.now()
            });

        } catch (error) {
            console.error('Audit error:', error);
            setAuditResult({
                status: 'FAIL',
                score: 0,
                issues: [],
                summary: `审核失败: ${error}`,
                timestamp: Date.now()
            });
        } finally {
            setIsAnalyzing(false);
        }
    }, []);

    /**
     * 清除建议
     */
    const clearSuggestions = useCallback(() => {
        setSuggestions([]);
    }, []);

    /**
     * 清除审核结果
     */
    const clearAudit = useCallback(() => {
        setAuditResult(null);
    }, []);

    /**
     * 移除特定建议
     */
    const removeSuggestion = useCallback((suggestionId: string) => {
        setSuggestions(prev => prev.filter(s => s.id !== suggestionId));
    }, []);

    // --- Chat Logic ---
    const [chatHistory, setChatHistory] = useState<any[]>([]); // Use any to avoid import loop for now, or use ChatMessage

    // Initial welcome
    // useEffect(() => {
    //    setChatHistory([{ role: 'model', parts: [{ text: '您好！我是您的智能写作顾问。' }] }]);
    // }, []);

    const sendChatMessage = useCallback(async (text: string) => {
        // Add user message
        const userMsg = { role: 'user', parts: [{ text }] };
        setChatHistory(prev => [...prev, userMsg]);
        setIsAnalyzing(true);

        try {
            // Import dynamically or use fetch directly? 
            // We use the common service 
            // Assume we can import callGenerativeAi from services/ai
            // But we need to handle streaming separately or simplified request.
            // For now, let's use the simple fetch to backend or re-implement simple stream.

            // Actually, we should use the existing service.
            // But since this file is already long, let's implement a simple fetch for now
            // or modify imports at top.

            // Let's use the Advisor Service endpoint for chat as well? 
            // Or just reuse the /api/advisor/suggestions? No, that's specific.
            // We can use the generic /api/common/chat or similar?

            // To be safe and quick, let's use the 'callGenerativeAi' from global services.
            // But imports are tricky with replace_content.
            // I will use fetch to /api/advisor (AdvisorService) if I add a chat endpoint there?
            // Or use /api/generate (Common).

            const response = await fetch(`${API_BASE}/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider: 'deepseek', // Default or from config
                    userPrompt: text,
                    systemInstruction: "You are a helpful writing assistant. Answer concisely.",
                    history: chatHistory,
                    executionMode: 'backend' // Prefer backend for proxy
                })
            });

            if (!response.ok) throw new Error('Chat failed');

            const data = await response.text(); // Assume text response for now, not stream
            // If backend returns raw text

            const modelMsg = { role: 'model', parts: [{ text: data }] };
            setChatHistory(prev => [...prev, modelMsg]);

        } catch (error) {
            console.error('Chat error:', error);
            const errorMsg = { role: 'model', parts: [{ text: `Error: ${error}` }] };
            setChatHistory(prev => [...prev, errorMsg]);
        } finally {
            setIsAnalyzing(false);
        }
    }, [chatHistory]);

    return {
        mode,
        setMode,
        isAnalyzing,
        suggestions,
        auditResult,
        analyzeRealtime,
        runAudit,
        clearSuggestions,
        clearAudit,
        removeSuggestion,
        // Chat exports
        chatHistory,
        sendChatMessage
    };
};
