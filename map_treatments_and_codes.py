import fitz
import re
from collections import Counter

def clean_code(raw):
    # Keep only digits and map OCR errors
    s = raw.replace('s', '5').replace('s', '5').replace('o', '0').replace('O', '0').replace('I', '1').replace('i', '1').replace('l', '1').replace('a', '0')
    s = re.sub(r'\D', '', s)
    return s

def test_mappings():
    doc = fitz.open("Cosas/20260604142405.pdf")
    
    mappings = []
    
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
                    
        # Find order number
        # We can extract order number for context
        order_num = ""
        # Search for order number in page text
        text_full = page.get_text()
        s_clean = re.sub(r'[^0-9A-Za-z]', '', text_full)
        pattern = r'3[8BA8]2[0Oo]2[6Gg][Ff][0Oo][1Iilf][1Iilf][0OoC][0Oo][0Oo]3[5sS](\d|[sS])(\d|[sS])'
        match = re.search(pattern, s_clean, re.IGNORECASE)
        if match:
            order_num = match.group(0)[-2:] # last two digits
            
        for row_idx in sorted(rows.keys()):
            row_words = rows[row_idx]
            
            codes = []
            desc_treat_words = []
            
            for rw in row_words:
                y_center = (rw[1] + rw[3]) / 2
                if 35 <= y_center <= 92:
                    codes.append(rw)
                elif 95 <= y_center <= 300:
                    desc_treat_words.append(rw)
                    
            code_str = "".join([w[4] for w in codes]).strip()
            if any(w in code_str for w in ["ARTICULO", "OBSE", "RVACIONES"]):
                continue
            if not code_str:
                continue
                
            # Clean code
            code_cleaned = clean_code(code_str)
            suffix = code_cleaned[-4:] if len(code_cleaned) >= 4 else ""
            
            # Separate desc and treatment
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
                    
            treat_str = " ".join([w[4] for w in treat_words]).strip()
            if treat_str:
                mappings.append((suffix, treat_str, f"P{page_idx+1}-O{order_num}"))
                
    # Count occurrences
    print("=== UNIQUE TREATMENT TEXTS ===")
    unique_treats = Counter([m[1] for m in mappings])
    for t, count in unique_treats.most_common():
        print(f"Treatment: {repr(t)} | Count: {count}")
        
    print("\n=== SUFFIX TO TREATMENT MAPPINGS ===")
    suffix_map = {}
    for suffix, treat, page in mappings:
        if suffix not in suffix_map:
            suffix_map[suffix] = Counter()
        suffix_map[suffix][treat] += 1
        
    for suffix in sorted(suffix_map.keys()):
        print(f"Suffix: {suffix}")
        for treat, count in suffix_map[suffix].most_common(3):
            print(f"  -> {repr(treat)} ({count} times)")

if __name__ == "__main__":
    test_mappings()
