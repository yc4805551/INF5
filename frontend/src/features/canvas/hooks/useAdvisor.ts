import { useState, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5179/api';

export interface AdvisorSuggestion {
    type: 'proofread' | 'polish' | 'logic';
    original: string;
    suggestion: string;
    reason: string;
}

export const useAdvisor = () => {
    const [suggestions, setSuggestions] = useState<AdvisorSuggestion[]>([]);
    const [isAdvising, setIsAdvising] = useState(false);

    const getSuggestions = useCallback(async (selectedText: string, contextText: string, modelConfig: any) => {
        if (!selectedText || selectedText.length < 2) return;

        setIsAdvising(true);
        setSuggestions([]); // Clear previous

        try {
            const res = await fetch(`${API_BASE}/agent/suggestions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    selectedText,
                    contextText,
                    modelConfig: {
                        apiKey: modelConfig.apiKey,
                        provider: modelConfig.provider,
                        endpoint: modelConfig.endpoint,
                        model: modelConfig.model
                    }
                })
            });

            if (!res.ok) {
                console.error("Advisor API Error");
                return;
            }

            const data = await res.json();
            if (data.status === 'success') {
                setSuggestions(data.suggestions);
            }
        } catch (e) {
            console.error("Advisor Fetch Error", e);
        } finally {
            setIsAdvising(false);
        }
    }, []);

    const removeSuggestion = useCallback((index: number) => {
        setSuggestions(prev => prev.filter((_, i) => i !== index));
    }, []);

    const clearSuggestions = useCallback(() => setSuggestions([]), []);

    return {
        suggestions,
        isAdvising,
        getSuggestions,
        clearSuggestions,
        removeSuggestion
    };
};
