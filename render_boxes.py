import fitz

def render_page_with_boxes(page_num=1):
    doc = fitz.open("Cosas/20260604142405.pdf")
    page = doc[page_num - 1]
    
    # Render page to a pixmap
    pix = page.get_pixmap(dpi=150)
    img_width, img_height = pix.width, pix.height
    print(f"Pixmap size: {img_width} x {img_height}")
    
    # We can also draw rectangles on the PDF page itself and save it as a PDF or image
    # Let's draw on the PDF page directly using page.draw_rect
    words = page.get_text("words")
    for w in words:
        # draw a thin rectangle around the word
        rect = fitz.Rect(w[0], w[1], w[2], w[3])
        page.draw_rect(rect, color=(1, 0, 0), width=0.5)
        # draw text block numbers
        page.insert_text((w[0], w[1]), f"{w[5]}:{w[6]}", fontsize=4, color=(0, 0, 1))
        
    doc.save(f"page_{page_num}_debug.pdf")
    print(f"Saved page_{page_num}_debug.pdf with boxes")

if __name__ == "__main__":
    render_page_with_boxes(1)
    render_page_with_boxes(5)
