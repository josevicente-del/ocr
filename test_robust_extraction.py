import fitz
import re

def extract_order_from_text(text):
    # Remove all spaces and newlines to handle arbitrary word splitting
    s = re.sub(r'\s+', '', text)
    
    # We search for:
    # 3 followed by 8 or B or A
    # then maybe a separator like - or * or ,
    # then 2026 or 2O26 or 2o26 or 202G
    # then F or f
    # then 0 or O or o
    # then 1 or I or i or l
    # then 1 or I or i or l
    # then 0 or O or o or C
    # then 0 or O or o
    # then 0 or O or o
    # then 3 or s or S (sometimes 3 is read as 3)
    # then 5 or s or S
    # then digit or s or S
    # then digit or s or S
    
    # Let's write a regular expression for this sequence of characters:
    # Pattern: 3 [8BA] [-*,_]? 2 [0Oo] 2 [6Gg] [Ff] [0Oo_] [1Iilf] [1Iilf] [0OoC] [0Oo] [0Oo] 3 [5sS] (\d|[sS]) (\d|[sS])
    pattern = r'3[8BA8][\-\*\,\_]?2[0Oo]2[6Gg][Ff][0Oo\_][1Iilf][1Iilf][0OoC][0Oo][0Oo]3[5sS](\d|[sS])(\d|[sS])'
    match = re.search(pattern, s, re.IGNORECASE)
    if match:
        raw_match = match.group(0)
        # Let's clean the matched text
        # Keep only letters and numbers
        cleaned = re.sub(r'[^0-9A-Za-z]', '', raw_match)
        # Clean the letters to numbers
        digits = []
        for char in cleaned:
            if char in ('O', 'o', 'C'):
                digits.append('0')
            elif char in ('I', 'i', 'l', 'f'):
                digits.append('1')
            elif char in ('S', 's'):
                digits.append('5')
            elif char in ('B', 'A'):
                # First two chars: 3B or 3A -> 38
                # Suffix: B -> 8
                digits.append('8')
            elif char.isdigit():
                digits.append(char)
            else:
                # Keep 'F' as is
                digits.append(char)
        # Reconstruct: we should have "38" at start, then "2026F", then "01100035", then last two digits
        cleaned_str = "".join(digits)
        # Find the last 2 digits
        # The length of the cleaned string should be 16 (since it contains F)
        # E.g. 382026F01100035XX
        # Let's extract the last two digits
        if len(cleaned_str) >= 2:
            last_two = cleaned_str[-2:]
            return f"38-2026F01100035{last_two}"
            
    return None

def test_robust_extraction():
    doc = fitz.open("Cosas/20260604142405.pdf")
    unmatched = 0
    for idx in range(len(doc)):
        page = doc[idx]
        text = page.get_text()
        order_num = extract_order_from_text(text)
        if order_num:
            print(f"Page {idx+1}: {order_num}")
        else:
            print(f"Page {idx+1}: FAILED")
            unmatched += 1
            
    print(f"Total: {len(doc)}, Unmatched: {unmatched}")

if __name__ == "__main__":
    test_robust_extraction()
