# InvisibleChat (ChatGPT edition) — Beginner Guide

InvisibleChat is a tiny Windows app that lets you chat with **ChatGPT** in a small floating window that’s **invisible to screen sharing** tools (best-effort via Windows APIs). It’s semi-transparent, always on top, and you can press **Ctrl+Alt+I** to hide/show it locally.

---

## What you need (simple checklist)

1. **A Windows 10 or 11 computer**
2. **Python** (version 3.10 or newer)
3. **VS Code** (a friendly editor)
4. An **OpenAI API key** (starts with `sk-...`)

> Your API key is stored securely in Windows Credential Manager through `keyring`.

---

## Step 1 — Install Python

1. Go to https://www.python.org/downloads/windows/
2. Download **Python 3.10+** (64-bit) and install it.
3. During installation, **check the box** “Add Python to PATH”.

---

## Step 2 — Install VS Code

1. Go to https://code.visualstudio.com/
2. Download and install **Visual Studio Code**.

Open VS Code when it finishes installing.

---

## Step 3 — Get the project

1. Create a folder like `C:\Projects\InvisibleChat`.
2. Put the project files in that folder (the folder should contain a subfolder `src`, plus `requirements.txt`, etc.).

Open the folder in VS Code:
- In VS Code: **File → Open Folder…** → choose your `InvisibleChat` folder.

---

## Step 4 — Create a virtual environment (safe sandbox)

In VS Code:
1. Open the built-in terminal: **View → Terminal**.
2. Run these commands:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
