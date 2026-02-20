# Implementation Plan: RollMind Oracle Web App

This document outlines the architecture and design for the RollMind Oracle, a sleek, minimalist web interface for interacting with the fine-tuned Gemma 7B D&D model.

## 1. Core Concept: The "Oracle"
Unlike a chatbot, the RollMind Oracle is a single-turn reference tool. Each interaction is a distinct consultation of the model's internalized D&D 2024 rules.

- **Interaction Style:** Single question -> Streamed answer.
- **No Follow-ups:** Each Q&A pair is standalone.
- **Visual Metaphor:** "Knowledge Cards" or "Archival Entries" instead of chat bubbles.

## 2. Technical Architecture

### Backend (Python/FastAPI) - `app/api/`
- **Model Serving:** Uses `transformers` and `peft` to load the 4-bit quantized Gemma 7B model.
- **Streaming:** Implements Server-Sent Events (SSE) via `TextIteratorStreamer` for real-time token delivery.
- **Demand-Based Memory Management:**
    - **Lazy Load:** Model is only loaded into VRAM on the first request.
    - **TTL Offloading:** A background timer (default 10 mins) will move the model weights to CPU or clear them if no activity is detected, preserving GPU resources.
- **Endpoints:**
    - `GET /health`: Check if model is loaded/loading.
    - `POST /consult`: The main streaming endpoint.

### Frontend (Next.js/App Router) - `app/web/`
- **Styling:** Vanilla CSS for a professional, low-overhead interface.
- **State Management:** Simple React state to manage current session history.
- **Streaming Hook:** Custom implementation to consume SSE streams.

## 3. Visual Design (Modern Minimalist)

### Brand Identity
- **Background:** Deep Obsidian (`#0A0A0A`).
- **Primary Accent:** Antique Gold (`#C5A059`) - sampled from `RollMind-logo-only.webp`.
- **Text:** High-contrast white (`#FFFFFF`) for answers, muted gray (`#A0A0A0`) for metadata.

### UI Components
- **The Obsidian Header:** Contains the `RollMind-logo-only.webp` and the project title.
- **The Inquiry Zone:** A prominent, minimalist text area at the top/center.
- **The Knowledge Cards:** A vertical list of previous interactions.
    - Gold-bordered cards with a subtle fade-in animation.
    - Question at the top, followed by the streamed Markdown response.
- **Submit Button:** Custom icon using `RollMind-send.png`.

## 4. Project Structure
```text
app/
├── api/
│   ├── main.py (FastAPI Routes)
│   ├── model.py (Lazy-load & Offload logic)
│   └── utils.py (Prompt formatting)
└── web/
    ├── src/
    │   ├── app/ (Next.js Pages)
    │   ├── components/ (Card, Input, Header)
    │   └── styles/ (Vanilla CSS Modules)
    └── public/ (Assets)
```

## 5. Implementation Roadmap

### Phase 1: Heavy Lifting (API)
1. Install server dependencies (`fastapi`, `uvicorn`, `sse-starlette`).
2. Implement `model.py` with the 7.5GB VRAM limit logic and TTL timer.
3. Verify streaming via simple `curl` commands.

### Phase 2: The Portal (Web Scaffold)
1. Initialize Next.js project.
2. Set up the Obsidian/Gold global theme.
3. Build the layout and asset integration.

### Phase 3: The Interaction (Streaming & Cards)
1. Build the streaming consumer logic.
2. Create the "Knowledge Card" component with Markdown support.
3. Implement session-based history (local only).

### Phase 4: Polish
1. Add loading states ("Consulting the Archives...").
2. Finalize animations and responsiveness for tablet/desktop.
