# Evidence-Based Health App & FSSAI Vector Database

A health advisory and compliance analysis system grounded in peer-reviewed scientific research papers and statutory FSSAI (Food Safety and Standards Authority of India) regulations.

---

## Interactive Launcher (`start.cmd` / `start.cms`)

To launch the interactive terminal interface at any time, run:
```cmd
start.cmd
```
*(or `./start.cmd` in PowerShell / `start.cms`)*

### Interactive Menu Options:
- **`[1] Search & Fetch Research Papers`**: Searches open-access biomedical literature (Europe PMC & arXiv), checks the deduplication index, displays summaries/abstracts, and downloads user-approved PDFs into `data/research_papers/`.
- **`[2] View Kept Research Papers in Index`**: Inspects all currently stored and reviewed papers.
- **`[3] Ingest Documents into Vector Database`**: Indexes research papers and FSSAI rules into ChromaDB.
- **`[4] Run Grounded Health & FSSAI Query`**: Queries the vector database and generates evidence-backed advisories with citations.
- **`[5] Check Ollama Embedding Service Status`**: Verifies connectivity to the local Ollama daemon and embedding model.
- **`[0] Exit`**

---

## Research Paper Fetcher Details

### How It Works:
1. **Prompt / Idea**: Enter any topic (e.g., `curcumin bioavailability`, `trans fat cardiovascular risk`, `stevia gut microbiome`).
2. **Paper Count**: Specify how many candidates to retrieve (default: 5).
3. **Open-Access Search**: Queries **Europe PMC** (indexing PubMed and PubMed Central for peer-reviewed health/clinical studies) and **arXiv**.
4. **Persistent Deduplication Index** (`data/research_papers_index.json`):
   - Compares candidate DOIs, PMCIDs, and normalized titles against the registry.
   - Automatically skips papers already marked as `kept` or `discarded`.
5. **Interactive Review**:
   - Prints Title, Authors, Year, Journal, DOI, and formatted Abstract.
   - You decide:
     - `y`: Keep and download full-text PDF to `data/research_papers/` (marked as `kept`).
     - `n`: Discard (marked as `discarded` in the index so it is never shown again).
     - `s`: Skip without indexing (can appear in future searches).
     - `q`: Quit back to menu.

---

## Command Line Direct Usage

### Run Paper Fetcher Directly:
```bash
python -m health_app.terminal_runner --fetch
```

### Ingest Documents into ChromaDB:
```bash
# Ingest with fast mock embeddings (offline/testing):
python -m health_app.terminal_runner --ingest --mock

# Ingest with active Ollama:
python -m health_app.terminal_runner --ingest
```

### Query Advisory Engine:
```bash
python -m health_app.terminal_runner --query "What are the health risks of trans fats?" --mock
```

### Run Automated Tests:
```bash
python -m pytest tests/ -v
```
