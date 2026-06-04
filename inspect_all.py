import fitz
import re

def inspect_all():
    doc = fitz.open("Cosas/20260604142405.pdf")
    print(f"Total pages: {len(doc)}")
    
    with open("pdf_text_dump.txt", "w", encoding="utf-8") as f:
        for i, page in enumerate(doc):
            f.write(f"\n================ PAGE {i+1} ================\n")
            f.write(page.get_text())
            
    print("Dumped all pages text to pdf_text_dump.txt")

if __name__ == "__main__":
    inspect_all()
