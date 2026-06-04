import fitz
import re

def extract_date_robust(text):
    # Search for date pattern allowing OCR errors
    # Day: 1-2 chars (digits or OCR digits)
    # Month: 1-2 chars (digits or OCR digits)
    # Year: 202 followed by digit/OCR digit
    # Let's map OCR digits: O/o->0, S/s->5, I/i/l/f->1, A/a->4?
    # Let's write a regex that matches the structure of date:
    pattern = r'\b[0-9OoSsIiyl]{1,2}\s*/\s*[0-9OoSsIiyl]{1,2}\s*/\s*202[0-9OoSsIiyl]\b'
    matches = re.findall(pattern, text)
    if matches:
        raw = matches[0]
        # Clean the match
        cleaned = raw.replace(" ", "")
        # Replace OCR chars with digits
        result = ""
        for char in cleaned:
            if char in ('O', 'o'):
                result += '0'
            elif char in ('I', 'i', 'l', 'f'):
                result += '1'
            elif char in ('S', 's'):
                result += '5'
            elif char == 'a': # sometimes 'a' might be '4' (e.g. 3/a6/2026? wait! page 57 has '3/a6/2026' where a -> 0 or 06?)
                # Wait, page 57 groups had '3/a6/2026' -> should be 3/06/2026!
                # Ah! 'a' in 'a6' was probably read instead of '0'! So 'a' -> '0'.
                result += '0'
            elif char.isdigit() or char == '/':
                result += char
        return result
    return None

def test_dates():
    doc = fitz.open("Cosas/20260604142405.pdf")
    unmatched = []
    for idx in range(len(doc)):
        page = doc[idx]
        text = page.get_text()
        dt = extract_date_robust(text)
        if not dt:
            unmatched.append(idx+1)
            print(f"Page {idx+1}: FAILED")
        else:
            # Let's print raw date also to verify
            pattern = r'\b[0-9OoSsIiyl]{1,2}\s*/\s*[0-9OoSsIiyl]{1,2}\s*/\s*202[0-9OoSsIiyl]\b'
            raw = re.findall(pattern, text)[0]
            print(f"Page {idx+1}: Raw={repr(raw)} -> Cleaned={dt}")
            
    print(f"Total: {len(doc)}, Unmatched count: {len(unmatched)}")

if __name__ == "__main__":
    test_dates()
