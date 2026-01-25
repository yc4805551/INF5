import { API_BASE_URL } from './ai';

/**
 * 智能导出 Docx
 */
export const exportSmartDocxService = async (contentPayload: any, title: string) => {
    const response = await fetch(`${API_BASE_URL}/canvas/export-smart-docx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: contentPayload })
    });

    if (!response.ok) throw new Error('Export failed');

    // Trigger Download logic (handled by service or hook? Service returning blob is cleaner)
    return await response.blob();
};
