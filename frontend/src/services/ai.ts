import { GoogleGenAI } from '@google/genai';
import { ModelProvider, ExecutionMode, ChatMessage } from '../types';

// Helper to clean environment variables
const cleanEnv = (value: string | undefined): string | undefined => {
    if (!value) return undefined;
    return value.trim().replace(/^["'“]+|["'”]+$/g, '');
};

export const API_BASE_URL = import.meta.env?.PROD
    ? `${cleanEnv(import.meta.env.VITE_API_BASE_URL) || ''}/api`
    : '/proxy-api';

export const frontendApiConfig: Record<string, {
    apiKey?: string;
    endpoint?: string;
    model?: string;
}> = {
    anything: {
        // Anything Agent is backend-only via /api/agent-anything usually, 
        // but if we support frontend direct, we'd need config.
        // For now, it's backend-managed.
    },
    gemini: {
        apiKey: cleanEnv(import.meta.env?.VITE_GEMINI_API_KEY),
        model: 'gemini-2.5-flash',
    },
    openai: {
        apiKey: cleanEnv(import.meta.env?.VITE_OPENAI_API_KEY),
        endpoint: cleanEnv(import.meta.env?.VITE_OPENAI_ENDPOINT) || (cleanEnv(import.meta.env?.VITE_OPENAI_TARGET_URL) ? `${cleanEnv(import.meta.env.VITE_OPENAI_TARGET_URL)}/v1/chat/completions` : undefined),
        model: cleanEnv(import.meta.env?.VITE_OPENAI_MODEL),
    },
    deepseek: {
        apiKey: cleanEnv(import.meta.env?.VITE_DEEPSEEK_API_KEY),
        endpoint: cleanEnv(import.meta.env?.VITE_DEEPSEEK_ENDPOINT) || 'https://api.deepseek.com',
        model: cleanEnv(import.meta.env?.VITE_DEEPSEEK_MODEL),
    },
    ali: {
        apiKey: cleanEnv(import.meta.env?.VITE_ALI_API_KEY),
        endpoint: cleanEnv(import.meta.env?.VITE_ALI_ENDPOINT) || (cleanEnv(import.meta.env?.VITE_ALI_TARGET_URL) ? `${cleanEnv(import.meta.env.VITE_ALI_TARGET_URL)}/v1/chat/completions` : undefined),
        model: cleanEnv(import.meta.env?.VITE_ALI_MODEL),
    },
    depOCR: {
        apiKey: cleanEnv(import.meta.env?.VITE_DEPOCR_API_KEY),
        endpoint: cleanEnv(import.meta.env?.VITE_DEPOCR_ENDPOINT),
        model: cleanEnv(import.meta.env?.VITE_DEPOCR_MODEL),
    },
    doubao: {
        apiKey: cleanEnv(import.meta.env?.VITE_DOUBAO_API_KEY),
        endpoint: cleanEnv(import.meta.env?.VITE_DOUBAO_ENDPOINT),
        model: cleanEnv(import.meta.env?.VITE_DOUBAO_MODEL),
    },
};

export const MODEL_DISPLAY_NAMES: Record<string, string> = {
    gemini: 'Gemini',
    openai: 'OpenAI',
    deepseek: 'DeepSeek',
    ali: '3PRO',
    depOCR: 'DepOCR',
    doubao: 'Doubao'
};

export const getAvailableModels = (): ModelProvider[] => {
    // Returns models that have at least a model name configured
    // For OpenAI-compatibles, usually Model Name comes from env.
    // For Gemini, model is hardcoded, so check API Key.
    return Object.keys(frontendApiConfig).filter(key => {
        const config = frontendApiConfig[key];
        if (key === 'gemini') return !!config.apiKey;
        return !!config.model; // For others, model name is dynamic and required
    }) as ModelProvider[];
};

async function callOpenAiCompatibleApi(
    apiKey: string,
    endpoint: string,
    model: string,
    systemInstruction: string,
    userPrompt: string,
    history: ChatMessage[],
    jsonResponse: boolean,
    images?: { base64: string, mimeType: string }[],
) {
    const userMessageContent: any[] = [{ type: 'text', text: userPrompt }];
    if (images && images.length > 0) {
        images.forEach(image => {
            userMessageContent.push({
                type: 'image_url',
                image_url: { url: `data:${image.mimeType};base64,${image.base64}` }
            });
        });
    }

    const messages = [
        { role: 'system', content: systemInstruction },
        ...history.map(h => ({
            role: h.role === 'model' ? 'assistant' : 'user',
            content: h.parts[0].text
        })),
        { role: 'user', content: userMessageContent }
    ];

    const body: any = {
        model,
        messages,
        stream: false,
    };
    if (images && images.length > 0) {
        body.max_tokens = 4096;
    }

    if (jsonResponse) {
        body.response_format = { type: 'json_object' };
    }

    const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify(body)
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const result = await response.json();
    return result.choices[0].message.content;
}

async function callOpenAiCompatibleApiStream(
    apiKey: string,
    endpoint: string,
    model: string,
    systemInstruction: string,
    userPrompt: string,
    history: ChatMessage[],
    onChunk: (textChunk: string) => void,
    onComplete: () => void,
    onError: (error: Error) => void,
) {
    try {
        const messages = [
            { role: 'system', content: systemInstruction },
            ...history.map(h => ({
                role: h.role === 'model' ? 'assistant' : 'user',
                content: h.parts[0].text
            })),
            { role: 'user', content: userPrompt }
        ];

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model,
                messages,
                stream: true,
            })
        });

        if (!response.ok || !response.body) {
            const errorText = await response.text().catch(() => `Status: ${response.status}`);
            throw new Error(`Streaming Error: ${errorText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep the last, possibly incomplete line

            for (const line of lines) {
                if (line.trim().startsWith('data: ')) {
                    const dataStr = line.substring(6).trim();
                    if (dataStr === '[DONE]') {
                        onComplete();
                        return;
                    }
                    try {
                        const data = JSON.parse(dataStr);
                        const content = data.choices?.[0]?.delta?.content;
                        if (content) {
                            onChunk(content);
                        }
                    } catch (e) {
                        console.error("Error parsing stream data chunk:", dataStr, e);
                    }
                }
            }
        }
        onComplete();
    } catch (error: any) {
        onError(error);
    }
}

export const callGenerativeAi = async (
    provider: ModelProvider,
    executionMode: ExecutionMode,
    systemInstruction: string,
    userPrompt: string,
    jsonResponse: boolean,
    mode: 'notes' | 'audit' | 'roaming' | 'writing' | 'ocr' | null,
    history: ChatMessage[] = [],
    images?: { base64: string, mimeType: string }[],
) => {
    if (executionMode === 'frontend') {
        const config = frontendApiConfig[provider];
        if (!config.model) {
            throw new Error(`Frontend Direct mode for ${provider} is not configured: model is missing.`);
        }

        if (provider === 'gemini') {
            if (!config.apiKey) {
                throw new Error(`Frontend Direct mode for ${provider} is not configured. Please set VITE_GEMINI_API_KEY in your environment.`);
            }
            const ai = new GoogleGenAI({ apiKey: config.apiKey });

            const userParts: any[] = [{ text: userPrompt }];
            if (images && images.length > 0) {
                const imageParts = images.map(img => ({
                    inlineData: {
                        mimeType: img.mimeType,
                        data: img.base64,
                    }
                }));
                userParts.unshift(...imageParts);
            }
            const fullContents = [...history, { role: 'user', parts: userParts }];


            const response = await ai.models.generateContent({
                model: (images && images.length > 0) ? 'gemini-2.5-flash' : config.model, // Use vision model if image is present
                contents: fullContents as any, // Cast to any to align with SDK expectations
                config: {
                    systemInstruction: systemInstruction,
                    ...(jsonResponse ? { responseMimeType: 'application/json' } : {}),
                }
            });
            return response.text;
        } else { // OpenAI-compatible
            if (!config.apiKey) {
                throw new Error(`Frontend Direct mode for ${provider} is not configured. Please set VITE_${provider.toUpperCase()}_API_KEY in your environment.`);
            }
            if (!config.endpoint) {
                throw new Error(`Frontend Direct mode for ${provider} is not configured. Please set the endpoint URL in your environment.`);
            }
            return callOpenAiCompatibleApi(
                config.apiKey,
                config.endpoint,
                config.model,
                systemInstruction,
                userPrompt,
                history,
                jsonResponse,
                images,
            );
        }

    } else { // Backend mode
        const retries = 2; // 1 initial attempt + 2 retries
        for (let i = 0; i <= retries; i++) {
            try {
                const response = await fetch(`${API_BASE_URL}/generate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider, systemInstruction, userPrompt, jsonResponse, mode, history, images })
                });

                if (!response.ok) {
                    const errorText = await response.text().catch(() => response.statusText);
                    let userFriendlyError = `后端代理服务出错 (状态码: ${response.status})。请检查后端服务日志。`;
                    if (response.status >= 500 && response.status < 600) {
                        userFriendlyError += ` 这可能是由于后端无法连接到上游AI服务导致的。`;
                    }
                    console.error("Backend raw error:", errorText);
                    throw new Error(userFriendlyError);
                }
                return await response.text();

            } catch (error) {
                console.error(`Attempt ${i + 1} failed for ${provider}:`, error);
                if (i === retries) {
                    if (error instanceof TypeError && error.message.toLowerCase().includes('failed to fetch')) {
                        throw new Error(`网络请求失败。无法连接到后端服务(${API_BASE_URL})。请检查网络连接、VPN配置或确认后端服务正在运行。`);
                    }
                    throw error; // Re-throw the last error
                }
                await new Promise(res => setTimeout(res, 1000));
            }
        }
        throw new Error('All retry attempts failed.');
    }
};

