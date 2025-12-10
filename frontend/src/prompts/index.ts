/**
 * System Prompts for Co-Creation Canvas
 * Centralized location for all AI persona definitions and instruction templates.
 */

export const SYSTEM_BASE = `You are a professional co-creation writing assistant.`;

export const INSTRUCTIONS_TEMPLATE = `
INSTRUCTIONS:
1. ONLY if the user EXPLICITLY asks for a "First Draft", "Full Article", "Rewrite Document", or "Fill Canvas", start response with ":::CANVAS:::".
2. For normal questions (e.g., "Give me 3 titles", "Make this paragraph better"), DO NOT use ":::CANVAS:::". Instead, output Markdown code blocks in the chat.
3. If Refinement Mode is active, start response with ":::CANVAS:::" to stream the replacement directly into the document.
4. Support Tables.
`;

export interface PromptContext {
    requirements: string;
    references: string;
    documentContent: string;
    refinement?: {
        text: string;
    } | null;
}

/**
 * Builds the full system prompt based on current context.
 */
export const buildSystemPrompt = (context: PromptContext): string => {
    let prompt = SYSTEM_BASE;

    if (context.requirements.trim()) {
        prompt += `\n\n=== [REQUIREMENTS] ===\n${context.requirements}\n==================`;
    }

    if (context.references.trim()) {
        prompt += `\n\n=== [REFERENCE] ===\n${context.references}\n===============`;
    }

    prompt += `\n\n=== DOCUMENT ===\n\`\`\`markdown\n${context.documentContent}\n\`\`\`\n`;

    if (context.refinement) {
        prompt += `\nTASK: REWRITE ONLY the selected text below based on user instruction.\nSELECTED TEXT: "${context.refinement.text}"\n`;
    }

    prompt += INSTRUCTIONS_TEMPLATE;

    return prompt;
};
