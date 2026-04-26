# Trading Bot — LLM Wiki

A knowledge base maintained by Claude Code.
Based on Andrej Karpathy's LLM Wiki pattern.

## Purpose

Local paper trading bot wired to Phosphor (llama3.1:8b via Ollama) running two strategies: a deterministic trailing stop for short-term position management and a congressional disclosure copy strategy for long-term accumulation. This wiki captures why the architecture is designed the way it is, what alternatives were considered and rejected, and what the system is trying to become — not what the code does (the code already captures that).

---

## Folder Structure

```
NOUS/
  raw/          -- source documents (immutable -- never modify these)
  wiki/         -- markdown pages maintained by Claude
  wiki/index.md -- table of contents for the entire wiki
  wiki/log.md   -- append-only record of all operations
  templates/    -- page templates for manual or scaffolded notes
```

---

## Ingest Workflow

When the user adds a new source to `NOUS/raw/` and asks you to ingest it:

1. Read the full source document
2. Discuss key takeaways with the user before writing anything
3. Create a summary page in `NOUS/wiki/` named after the source
4. Create or update concept pages for each major idea, decision, or component
5. Add wiki-links ([[page-name]]) to connect related pages
6. Update `NOUS/wiki/index.md` with new pages and one-line descriptions
7. Append an entry to `NOUS/wiki/log.md` with the date, source name, and what changed

A single source may touch 10-15 wiki pages. That is normal.

---

## Page Format

Every wiki page follows this structure:

```markdown
# Page Title

**Summary**: One to two sentences describing this page.

**Sources**: List of raw source files this page draws from.

**Last updated**: Date of most recent update.

---

Main content goes here. Use clear headings and short paragraphs.

Link to related concepts using [[wiki-links]] throughout the text.

## Related Pages

- [[related-concept-1]]
- [[related-concept-2]]
```

---

## Citation Rules

- Every factual claim should reference its source file
- Use the format (source: filename.md) after the claim
- If two sources disagree, note the contradiction explicitly
- If a claim has no source, mark it as needing verification

---

## Question Answering

When the user asks a question:

1. Read `NOUS/wiki/index.md` first to find relevant pages
2. Read those pages and synthesize an answer
3. Cite specific wiki pages in your response
4. If the answer is not in the wiki, say so clearly
5. If the answer is valuable, offer to save it as a new wiki page

Good answers should be filed back into the wiki so they compound over time.

---

## Rules

- Never modify anything in the `NOUS/raw/` folder
- Always update `NOUS/wiki/index.md` and `NOUS/wiki/log.md` after changes
- Keep page names lowercase with hyphens (e.g. `llm-boundary.md`)
- Write in clear, plain language
- The wiki captures WHY, not WHAT -- the code captures what exists
- When uncertain about how to categorize something, ask the user
