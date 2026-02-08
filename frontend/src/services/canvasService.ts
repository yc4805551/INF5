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

export const importDocxService = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    // We assume backend is running on same host/port or proxied correctly.
    // Use relative path '/api' if configured in vite proxy, or API_BASE_URL.
    // API_BASE_URL is imported from './ai'.
    const response = await fetch(`${API_BASE_URL}/canvas/import-from-docx`, {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Import failed: ${errorText}`);
    }

    return await response.json();
};
