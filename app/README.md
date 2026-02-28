# RollMind Web Application

This directory contains the full-stack implementation of RollMind, a sleek web interface for interacting with the fine-tuned Gemma 7B D&D model.

## Architecture
- **Backend (`app/api/`):** FastAPI server handling model loading, VRAM management, and streaming inference.
- **Frontend (`app/web/`):** Next.js (App Router) interface with a minimalist "Obsidian & Gold" design.

---

## 🔥 One-Step Start

You can now launch both the **Backend API** and **Frontend Web** simultaneously using the included startup script.

From the `app/` directory:
```bash
./start.sh
```
This will start the FastAPI server on port 8000 and the Next.js development server on port 3000. Press `Ctrl+C` to stop both.

---

## 1. Backend Setup & Start

### Requirements
Ensure your Python environment has the necessary serving dependencies:
```bash
pip install fastapi uvicorn sse-starlette
```

### Configuration
Edit `app/api/.env` to configure your model and inference mode:

**Common Settings:**
- `INFERENCE_MODE`: Set to `local` (default) or `vertex`.

**Local Mode Settings:**
- `MODEL_ID`: Base model (e.g., `google/gemma-7b-it`)
- `ADAPTER_PATH`: Path to your best Step 2 checkpoint.
- `MAX_GPU_MEMORY`: Set based on your VRAM (e.g., `7.5GiB` for 12GB cards).

**Vertex Mode Settings:**
- `GOOGLE_CLOUD_PROJECT`: Your GCP Project ID.
- `GOOGLE_CLOUD_LOCATION`: The region where your endpoint is deployed (e.g., `us-east4`).
- `VERTEX_ENDPOINT_ID`: The **numeric ID** of your Vertex AI Endpoint (e.g., `9096886418218680320`).

### Start Server
Run from the `app/api/` directory (ensure `ADAPTER_PATH` in `.env` is relative to this location):
```bash
../../venv/bin/python main.py
```
The API will start on `http://localhost:8000`. The model will lazy-load into VRAM on the first inquiry.

---

## 2. Frontend Setup & Start

### Requirements
Ensure you have **Node.js** installed.

### Installation
From the `app/web/` directory:
```bash
npm install
```

### Start App
From the `app/web/` directory:
```bash
npm run dev
```
The interface will be available at `http://localhost:3000`.

---

## 3. Usage & Features

- **Single-Turn Interaction:** The UI is designed for standalone inquiries. Type a question and hit Enter or click the Consult icon.
- **Streaming:** Responses appear in real-time as the model generates tokens.
- **Auto-Offload:** To preserve your GPU for other tasks, the model will automatically offload from VRAM after 10 minutes of inactivity (configurable in `.env`).
- **Markdown Support:** The model's responses are rendered with full Markdown support, including bolding for mechanics and table formatting.
