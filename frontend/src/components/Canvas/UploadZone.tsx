import React, { useCallback } from 'react';
import { Upload } from 'lucide-react';

interface UploadZoneProps {
    onFileSelect: (file: File) => void;
    isUploading: boolean;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onFileSelect, isUploading }) => {
    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            onFileSelect(e.dataTransfer.files[0]);
        }
    }, [onFileSelect]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            onFileSelect(e.target.files[0]);
        }
    };

    return (
        <div
            className="upload-zone"
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                width: '100%',
                height: '256px',
                border: '2px dashed #ccc',
                borderRadius: '8px',
                cursor: 'pointer',
                backgroundColor: '#f9f9f9',
                transition: 'background-color 0.2s'
            }}
        >
            <label style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%', cursor: 'pointer' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', paddingTop: '20px', paddingBottom: '24px' }}>
                    <Upload size={40} color="#9ca3af" style={{ marginBottom: '12px' }} />
                    <p style={{ marginBottom: '8px', fontSize: '14px', color: '#6b7280' }}>
                        <span style={{ fontWeight: 600 }}>Click to upload</span> or drag and drop
                    </p>
                    <p style={{ fontSize: '12px', color: '#6b7280' }}>DOCX files only</p>
                </div>
                <input type="file" className="hidden" accept=".docx" onChange={handleChange} disabled={isUploading} style={{ display: 'none' }} />
            </label>
            {isUploading && <p style={{ color: '#3b82f6', marginTop: '8px' }}>Uploading...</p>}
        </div>
    );
};
