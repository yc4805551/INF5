import React from 'react';
import { UploadZone } from './components/UploadZone';
import { PreviewPane } from './components/PreviewPane';
import { ChatPane } from './components/ChatPane';
import { Download, FileText } from 'lucide-react';
import { useDocxEditor } from './hooks/useDocxEditor';

function App() {
  const {
    state,
    handleFileUpload,
    handleSendMessage,
    handleConfirm,
    handleDiscard,
    handleFormat,
    handleDownload,
    reset,
    handleBodyFormatConfirm,
    handleBodyFormatCancel,
    handleSelectionEdit,
    handleClearSelection
  } = useDocxEditor();

  const { previewData, isUploading, isProcessing, hasFile, isPendingConfirmation } = state;

  const [sidebarWidth, setSidebarWidth] = React.useState(400);
  const [isResizing, setIsResizing] = React.useState(false);

  const startResizing = React.useCallback((mouseDownEvent: React.MouseEvent) => {
    setIsResizing(true);
  }, []);

  const stopResizing = React.useCallback(() => {
    setIsResizing(false);
  }, []);

  const resize = React.useCallback(
    (mouseMoveEvent: MouseEvent) => {
      if (isResizing) {
        setSidebarWidth(mouseMoveEvent.clientX);
      }
    },
    [isResizing]
  );

  React.useEffect(() => {
    window.addEventListener("mousemove", resize);
    window.addEventListener("mouseup", stopResizing);
    return () => {
      window.removeEventListener("mousemove", resize);
      window.removeEventListener("mouseup", stopResizing);
    };
  }, [resize, stopResizing]);

  return (
    <div className="flex h-screen bg-gray-50 font-sans overflow-hidden" onMouseUp={stopResizing}>
      {/* Sidebar / Chat */}
      <div
        className="flex flex-col bg-white z-20 shadow-xl border-r border-gray-100 relative"
        style={{ width: sidebarWidth, minWidth: 300, maxWidth: 800 }}
      >
        <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-white">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg shadow-lg shadow-blue-600/30">
              <FileText className="text-white" size={20} />
            </div>
            <h1 className="text-lg font-bold text-gray-900 tracking-tight">Docx Editor</h1>
          </div>
          {hasFile && (
            <div className="flex gap-2">
              <button
                onClick={reset}
                className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all"
                title="Return to Upload"
              >
                <FileText size={20} />
              </button>
              <button
                onClick={handleDownload}
                className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all"
                title="Download"
              >
                <Download size={20} />
              </button>
            </div>
          )}
        </div>

        {!hasFile ? (
          <div className="p-6 flex-1 flex items-center justify-center bg-gray-50/50">
            <UploadZone onFileSelect={handleFileUpload} isUploading={isUploading} />
          </div>
        ) : (
          <ChatPane
            onSendMessage={handleSendMessage}
            isProcessing={isProcessing}
            isPendingConfirmation={isPendingConfirmation}
            onConfirm={handleConfirm}
            onDiscard={handleDiscard}
            onFormat={handleFormat}
            showBodyFormatDialog={state.showBodyFormatDialog}
            onBodyFormatConfirm={handleBodyFormatConfirm}
            onBodyFormatCancel={handleBodyFormatCancel}
            messages={state.messages}
            selectionContext={state.selectionContext}
            onClearSelection={handleClearSelection}
          />
        )}

        {/* Resize Handle */}
        <div
          className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-400 transition-colors z-50"
          onMouseDown={startResizing}
        />
      </div>

      {/* Main Preview Area */}
      <div className="flex-1 bg-gray-100/50 overflow-hidden relative">
        <PreviewPane
          paragraphs={previewData}
          onSelectionEdit={handleSelectionEdit}
        />
      </div>
    </div>
  );
}

export default App;
