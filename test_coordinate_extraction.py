import fitz
import re

def clean_extracted_order(text):
    # Remove all spaces and newlines
    s = re.sub(r'\s+', '', text)
    # Replace non-alphanumeric chars at start
    s = re.sub(r'^[^0-9A-Za-z]+', '', s)
    # We expect a format like: 38-2026F01100035XX
    # Let's clean the string. We replace common characters:
    # Let's find where '202' or '2O2' or '2o2' is.
    # The prefix should be '38' or '3B' or '3A'.
    # We replace punctuation or special chars near the start with '-'
    # E.g., '38*2026' -> '38-2026', '38,2026' -> '38-2026'
    s = re.sub(r'^(3[8AB8])[^a-zA-Z0-9]', r'\1-', s)
    # Ensure prefix is '38-'
    if s.startswith('3B-') or s.startswith('3A-'):
        s = '38-' + s[3:]
    
    # Replace common OCR misread letters in numbers:
    # O or o -> 0
    # I or i or l or f -> 1
    # S or s -> 5
    # Let's replace 'O'/'o' with '0' inside the digits section
    # Let's replace 'C' with '0' in '011C00' -> '01100'
    # Let's do selective replacements:
    # First, let's replace 2O26 or 2o26 with 2026
    s = re.sub(r'2[Oo]2\d', '2026', s)
    # Replace F0_11 with F011
    s = s.replace('F0_11', 'F011')
    # Replace FO11 with F011
    s = s.replace('FO11', 'F011')
    # Replace Fo11 with F011
    s = s.replace('Fo11', 'F011')
    # Replace C with 0 in the context of 011C00 -> 01100
    s = s.replace('011C00', '01100')
    # Replace i10 or 1f0 with 011 or 110 or whatever is appropriate:
    # The fixed part is 'F01100035'
    # Let's search for a 'F' or 'f' followed by stuff, and then a '3' or 's' or '5'
    # We can use regex to extract the digits
    # Let's just strip everything non-alphanumeric except '-'
    s = re.sub(r'[^0-9A-Za-z\-]', '', s)
    
    # If the string contains '2026F' or similar, let's look at the suffix
    # Let's extract all digits and 'F'
    match = re.search(r'38\-2026[Ff]([0-9A-Za-z]+)', s)
    if match:
        suffix = match.group(1)
        # Clean suffix: replace O->0, o->0, I->1, i->1, l->1, f->1, S->5, s->5, B->8
        cleaned_suffix = ""
        for char in suffix:
            if char in ('O', 'o'):
                cleaned_suffix += '0'
            elif char in ('I', 'i', 'l', 'f'):
                cleaned_suffix += '1'
            elif char in ('S', 's'):
                cleaned_suffix += '5'
            elif char in ('B', 'A'):
                cleaned_suffix += '8'
            elif char.isdigit():
                cleaned_suffix += char
        # The suffix should be '01100035xx'
        # Let's check length and format
        if len(cleaned_suffix) >= 10:
            # Reconstruct the order number
            # We want the last 2 digits as the sequence
            last_two = cleaned_suffix[-2:]
            return f"38-2026F01100035{last_two}"
        else:
            return f"38-2026F{cleaned_suffix}"
            
    # Fallback: if we just have digits, let's reconstruct it
    digits = re.findall(r'\d', s)
    if len(digits) >= 15:
        # Reconstruct
        last_two = ''.join(digits[-2:])
        return f"38-2026F01100035{last_two}"
        
    return s

def clean_extracted_date(text):
    s = re.sub(r'\s+', '', text)
    # replace common OCR errors in date
    s = s.replace('o', '0').replace('O', '0').replace('S', '5').replace('s', '5')
    # Match dd/mm/yyyy
    match = re.search(r'\b\d{1,2}/\d{1,2}/202\d\b', s)
    if match:
        return match.group(0)
    return s

def clean_extracted_client(text):
    s = re.sub(r'\s+', '', text)
    # Client code is usually 0000011
    # Replace common OCR errors: O/o -> 0, I/i/l/f -> 1
    cleaned = ""
    for char in s:
        if char in ('O', 'o'):
            cleaned += '0'
        elif char in ('I', 'i', 'l', 'f'):
            cleaned += '1'
        elif char.isdigit():
            cleaned += char
    # Keep only digits
    if len(cleaned) >= 7:
        return cleaned[:7]
    return cleaned

def test_coords():
    doc = fitz.open("Cosas/20260604142405.pdf")
    print(f"Total pages: {len(doc)}")
    
    for idx in range(len(doc)):
        page = doc[idx]
        words = page.get_text("words")
        
        # We filter words that fall in the header region:
        # x is between 430 and 480
        # y is between 30 and 320
        header_words = []
        for w in words:
            # w = (x0, y0, x1, y1, word, block_no, line_no, word_no)
            if 430 <= w[0] <= 485 and 30 <= w[1] <= 320:
                header_words.append(w)
                
        # Sort header words by their y coordinate (which is visual horizontal coordinate from left to right)
        header_words.sort(key=lambda x: x[1])
        
        # Combine words into text segments
        # Let's group words if they are close visually in y (e.g. diff < 15)
        groups = []
        current_group = []
        for w in header_words:
            if not current_group:
                current_group.append(w)
            else:
                # check if y distance from last word is small
                last_w = current_group[-1]
                if w[1] - last_w[1] < 15:
                    current_group.append(w)
                else:
                    groups.append(current_group)
                    current_group = [w]
        if current_group:
            groups.append(current_group)
            
        # For each group, reconstruct string
        group_texts = []
        for g in groups:
            text = " ".join([w[4] for w in g])
            group_texts.append((g[0][1], text)) # (y_coord, text)
            
        # Now let's try to extract Order Number, Client Code, and Date
        # Order number starts with 38 or 3B or 3A or contains 2026F or is the first group
        order_num = ""
        client_code = ""
        order_date = ""
        
        # Let's search by patterns in all group texts
        for y, text in group_texts:
            # Order number pattern
            if re.search(r'3[8AB]\s*[\-\*\,]?\s*2[0O]2', text) or '2026F' in text or '2O26F' in text or '2o26F' in text or '2026F' in text.replace(' ', ''):
                order_num = clean_extracted_order(text)
            # Date pattern
            elif '/' in text:
                order_date = clean_extracted_date(text)
            # Client code pattern (like 0000011)
            elif re.search(r'000\s*0011', text) or len(re.sub(r'\s+', '', text)) == 7 and re.sub(r'\s+', '', text).isdigit():
                client_code = clean_extracted_client(text)
                
        # Fallback if any is empty:
        # Let's print the extracted parts
        print(f"Page {idx+1}: Order={order_num} | Client={client_code} | Date={order_date} | Groups={[t[1] for t in group_texts]}")

if __name__ == "__main__":
    test_coords()
