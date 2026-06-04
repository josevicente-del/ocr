import fitz
import re

def clean_quantity(raw):
    # Remove whitespace
    s = re.sub(r'\s+', '', raw)
    # Replace o/O with 0, S/s with 5, I/i/l/f with 1
    s = s.replace('o', '0').replace('O', '0').replace('S', '5').replace('s', '5').replace('I', '1').replace('i', '1').replace('l', '1')
    # Keep only digits and decimal separator (comma/dot)
    s = re.sub(r'[^0-9\,\.]', '', s)
    # Usually it's an integer like 2,00 -> 2, or 2
    # Let's split by comma or dot
    parts = re.split(r'[\,\.]', s)
    if parts:
        # The integer part
        val = parts[0]
        # Return as integer if possible
        if val.isdigit():
            return int(val)
    return raw

def test_quantities():
    doc = fitz.open("Cosas/20260604142405.pdf")
    
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        w_width, w_height = page.rect.width, page.rect.height
        rotation = page.rotation
        
        words = page.get_text("words")
        normalized_words = []
        for w in words:
            if rotation == 270:
                normalized_words.append((w[0], w[1], w[2], w[3], w[4]))
            elif rotation == 90:
                x0_std = w_height - w[2]
                x1_std = w_height - w[0]
                y0_std = w_width - w[3]
                y1_std = w_width - w[1]
                normalized_words.append((x0_std, y0_std, x1_std, y1_std, w[4]))
            else:
                # Fallback
                normalized_words.append((w[0], w[1], w[2], w[3], w[4]))
                
        # Group by row
        rows = {}
        for nw in normalized_words:
            x_center = (nw[0] + nw[2]) / 2
            y_center = (nw[1] + nw[3]) / 2
            if x_center < 425:
                row_idx = round((412.0 - x_center) / 22.56)
                if 0 <= row_idx < 15:
                    if row_idx not in rows:
                        rows[row_idx] = []
                    rows[row_idx].append(nw)
                    
        print(f"--- PAGE {page_idx+1} ---")
        for row_idx in sorted(rows.keys()):
            row_words = rows[row_idx]
            
            # Check if this row is actually a header or observations row
            # If the code or description contains labels like "ARTICULO", "OBSE", "RVACIONES", we skip
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
                    
            code_str = "".join([w[4] for w in codes]).strip()
            if any(w in code_str for w in ["ARTICULO", "OBSE", "RVACIONES"]):
                continue
            if not code_str:
                continue
                
            # Filter quantity words by y_center in [405, 445]
            qty_val_words = []
            for qw in qty_words:
                y_center = (qw[1] + qw[3]) / 2
                if 405 <= y_center <= 445:
                    qty_val_words.append(qw)
                    
            qty_val_words.sort(key=lambda w: w[1])
            qty_raw = "".join([w[4] for w in qty_val_words])
            qty_cleaned = clean_quantity(qty_raw)
            
            # Extract description & treatment
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
                    desc_words = desc_treat_words
                    
            desc_words.sort(key=lambda w: w[1])
            treat_words.sort(key=lambda w: w[1])
            
            desc_str = " ".join([w[4] for w in desc_words])
            treat_str = " ".join([w[4] for w in treat_words])
            
            print(f"  Row {row_idx}: Code={code_str} | Qty={qty_cleaned} | Desc={desc_str} | Treat={treat_str}")

if __name__ == "__main__":
    test_quantities()
