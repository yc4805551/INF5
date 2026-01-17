import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.PROD
    ? `${(import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')}/api/smart-filler`
    : '/proxy-api/smart-filler';

export interface SourceData {
    filename: string;
    type?: 'excel' | 'docx' | 'image';
    columns?: string[];
    total_rows?: number;
    total_lines?: number;
    preview: any[];
}

export interface Recommendation {
    tables: {
        table_index: number;
        matches: string[];
        confidence: number;
    }[];
    placeholders: any[];
    error?: string;
}

export interface FillerMessage {
    id: string;
    role: 'user' | 'agent' | 'system';
    content: string;
    trace?: string[];
    timestamp: number;
    status: 'pending' | 'success' | 'error' | 'review_failed';
    critique?: string;
    suggestion?: string;
    plan?: PlanStep[];
    isInteractive?: boolean;
    instruction?: string; // Original instruction context
}

export interface PlanStep {
    step: number;
    description: string;
    tool_hint: string;
}

export const useFiller = () => {
    const [isUploading, setIsUploading] = useState(false);
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    const [sourceData, setSourceData] = useState<SourceData | null>(null);
    const [recommendations, setRecommendations] = useState<Recommendation | null>(null);
    const [chatHistory, setChatHistory] = useState<FillerMessage[]>([]);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await fetch(`${API_BASE}/status`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.source_loaded) {
                        setSourceData(data); // Assuming data matches SourceData interface or close enough
                        // SourceData expects: filename, type, columns?, preview?
                        // Backend returns: filename, type.
                        // We might need columns/preview for UI? The Header only uses filename.
                        // So minimal data is fine for header.
                    }
                }
            } catch (e) {
                console.error("Failed to fetch status", e);
            }
        };
        fetchStatus();

        // Listen for Global Refresh events?
        const handleRefresh = () => fetchStatus();
        window.addEventListener('canvas-refresh', handleRefresh);
        return () => window.removeEventListener('canvas-refresh', handleRefresh);
    }, []);

    const [currentPlan, setCurrentPlan] = useState<PlanStep[] | null>(null);
    const [isPlanning, setIsPlanning] = useState(false);


    const uploadSource = async (file: File) => {
        setIsUploading(true);
        setRecommendations(null); // Reset prev recommendations
        try {
            const formData = new FormData();
            formData.append('file', file);

            const res = await fetch(`${API_BASE}/upload-source`, {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const err = await res.text();
                throw new Error(err);
            }

            const data = await res.json();
            setSourceData(data);

            // Add system message
            const sysMsg: FillerMessage = {
                id: Date.now().toString(),
                role: 'system',
                content: `已加载文件: ${data.filename}`,
                timestamp: Date.now(),
                status: 'success'
            };
            setChatHistory(prev => [...prev, sysMsg]);

            return data;
        } catch (e: any) {
            console.error(e);
            alert(`上传失败: ${e.message}`);
            return null;
        } finally {
            setIsUploading(false);
        }
    };

    const getRecommendations = async () => {
        setIsAnalyzing(true);
        try {
            const res = await fetch(`${API_BASE}/recommendations`);
            if (!res.ok) throw new Error("Failed to get recommendations");
            const data = await res.json();
            setRecommendations(data);
            return data;
        } catch (e: any) {
            console.error(e);
            alert("分析失败，请确保您已打开一个 Word 文档");
        } finally {
            setIsAnalyzing(false);
        }
    };

    const fillTable = async (tableIndex: number) => {
        setIsAnalyzing(true);
        try {
            const res = await fetch(`${API_BASE}/execute-fill`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table_index: tableIndex })
            });
            if (!res.ok) throw new Error("Fill failed");
            const data = await res.json();

            const msg: FillerMessage = {
                id: Date.now().toString(),
                role: 'system',
                content: `填充成功！已插入 ${data.rows_added} 行数据。`,
                timestamp: Date.now(),
                status: 'success'
            };
            setChatHistory(prev => [...prev, msg]);

            return data;
        } catch (e: any) {
            console.error(e);
            alert(`填充失败: ${e.message}`);
        } finally {
            setIsAnalyzing(false);
        }
    };

    const runAgentTask = async (instruction: string, plan: PlanStep[] | null = null) => {
        if (!instruction.trim()) return;
        // Don't clear plan if we are executing specific plan
        if (!plan) {
            setCurrentPlan(null); // Clear any existing plan
        }

        const userMsgId = Date.now().toString();
        const userMsg: FillerMessage = {
            id: userMsgId,
            role: 'user',
            content: instruction,
            timestamp: Date.now(),
            status: 'success'
        };

        const agentMsgId = (Date.now() + 1).toString();
        const agentPendingMsg: FillerMessage = {
            id: agentMsgId,
            role: 'agent',
            content: 'Thinking...',
            timestamp: Date.now(),
            status: 'pending'
        };

        setChatHistory(prev => [...prev, userMsg, agentPendingMsg]);
        setIsAnalyzing(true);

        try {
            const modelConfig = {
                apiKey: localStorage.getItem('gemini_api_key'),
                provider: 'gemini',
                endpoint: '',
                model: 'gemini-2.5-flash'
            };

            const res = await fetch(`${API_BASE}/agent-task`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ instruction, modelConfig, plan }) // Send plan if exists
            });
            if (!res.ok) throw new Error("Agent task failed");
            const data = await res.json();

            // Plan A: Push Updates
            if (data.events && Array.isArray(data.events)) {
                data.events.forEach((evt: any) => {
                    if (evt.type === 'CANVAS_UPDATE') {
                        window.dispatchEvent(new Event('canvas-refresh'));
                    }
                });
            }

            setChatHistory(prev => prev.map(msg => {
                if (msg.id === agentMsgId) {
                    return {
                        ...msg,
                        content: data.status === 'success' ? 'Task Completed' : `Warning: ${data.message}`,
                        trace: data.trace,
                        status: data.status === 'success' ? 'success' : 'error'
                    };
                }
                return msg;
            }));

            return data;
        } catch (e: any) {
            console.error(e);
            setChatHistory(prev => prev.map(msg => {
                if (msg.id === agentMsgId) {
                    return {
                        ...msg,
                        content: `Execution failed: ${e.message}`,
                        status: 'error'
                    };
                }
                return msg;
            }));
        } finally {
            setIsAnalyzing(false);
        }
    };

    const generatePlan = async (instruction: string) => {
        if (!instruction.trim()) return;
        setIsPlanning(true);
        setCurrentPlan(null); // Clear previous

        try {
            const modelConfig = {
                apiKey: localStorage.getItem('gemini_api_key'),
                provider: 'gemini',
                endpoint: '',
                model: 'gemini-2.5-flash'
            };

            const res = await fetch(`${API_BASE}/plan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ instruction, modelConfig })
            });

            if (!res.ok) throw new Error("Planning failed");
            const data = await res.json();
            const plan = data.plan;

            // Add Agent Message with Plan
            const agentMsg: FillerMessage = {
                id: (Date.now() + 1).toString(),
                role: 'agent',
                content: '已为您生成执行计划，请审阅并确认执行：',
                timestamp: Date.now(),
                status: 'success',
                plan: plan,
                isInteractive: true,
                instruction: instruction
            };
            setChatHistory(prev => [...prev, agentMsg]);

            // We no longer set currentPlan state for side panel
        } catch (e: any) {
            console.error(e);
            const errMsg: FillerMessage = {
                id: Date.now().toString(),
                role: 'agent',
                content: `生成计划失败，请重试。错误: ${e.message}`,
                timestamp: Date.now(),
                status: 'error'
            };
            setChatHistory(prev => [...prev, errMsg]);
        } finally {
            setIsAnalyzing(false);
            setIsPlanning(false);
        }
    };

    const updateMessage = (id: string, updates: Partial<FillerMessage>) => {
        setChatHistory(prev => prev.map(msg => msg.id === id ? { ...msg, ...updates } : msg));
    };

    const getDebugLogs = async () => {
        try {
            // Add cache-busting timestamp
            const res = await fetch(`${API_BASE}/logs?t=${Date.now()}`);
            if (!res.ok) throw new Error("Failed to fetch logs");
            const data = await res.json();
            return data.logs;
        } catch (e: any) {
            console.error(e);
            return `Error fetching logs: ${e.message}`;
        }
    };

    return {
        isUploading,
        isAnalyzing,
        sourceData,
        recommendations,
        chatHistory, // Exposed
        uploadSource,
        getRecommendations,
        fillTable,
        runAgentTask,
        generatePlan,
        isPlanning,
        getDebugLogs,
        updateMessage // Export this
    };
};
