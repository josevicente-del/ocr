import fitz
import re

def clean_date_robust(raw):
    # Remove whitespace
    s = re.sub(r'\s+', '', raw)
    
    # Replace characters that should be slashes
    # We look for something like '3/06i2026' -> replace 'i' with '/'
    # Slashes are usually between day/month and month/year
    # Let's clean characters:
    # First, let's normalize separators: replace 'i', '\\', '|', ',' between digits with '/'
    s = re.sub(r'(?<=[0-9A-Za-z])(?:[i\\\|\,])(?=[0-9A-Za-z])', '/', s)
    
    # Now let's split by '/'
    parts = s.split('/')
    if len(parts) == 3:
        day, month, year = parts
        
        # Clean day
        day = day.replace('O', '0').replace('o', '0').replace('S', '5').replace('s', '5').replace('I', '1').replace('i', '1').replace('l', '1')
        
        # Clean month
        # E.g. 'Ub' -> '06', 'a' or 'A' -> '0'
        if month.lower() == 'ub':
            month = '06'
        else:
            month = month.replace('O', '0').replace('o', '0').replace('S', '5').replace('s', '5').replace('I', '1').replace('i', '1').replace('l', '1')
            month = month.replace('a', '0').replace('A', '0').replace('b', '6')
            
        # Clean year
        # E.g. '2U26' -> '2026', '2A26' -> '2026'
        year = year.replace('O', '0').replace('o', '0').replace('S', '5').replace('s', '5').replace('I', '1').replace('i', '1').replace('l', '1')
        year = year.replace('U', '0').replace('A', '0')
        
        # Keep only digits in each part
        day = re.sub(r'\D', '', day)
        month = re.sub(r'\D', '', month)
        year = re.sub(r'\D', '', year)
        
        # Pad day and month
        if len(day) == 1:
            day = '0' + day
        if len(month) == 1:
            month = '0' + month
            
        # Standardize year to 4 digits
        if len(year) == 2:
            year = '20' + year
            
        return f"{day}/{month}/{year}"
        
    return s

def extract_date_super_robust(text):
    # Match any pattern like day/month/year with OCR errors
    # Separator can be /, i, \, |, or comma
    # Day: 1-2 alphanumeric characters
    # Month: 1-2 alphanumeric characters
    # Year: 4 alphanumeric characters starting with 2 (or 202x)
    pattern = r'\b[0-9A-Za-z]{1,2}[\/i\\\|\,][0-9A-Za-z]{1,2}[\/i\\\|\,](?:202[0-9A-Za-z]|[22UuAa0Oo]{4})\b'
    matches = re.findall(pattern, text)
    if matches:
        return clean_date_robust(matches[0])
        
    # Fallback search if no boundary
    pattern_noboundary = r'[0-9A-Za-z]{1,2}[\/i\\\|\,][0-9A-Za-z]{1,2}[\/i\\\|\,](?:202[0-9A-Za-z]|[22UuAa0Oo]{4})'
    matches = re.findall(pattern_noboundary, text)
    if matches:
        return clean_date_robust(matches[0])
        
    return None

def test_super_robust_dates():
    doc = fitz.open("Cosas/20260604142405.pdf")
    unmatched = []
    for idx in range(len(doc)):
        page = doc[idx]
        text = page.get_text()
        dt = extract_date_super_robust(text)
        if not dt:
            unmatched.append(idx+1)
            print(f"Page {idx+1}: FAILED")
        else:
            print(f"Page {idx+1}: {dt}")
            
    print(f"Total: {len(doc)}, Unmatched count: {len(unmatched)}, Unmatched pages: {unmatched}")

if __name__ == "__main__":
    test_super_robust_dates()
