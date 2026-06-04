import fitz

def test_date_coords():
    doc = fitz.open("Cosas/20260604142405.pdf")
    for idx in range(len(doc)):
        page = doc[idx]
        words = page.get_text("words")
        # Filter words in the date box: x in [430, 485], y in [210, 310]
        date_words = [w for w in words if 430 <= w[0] <= 485 and 210 <= w[1] <= 310]
        date_words.sort(key=lambda x: x[1]) # sort left to right visually
        text = " ".join([w[4] for w in date_words])
        print(f"Page {idx+1}: {repr(text)}")

if __name__ == "__main__":
    test_date_coords()
