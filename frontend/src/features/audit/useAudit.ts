import { useState } from 'react';
import { frontendApiConfig } from '../../services/ai';

const API_BASE = import.meta.env.PROD
    ? `${(import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')}/api/audit`
    : '/proxy-api/audit';

export const useAudit = () => {
    const [isAuditing, setIsAuditing] = useState(false);
    const [auditResults, setAuditResults] = useState<any | null>(null);

    const runAudit = async (rules: string, modelKey: string = 'gemini') => {
        setIsAuditing(true);
        setAuditResults(null);

        // Get config
        const config = frontendApiConfig[modelKey] || {};
        const apiKey = config.apiKey;

        if (!apiKey) {
            setAuditResults({
                status: 'FAIL',
                issues: [],
                summary: `API Key Missing for ${modelKey}. Please configure env vars.`,
                error: "Missing API Key"
            });
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    rules,
                    model_config: {
                        provider: modelKey,
                        apiKey: apiKey,
                        endpoint: config.endpoint,
                        model: config.model || 'gemini-2.5-flash'
                    }
                })
            });

            if (!response.ok) {
                const err = await response.text();
                throw new Error(err || "Audit failed");
            }

            const data = await response.json();
            setAuditResults(data);
            return data;
        } catch (error: any) {
            console.error("Audit Error:", error);
            setAuditResults({
                status: 'FAIL',
                issues: [],
                summary: "Audit failed due to network or server error.",
                error: error.message
            });
            return null;
        } finally {
            setIsAuditing(false);
        }
    };

    return {
        isAuditing,
        auditResults,
        runAudit
    };
};
