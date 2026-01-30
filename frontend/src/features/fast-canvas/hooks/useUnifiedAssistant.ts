import { useState, useCallback, useRef } from 'react';
import { AISuggestion, AssistantMode, AuditResult } from '../types';
import { performRealtimeCheck, performFullAudit } from '../../../services/auditService';
import { getModelConfig } from '../../../services/configService';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5179/api';

// Simple hash function for cache keys
const hashRequest = (content: string, agents: string[]): string => {
    return `${content.slice(0, 100)}_${agents.join(',')}_${content.length}`;
};

/**
 * 统一智能助手Hook - 整合实时建议和审核功能
 */
export const useUnifiedAssistant = (modelProvider: string = 'free') => {
    const [mode, setMode] = useState<AssistantMode>('realtime');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
    const [auditResult, setAuditResult] = useState<AuditResult | null>(null);

    // 新增：检查状态反馈
    const [lastCheckResult, setLastCheckResult] = useState<{
        message: string;
        timestamp: string;
        issueCount: number;
    } | null>(null);

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
                severity: issue.severity || 'high',
                original: issue.original || issue.problematicText,
                suggestion: issue.suggestion,
                reason: issue.reason || issue.explanation,
                confidence: issue.confidence
            })) || [];
            setSuggestions(formattedSuggestions);
            return;
        }

        setIsAnalyzing(true);
        setSuggestions([]);

        try {
            // Get complete config using unified service
            const completeModelConfig = getModelConfig(modelProvider, modelConfig);

            // 使用 Service 层调用
            const result = await performRealtimeCheck(selectedText, contextText, completeModelConfig);

            // Store in cache
            cacheRef.current.set(cacheKey, { result, timestamp: now });

            // 设置检查结果反馈
            setLastCheckResult({
                message: result.message || '检查完成',
                timestamp: result.checked_at || new Date().toISOString(),
                issueCount: result.issues?.length || 0
            });

            if (result.issues) {
                // 转换为统一格式 (AISuggestion)
                const formattedSuggestions: AISuggestion[] = result.issues.map((issue: any, idx: number) => ({
                    id: `realtime-${Date.now()}-${idx}`,
                    blockId: '',
                    type: issue.type || 'proofread',
                    severity: issue.severity || 'high',
                    original: issue.original || issue.problematicText,
                    suggestion: issue.suggestion,
                    reason: issue.reason || issue.explanation,
                    confidence: issue.confidence
                }));

                setSuggestions(formattedSuggestions);
            } else {
                setSuggestions([]);
            }
        } catch (error) {
            console.error('[UnifiedAssistant] Realtime analysis error:', error);
            setLastCheckResult({
                message: '检查失败',
                timestamp: new Date().toISOString(),
                issueCount: 0
            });
        } finally {
            setIsAnalyzing(false);
        }
    }, [modelProvider]);

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
            // Get complete config using unified service
            const completeModelConfig = getModelConfig(modelProvider, modelConfig);

            const currentIssues: AISuggestion[] = [];

            // 使用 Service 层处理流式响应
            await performFullAudit(
                documentText,
                '', // source currently not passed in this signature/UI but service supports it
                rules || [],
                completeModelConfig,
                agents || [],
                (issue: AISuggestion) => {
                    // On Chunk
                    currentIssues.push(issue);
                    setAuditResult(prev => ({
                        status: 'WARNING',
                        score: prev?.score || 100,
                        issues: [...currentIssues],
                        summary: prev?.summary || '正在审核...',
                        timestamp: Date.now()
                    }));
                },
                (summary: any) => {
                    // On Summary
                    setAuditResult(prev => ({
                        status: summary.status || 'WARNING',
                        score: summary.score || 0,
                        issues: [...currentIssues],
                        summary: summary.summary || '审核完毕',
                        timestamp: Date.now()
                    }));
                },
                (errorMsg: string) => {
                    // On Error
                    throw new Error(errorMsg);
                }
            );

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
    }, [modelProvider]);

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
        setAuditResult(prev => {
            if (!prev) return null;
            return {
                ...prev,
                issues: prev.issues.filter(issue => issue.id !== suggestionId)
            };
        });
    }, []);

    // --- Chat Logic ---
    const [chatHistory, setChatHistory] = useState<any[]>([]); // Use any to avoid import loop for now, or use ChatMessage

    // Initial welcome
    // useEffect(() => {
    //    setChatHistory([{ role: 'model', parts: [{ text: '您好！我是您的智能写作顾问。' }] }]);
    // }, []);

    const sendChatMessage = useCallback(async (text: string, context?: string, triggerAudit: boolean = false) => {
        // Add user message
        const userMsg = { role: 'user', parts: [{ text }] };
        setChatHistory(prev => [...prev, userMsg]);
        setIsAnalyzing(true);

        try {
            // Get complete config using unified service
            const completeModelConfig = getModelConfig(modelProvider);

            const response = await fetch(`${API_BASE}/advisor/copilot`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    context: context || '',
                    trigger_audit: triggerAudit,
                    history: chatHistory,
                    model_config: completeModelConfig
                })
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`Copilot call failed: ${errText}`);
            }

            const data = await response.json();
            // Expect { type: 'text' | 'audit_report' | 'error', content: ..., data: ... }

            let resultText = '';
            if (data.type === 'text') {
                resultText = data.content;
            } else if (data.type === 'audit_report') {
                // Pass structured data via a specially formatted JSON string
                // CopilotChat will detect this signature {"type":"audit_report"} and render the Card
                resultText = JSON.stringify({
                    type: 'audit_report',
                    data: data.data // Contains { score, issues, summary }
                });
            } else if (data.type === 'error') {
                resultText = `Error: ${data.content}`;
            }

            const modelMsg = { role: 'model', parts: [{ text: resultText }] };
            setChatHistory(prev => [...prev, modelMsg]);

        } catch (error) {
            console.error('Chat error:', error);
            const errorMsg = { role: 'model', parts: [{ text: `Connection Error: ${error}` }] };
            setChatHistory(prev => [...prev, errorMsg]);
        } finally {
            setIsAnalyzing(false);
        }
    }, [chatHistory, modelProvider]);

    const smartWrite = useCallback(async (prompt: string) => {
        // 1. Add User Message immediately
        setChatHistory(prev => [...prev, { role: 'user', parts: [{ text: `[写作指令] ${prompt}` }] }]);

        setIsAnalyzing(true);
        try {
            const response = await fetch(`${API_BASE}/agent-anything/smart-write`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            // 2. Add Model Response
            const content = data.content || "生成失败 (无内容)";
            // Optionally append sources?
            let finalText = content;
            if (data.sources && data.sources.length > 0) {
                finalText += `\n\n--- 参考来源 ---\n` + data.sources.map((s: any) => `- ${s.title || s.name || 'Unknown'}`).join('\n');
            }

            setChatHistory(prev => [...prev, { role: 'model', parts: [{ text: finalText }] }]);

            setIsAnalyzing(false);
            return data;
        } catch (error) {
            console.error('Smart Write Error:', error);
            setChatHistory(prev => [...prev, { role: 'model', parts: [{ text: `Error: ${error}` }] }]);
            setIsAnalyzing(false);
            return { content: "Error generating content.", sources: [] };
        }
    }, []);

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
        sendChatMessage,
        lastCheckResult,
        smartWrite
    };
};
