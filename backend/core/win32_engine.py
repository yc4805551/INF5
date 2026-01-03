
import sys
import os
import logging
import traceback

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WordAppEngine:
    def __init__(self):
        self.word = None
        self.doc = None

    def connect(self):
        """Attempts to connect to Word Application."""
        try:
            import win32com.client
            # dispatch 'Word.Application'
            self.word = win32com.client.Dispatch("Word.Application")
            self.word.Visible = False # Run in background
            self.word.DisplayAlerts = 0 # Turn off alerts
            logging.info(f"Connected to Word Version: {self.word.Version}")
            return True
        except ImportError:
            logging.error("pywin32 library not found. Please run 'pip install pywin32'.")
            return False
        except Exception as e:
            logging.error(f"Failed to connect to Word: {e}")
            logging.debug(traceback.format_exc())
            return False

    def get_accurate_page_count(self, doc_path):
        """Opens doc and gets precise page count."""
        if not self.word:
            if not self.connect(): return -1
            
        doc_path = os.path.abspath(doc_path)
        try:
            # Open doc
            self.doc = self.word.Documents.Open(doc_path, ReadOnly=True)
            
            # WdInformation Enumeration
            # wdNumberOfPagesInDocument = 4
            page_count = self.doc.ComputeStatistics(2) # wdStatisticPages = 2
            
            logging.info(f"Document {os.path.basename(doc_path)} has {page_count} pages.")
            
            self.doc.Close(SaveChanges=False)
            self.doc = None
            return page_count
        except Exception as e:
            logging.error(f"Error getting page count: {e}")
            if self.doc:
                try: self.doc.Close(SaveChanges=False)
                except: pass
            return -1

    def export_to_pdf(self, doc_path, pdf_path):
        """
        Exports the document to PDF using Word's native export.
        Values for WdExportFormat: wdExportFormatPDF = 17
        """
        if not self.word:
            if not self.connect(): return False
            
        doc_path = os.path.abspath(doc_path)
        pdf_path = os.path.abspath(pdf_path)
        
        try:
            logging.info(f"Exporting to PDF: {pdf_path}")
            self.doc = self.word.Documents.Open(doc_path, ReadOnly=True, Visible=False)
            
            # 17 = wdExportFormatPDF
            self.doc.ExportAsFixedFormat(
                OutputFileName=pdf_path,
                ExportFormat=17, 
                OpenAfterExport=False,
                OptimizeFor=0, # wdExportOptimizeForPrint
                CreateBookmarks=1, # wdExportCreateHeadingBookmarks
                DocStructureTags=True
            )
            
            self.doc.Close(SaveChanges=False)
            self.doc = None
            logging.info("PDF Export successful.")
            return True
        except Exception as e:
            logging.error(f"Error exporting to PDF: {e}")
            if self.doc:
                try: self.doc.Close(SaveChanges=False)
                except: pass
            return False

    def update_toc(self, doc_path):
        """
        Updates the Table of Contents (TOC) fields in the document.
        Critically useful after programmatic edits.
        """
        if not self.word:
            if not self.connect(): return False
            
        doc_path = os.path.abspath(doc_path)
        try:
            logging.info(f"Updating TOC for: {doc_path}")
            self.doc = self.word.Documents.Open(doc_path, ReadOnly=False, Visible=False)
            
            # Update all fields (including TOC)
            for table in self.doc.TablesOfContents:
                table.Update()
                
            # Also update page numbers
            # self.doc.Fields.Update() # Can be risky if there are other dynamic fields
            
            self.doc.Save()
            self.doc.Close()
            self.doc = None
            logging.info("TOC Updated.")
            return True
        except Exception as e:
            logging.error(f"Error updating TOC: {e}")
            if self.doc:
                try: self.doc.Close(SaveChanges=False)
                except: pass
            return False

    def quit(self):
        try:
            if self.word:
                self.word.Quit()
                self.word = None
                logging.info("Word Application closed.")
        except Exception as e:
            logging.error(f"Error closing Word: {e}")

def check_env():
    """Run a self-check"""
    print("--- Checking Win32 Environment ---")
    
    # 1. Check Library
    try:
        import win32com.client
        print("[OK] pywin32 library is installed.")
    except ImportError:
        print("[FAIL] pywin32 is NOT installed. Run: pip install pywin32")
        return

    # 2. Check Word App
    engine = WordAppEngine()
    if engine.connect():
        print(f"[OK] Successfully connected to Word (Version: {engine.word.Version})")
        engine.quit()
        print("--- Environment Check Passed ---")
    else:
        print("[FAIL] Could not connect to Word Application.")
        print("Please ensure Microsoft Word is installed and you have permissions.")

if __name__ == "__main__":
    check_env()
