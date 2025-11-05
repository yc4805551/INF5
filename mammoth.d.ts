// FIX: Removed the reference to "vite/client" to resolve a "Cannot find type definition file" error. The project does not use client-side Vite features like `import.meta.env`, so this reference is not needed.

declare namespace NodeJS {
  interface ProcessEnv {
    NODE_ENV: 'development' | 'production';
    API_KEY?: string;
    OPENAI_API_KEY?: string;
    DEEPSEEK_API_KEY?: string;
    ALI_API_KEY?: string;
    OPENAI_ENDPOINT?: string;
    OPENAI_MODEL?: string;
    DEEPSEEK_ENDPOINT?: string;
    DEEPSEEK_MODEL?: string;
    ALI_ENDPOINT?: string;
    ALI_MODEL?: string;
  }
}

declare module 'mammoth' {
  interface MammothResult {
    value: string;
    messages: any[];
  }

  const mammoth: {
    extractRawText(options: { arrayBuffer: ArrayBuffer }): Promise<MammothResult>;
  };

  export default mammoth;
}
