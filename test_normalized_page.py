import fitz

def test_page_9_normalization():
    doc = fitz.open("Cosas/20260604142405.pdf")
    page = doc[8] # Page 9
    
    words = page.get_text("words")
    w_width, w_height = page.rect.width, page.rect.height
    
    # Normalize coordinates to 270 degree rotation equivalent
    normalized_words = []
    for w in words:
        x0_std = w_height - w[2]
        x1_std = w_height - w[0]
        y0_std = w_width - w[3]
        y1_std = w_width - w[1]
        normalized_words.append((x0_std, y0_std, x1_std, y1_std, w[4], w[5], w[6], w[7]))
        
    rows = {}
    for nw in normalized_words:
        x = (nw[0] + nw[2]) / 2 # center x
        y = (nw[1] + nw[3]) / 2 # center y
        
        if x < 425:
            row_idx = round((412.0 - x) / 22.56)
            if 0 <= row_idx < 15:
                if row_idx not in rows:
                    rows[row_idx] = []
                rows[row_idx].append(nw)
                
    for row_idx in sorted(rows.keys()):
        row_words = rows[row_idx]
        codes = []
        desc_treat_words = []
        qty_words = []
        
        for rw in row_words:
            y_center = (rw[1] + rw[3]) / 2
            if 35 <= y_center <= 92:
                codes.append(rw)
            elif 95 <= y_center <= 300:
                desc_treat_words.append(rw)
            elif 300 <= y_center <= 440:
                qty_words.append(rw)
                
        # Split desc_treat_words into Description and Treatment using relative clustering
        desc_words = []
        treat_words = []
        if desc_treat_words:
            x_coords = [(w[0] + w[2])/2 for w in desc_treat_words]
            min_x = min(x_coords)
            max_x = max(x_coords)
            if max_x - min_x > 4.0:
                midpoint = (min_x + max_x) / 2
                for rw in desc_treat_words:
                    x_center = (rw[0] + rw[2]) / 2
                    if x_center >= midpoint:
                        desc_words.append(rw)
                    else:
                        treat_words.append(rw)
            else:
                # Only one line exists. Is it description or treatment?
                # Usually it's description.
                desc_words = desc_treat_words
                
        codes.sort(key=lambda w: w[1])
        desc_words.sort(key=lambda w: w[1])
        treat_words.sort(key=lambda w: w[1])
        qty_words.sort(key=lambda w: w[1])
        
        code_str = " ".join([w[4] for w in codes])
        desc_str = " ".join([w[4] for w in desc_words])
        treat_str = " ".join([w[4] for w in treat_words])
        qty_str = " ".join([w[4] for w in qty_words])
        
        print(f"Row {row_idx}: Code={code_str} | Desc={desc_str} | Treat={treat_str} | Qty={qty_str}")

if __name__ == "__main__":
    test_page_9_normalization()
