import fitz
import re

def clean_order_number(raw):
    # Remove all whitespace
    s = re.sub(r'\s+', '', raw)
    # Replace common OCR errors
    # Prefix mapping: should start with 38-2026F01100035
    # Let's map characters:
    # First letter can be 3, second B/A -> 8, third '-'
    s = re.sub(r'^[3B][8A]?\b', '38', s) # just in case
    # Let's replace 'B' or 'A' in the first two chars if it looks like 3B or 3A
    if len(s) >= 2 and s[0] == '3' and s[1] in ('B', 'A'):
        s = '38' + s[2:]
    elif len(s) >= 2 and s[0] == '3' and s[1] == '-':
        s = '38-' + s[2:]
    
    # Replace 'G' with '6' in '2026'
    s = s.replace('202G', '2026')
    # Replace 's' or 'S' with '5' in the last digits
    # For order number, it's typically 38-2026F01100035xx
    # Let's clean the prefix and format it as 38-2026F01100035xx
    # We can match the last digits
    match = re.search(r'38-2026F0110003[5sS](\d|[sS])(\d|[sS])', s, re.IGNORECASE)
    if match:
        cleaned = s.replace('s', '5').replace('S', '5').replace('o', '0').replace('O', '0')
        # Ensure it has exactly 38-2026F01100035xx format
        # Let's reconstruct it to be absolutely sure
        digits = re.findall(r'\d', cleaned)
        if len(digits) >= 15:
            # We want: 38-2026F01100035XX
            # Let's look at the last two digits
            last_two = ''.join(digits[-2:])
            return f"38-2026F01100035{last_two}"
    return s

def test_orders():
    doc = fitz.open("Cosas/20260604142405.pdf")
    unmatched = 0
    for idx in range(len(doc)):
        page = doc[idx]
        text = page.get_text()
        # Find order number pattern
        # Usually it starts with 38 or 3B or 3A, followed by -2026F or -202 6F etc.
        pattern = r'\b3[8AB8\s]*-\s*202\s*[6Gg]\s*[Ff]\s*0\s*1\s*1\s*0\s*0\s*0\s*3\s*[5Ss\s]*[0-9sSs\s]{2,3}\b'
        matches = re.findall(pattern, text)
        if matches:
            raw = matches[0]
            cleaned = clean_order_number(raw)
            print(f"Page {idx+1}: Raw={repr(raw)} | Cleaned={cleaned}")
        else:
            print(f"Page {idx+1}: NO MATCH FOR ORDER NUMBER!")
            unmatched += 1
            
    print(f"Total pages: {len(doc)}, Unmatched: {unmatched}")

if __name__ == "__main__":
    test_orders()
