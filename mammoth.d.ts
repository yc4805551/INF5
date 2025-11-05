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
