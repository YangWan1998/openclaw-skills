---
name: translate-word
description: |
  Translate Word documents (.docx) to any language while preserving structure, formatting, images, and tables.
  Use when user wants to: (1) translate a Word document, (2) convert DOCX from one language to another, (3) create translated version of Word document.
  Triggers: "translate Word", "DOCX翻译", "把Word翻译成", "translate this document to Chinese/English/Japanese", "翻译文档"
---

# Word Document Translation

Translate Word (.docx) text while preserving structure, formatting, images, and tables.

## Advantages over PDF Translation

| Feature | Word | PDF |
|---------|------|-----|
| Text structure | ✅ True paragraphs, headings | ❌ Rendered fragments |
| Image preservation | ✅ Automatic | ❌ Manual/OCR needed |
| Table handling | ✅ Native table structure | ❌ Complex extraction |
| Font/layout issues | ✅ Auto-reflow | ❌ Fixed positions |
| Post-translation edit | ✅ Easy | ❌ Difficult |

## Workflow

### Step 1: Extract texts with structure

```bash
python {skill_path}/scripts/extract_texts.py <input.docx> [--output <extracted.json>] [--organize]
```

This extracts:
- All paragraphs with type (heading1/2/3, body, caption)
- All table cells
- Image count (images are preserved automatically)
- Unique texts for translation

**Organized mode** (`--organize` or `-O`): Creates a folder named after the input file (without extension) and places all output files inside:
- `A.docx` → `A/A.extracted.json`, `A/A.translations.json`, `A/A_EN.docx`
- Keeps all related files together for each document

### Step 2: Create translation mapping

Translate each text to target language. Create JSON file:

```json
{
  "Original Text 1": "Translated 1",
  "Original Text 2": "Translated 2",
  ...
}
```

Save as `translations.json` next to input file.

**Tips:**
- Keep proper nouns, abbreviations, technical terms unchanged when appropriate
- Maintain consistent terminology throughout
- For long documents, translate in batches

### Step 3: Apply translations

```bash
python {skill_path}/scripts/translate_word.py <input.docx> translations.json [<output.docx>] [--organize]
```

**Organized mode** (`--organize` or `-O`): Automatically places output in the folder created during extraction:
- `A.docx` + `A/A.translations.json` → `A/A_EN.docx`
- If output path is omitted, defaults to `<input>_EN.docx`

## Output naming

Append language suffix: `filename_EN.docx`, `filename_ZH.docx`, `filename_JA.docx`

## What gets preserved

- ✅ All images (embedded, positioned)
- ✅ Table structure (rows, columns, merged cells)
- ✅ Paragraph formatting (bold, italic, color, font size)
- ✅ Heading styles (Heading 1, Heading 2, etc.)
- ✅ Page layout (margins, orientation)
- ✅ Header/footer

## What gets translated

- ✅ Paragraph text
- ✅ Table cell text
- ✅ Caption text
- ❌ Text inside images (use OCR separately if needed)
- ❌ Embedded Excel charts (translate in source file)

## Example

```bash
# Extract texts
python scripts/extract_texts.py report.docx --output report.extracted.json

# Review extracted texts, create translations.json
# ... translate manually or with AI assistance ...

# Apply translations
python scripts/translate_word.py report.docx translations.json report_EN.docx
```

## Requirements

```bash
pip install python-docx
```

## Comparison with PDF Translation

Use **Word translation** when:
- You have the source .docx file
- Document has complex tables
- Document has many images
- You need to edit after translation

Use **PDF translation** when:
- You only have a PDF file
- Document is simple text-only
- You don't need to edit after translation
