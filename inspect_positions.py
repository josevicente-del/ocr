import fitz

def inspect_page_positions(page_num=1):
    doc = fitz.open("Cosas/20260604142405.pdf")
    page = doc[page_num - 1]
    
    print(f"=== POSITIONS FOR PAGE {page_num} ===")
    print("Page Rect:", page.rect)
    
    words = page.get_text("words")
    # A word is: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
    print(f"Total words: {len(words)}")
    
    # Let's save all words to a file for analysis
    with open(f"page_{page_num}_words.txt", "w", encoding="utf-8") as f:
        f.write("x0\ty0\tx1\ty1\tword\tblock_no\tline_no\tword_no\n")
        for w in words:
            f.write(f"{w[0]:.2f}\t{w[1]:.2f}\t{w[2]:.2f}\t{w[3]:.2f}\t{repr(w[4])}\t{w[5]}\t{w[6]}\t{w[7]}\n")
            
    print(f"Saved words to page_{page_num}_words.txt")

if __name__ == "__main__":
    inspect_page_positions(1)
    inspect_page_positions(5)