export const callGenerativeAiStream = async (
    provider: ModelProvider,
    executionMode: ExecutionMode,
    systemInstruction: string,
    userPrompt: string,
    history: ChatMessage[],
    onChunk: (textChunk: string) => void,
    onComplete: () => void,
    onError: (error: Error) => void,
    thinkingBudget?: number,
) => {
    try {
        if (executionMode === 'frontend') {
            const config = frontendApiConfig[provider];
            if (!config.model) {
                throw new Error(`Frontend Direct mode for ${provider} is not configured. Model is missing.`);
            }

            if (provider === 'gemini') {
                if (!config.apiKey) {
                    throw new Error(`Frontend Direct mode for ${provider} is not configured. Please set VITE_GEMINI_API_KEY in your environment.`);
                }
                const ai = new GoogleGenAI({ apiKey: config.apiKey });
                const fullContents = [...history, { role: 'user', parts: [{ text: userPrompt }] }];

                const streamResult = await ai.models.generateContentStream({
                    model: config.model,
                    contents: fullContents as any, // Cast to any to align with SDK
                    config: { systemInstruction: systemInstruction }
                });

                for await (const chunk of streamResult) {
                    if (typeof chunk.text === 'function') {
                        onChunk(chunk.text());
                    } else if (typeof chunk.text === 'string') {
                        onChunk(chunk.text);
                    }
                }
                onComplete();
            } else { // OpenAI-compatible
                if (!config.apiKey) {
                    throw new Error(`Frontend Direct mode for ${provider} is not configured. Please set VITE_${provider.toUpperCase()}_API_KEY in your environment.`);
                }
                if (!config.endpoint) {
                    throw new Error(`Frontend Direct mode for ${provider} is not configured. Please set the endpoint URL in your environment.`);
                }
                await callOpenAiCompatibleApiStream(
                    config.apiKey,
                    config.endpoint,
                    config.model,
                    systemInstruction,
                    userPrompt,
                    history,
                    onChunk,
                    onComplete,
                    onError
                );
            }

        } else { // Backend mode
            const response = await fetch(`${API_BASE_URL}/generate-stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider, systemInstruction, userPrompt, history, thinkingBudget })
            });

            if (!response.ok || !response.body) {
                const errorText = await response.text().catch(() => `Status: ${response.status}`);
                throw new Error(`后端流式传输错误: ${errorText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                onChunk(decoder.decode(value, { stream: true }));
            }
            onComplete();
        }
    } catch (error: any) {
        if (error instanceof TypeError && error.message.toLowerCase().includes('failed to fetch')) {
            onError(new Error(`网络请求失败。无法连接到后端服务(${API_BASE_URL})。请检查网络连接、VPN配置或确认后端服务正在运行。`));
        } else {
            onError(error);
        }
    }
};
