import fitz
import re

def extract_order_from_text_super_robust(text):
    # Remove ALL non-alphanumeric characters
    s = re.sub(r'[^0-9A-Za-z]', '', text)
    
    # Now our string should contain something like "382026F0110003587"
    # Let's write the regex pattern for this cleaned string:
    # 3
    # [8BA8]
    # 2
    # [0Oo]
    # 2
    # [6Gg]
    # [Ff]
    # [0Oo]
    # [1Iilf]
    # [1Iilf]
    # [0OoC]
    # [0Oo]
    # [0Oo]
    # 3
    # [5sS]
    # (\d|[sS])
    # (\d|[sS])
    pattern = r'3[8BA8]2[0Oo]2[6Gg][Ff][0Oo][1Iilf][1Iilf][0OoC][0Oo][0Oo]3[5sS](\d|[sS])(\d|[sS])'
    match = re.search(pattern, s, re.IGNORECASE)
    if match:
        raw_match = match.group(0)
        # Clean the letters to numbers
        digits = []
        for char in raw_match:
            if char in ('O', 'o', 'C'):
                digits.append('0')
            elif char in ('I', 'i', 'l', 'f'):
                digits.append('1')
            elif char in ('S', 's'):
                digits.append('5')
            elif char in ('B', 'A'):
                digits.append('8')
            elif char.isdigit():
                digits.append(char)
            else:
                digits.append(char) # Keep 'F' or 'f'
        cleaned_str = "".join(digits).upper()
        # Ensure it starts with 38, is 382026F01100035XX
        if len(cleaned_str) >= 2:
            last_two = cleaned_str[-2:]
            return f"38-2026F01100035{last_two}"
    return None

def test_super_robust():
    doc = fitz.open("Cosas/20260604142405.pdf")
    unmatched = []
    for idx in range(len(doc)):
        page = doc[idx]
        text = page.get_text()
        order_num = extract_order_from_text_super_robust(text)
        if not order_num:
            unmatched.append(idx+1)
            
    print(f"Total: {len(doc)}, Unmatched count: {len(unmatched)}, Unmatched pages: {unmatched}")

if __name__ == "__main__":
    test_super_robust()
