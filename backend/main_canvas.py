from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from core.docx_engine import DocxEngine
from core.llm_engine import LLMEngine
from typing import List, Dict, Any
import io
import uvicorn

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
current_engine = DocxEngine()
llm_engine = LLMEngine() # Initialize with API key if available

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    current_engine.load_document(io.BytesIO(content))
    return {
        "message": "File uploaded successfully", 
        "preview": current_engine.get_preview_data(),
        "html_preview": current_engine.get_html_preview()
    }

@app.post("/create_with_text")
async def create_from_text(data: Dict[str, str] = Body(...)):
    text = data.get("text", "")
    current_engine.load_from_text(text)
    return {
        "message": "Document created from text",
        "preview": current_engine.get_preview_data(),
        "html_preview": current_engine.get_html_preview()
    }

@app.get("/preview")
async def get_preview():
    return current_engine.get_preview_data()

@app.get("/preview_html")
async def get_preview_html():
    return {"html": current_engine.get_html_preview()}

@app.post("/chat")
async def chat_with_doc(message: Dict[str, Any] = Body(...)):
    """
    Endpoint for natural language interaction.
    """
    user_text = message.get("message")
    model_config = message.get("model_config", {})
    history = message.get("history", [])
    selection_context = message.get("selection_context", [])
    
    if not user_text:
        raise HTTPException(status_code=400, detail="Message required")
    
    # Create staging copy for this new interaction if needed
    if not current_engine.staging_doc:
        current_engine.create_staging_copy()

    # Get current context from the STAGING doc
    context = current_engine.get_preview_data()
    
    # Interact with LLM
    response = llm_engine.chat_with_doc(
        user_message=user_text, 
        doc_context=context, 
        model_config=model_config,
        history=history,
        selection_context=selection_context
    )
    
    intent = response.get("intent")
    reply = response.get("reply") or "" # Ensure reply is never None
    code = response.get("code")
    
    is_staging = False
    
    if intent == "MODIFY":
        if code:
            # Execute Code on STAGING
            success, error_msg = current_engine.execute_code(code)
            
            if not success:
                 # If execution fails, return error in reply and downgrade to CHAT
                 reply = f"{reply}\n\n(Error executing changes: {error_msg})"
                 intent = "CHAT"
            else:
                 is_staging = True
        else:
            # MODIFY intent but no code? Downgrade to CHAT
            intent = "CHAT"
    
    return {
        "message": "Processed", 
        "reply": reply,
        "intent": intent,
        "preview": current_engine.get_preview_data(),
        "html_preview": current_engine.get_html_preview(),
        "is_staging": is_staging
    }

@app.post("/confirm")
async def confirm_changes():
    """
    Commits the staging document to be the real document.
    """
    success = current_engine.commit_staging()
    if not success:
        raise HTTPException(status_code=400, detail="No pending changes to confirm")
    
    return {
        "message": "Changes confirmed",
        "preview": current_engine.get_preview_data(),
        "html_preview": current_engine.get_html_preview()
    }

@app.post("/discard")
async def discard_changes():
    """
    Discards the staging document and reverts to the last committed state.
    """
    current_engine.discard_staging()
    return {
        "message": "Changes discarded",
        "preview": current_engine.get_preview_data(),
        "html_preview": current_engine.get_html_preview()
    }

@app.post("/patch")
async def apply_patch(patch: List[Dict[str, Any]] = Body(...)):
    """
    Direct patch endpoint (for debugging or advanced usage).
    """
    # For direct patch, let's assume it applies to committed doc for now, 
    # or we could make it support staging too. Let's keep it simple: applies to committed.
    success = current_engine.apply_patch(patch, use_staging=False)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to apply patch")
    return {"message": "Patch applied", "preview": current_engine.get_preview_data()}

@app.post("/format_official")
async def format_official_doc(data: Dict[str, Any] = Body(...)):
    """
    Endpoint for applying official formatting rules.
    """
    model_config = data.get("model_config", {})
    scope = data.get("scope", "all")

    # Ensure staging exists
    if not current_engine.staging_doc:
        current_engine.create_staging_copy()

    # Get context
    context = current_engine.get_preview_data()

    # Generate Formatting Code
    code = llm_engine.generate_formatting_code(context, model_config, scope)
    
    # Execute Code on STAGING
    success, error_msg = current_engine.execute_code(code)
    
    if not success:
         raise HTTPException(status_code=400, detail=f"Failed to execute formatting code: {error_msg}")

    return {
        "message": "Formatting applied", 
        "code_executed": code,
        "preview": current_engine.get_preview_data(),
        "html_preview": current_engine.get_html_preview(),
        "is_staging": True
    }

@app.post("/modify_local")
async def modify_local_doc(data: Dict[str, Any] = Body(...)):
    file_path = data.get("file_path")
    instruction = data.get("instruction")
    
    if not file_path or not instruction:
        raise HTTPException(status_code=400, detail="file_path and instruction are required")
    
    try:
        # 1. Load
        current_engine.load_from_path(file_path)
        
        # 2. Generate Code (using committed doc context)
        context = current_engine.get_preview_data()
        code = llm_engine.generate_code(instruction, context)
        
        # 3. Execute Code (directly on doc, no staging for local batch mode usually, but let's use staging logic if we want to be safe? 
        # Actually, for "modify local docx" user usually expects direct result or preview. 
        # Let's do: Load -> Execute -> Save.
        
        # We can use the existing execute_code which uses staging if available.
        # But load_from_path clears staging.
        # So execute_code will use self.doc.
        
        success, error_msg = current_engine.execute_code(code)
        if not success:
             raise HTTPException(status_code=500, detail=f"Failed to execute AI code: {error_msg}")
        
        # 4. Save
        # Save back to the same path
        current_engine.save_to_path(file_path)
        
        return {
            "message": "File processed and saved",
            "file_path": file_path,
            "preview": current_engine.get_preview_data()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download")
async def download_file():
    stream = current_engine.save_to_stream()
    return StreamingResponse(
        stream, 
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=modified.docx"}
    )

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5431"))
    
    uvicorn.run("main:app", host=host, port=port, reload=True)
