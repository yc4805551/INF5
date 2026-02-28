/**
 * System Prompts for Co-Creation Canvas
 * Centralized location for all AI persona definitions and instruction templates.
 */

export const SYSTEM_BASE = `你是一位专业的公文写作与改写助手。`;

export const INSTRUCTIONS_TEMPLATE = `
【执行指令】:
1. 只有当用户**明确**要求“写初稿”、“写全文”、“重写文档”或“填充画布”时，才在回答开头使用 ":::CANVAS:::"。
2. 对于普通的问答（例如：“给我3个备选标题”、“把这段话改得更专业”），请勿使用 ":::CANVAS:::"。直接在聊天框中使用 Markdown 代码块输出建议。
3. 如果当前有被选中的文字（精修模式），请在请求的具体修改之前，始终在回答开头带上 ":::CANVAS:::"，以便直接替换。
4. 熟练支持处理 Markdown 表格。
5. **智能引用**: 当你提取和使用来自【参考资料 (REFERENCE)】里的信息时，你**必须**在句子末尾使用 \`[资料 ID]\` 的格式标注来源。示例：“根据相关要求 [资料 1]，该项目...”或“总预算为 500 万 [资料 2]”。
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
        prompt += `\n\n === [写作要求 (REQUIREMENTS)] ===\n${context.requirements} \n ================== `;
    }

    if (context.references.trim()) {
        prompt += `\n\n === [参考资料 (REFERENCE)] ===\n${context.references} \n =============== `;
    }

    prompt += `\n\n === [当前文档 (DOCUMENT)] ===\n\`\`\`markdown\n${context.documentContent}\n\`\`\`\n`;

    if (context.refinement) {
        prompt += `\n【当前任务】: 请严格根据用户指令，**仅重写**以下被选中的文本内容。\n【选中内容】: "${context.refinement.text}"\n`;
    }

    prompt += INSTRUCTIONS_TEMPLATE;

    return prompt;
};
