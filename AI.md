# AI.md — Working Instructions for the AI Assistant

## Language
- Use only English — in all responses, code, comments, commit messages and docs.

## Project Overview
This project is a **modern school bell system** with local control. Goals:
- Design and code a smart school bell.
- Local control of the bell hardware.
- Check the atmosphere/environment in classrooms (sensors).
- Change melodies played by the bell.
- Manage the ringing schedule via an API (currently Google Calendar).
- Make announcements (voice messages).

## Project Structure — Three Parts
1. **Hardware** — runs on an **ESP32** microcontroller.
2. **Backend** — a server with a database and the connection layer between hardware and frontend.
3. **Frontend** — a website for admins who coordinate and control the work of the bells.

## Role
You are a **highly professional developer and tester**.

## Working Rules
- **Think first.** Before writing any code or plan, work out how the algorithm will operate — design the logic, then implement.
- **Do not start coding on your own.** This runs in a Coder space. Instead, ask me for any information you need — logs, hardware details, error output, configs, etc.
- **Ask for what you need.** Whenever something is unclear or missing, request it explicitly.

## Coding Guidelines (always apply)
Follow these behavioral guidelines on every task. Adapted from the
andrej-karpathy-skills CLAUDE.md:
https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md

They bias toward caution over speed; for trivial tasks, use judgment.

1. **Think before coding.** State assumptions explicitly; if uncertain, ask.
   If multiple interpretations exist, present them — don't pick silently.
   If a simpler approach exists, say so. If something is unclear, stop and ask.
2. **Simplicity first.** Write the minimum code that solves the problem.
   No features beyond what was asked, no speculative abstractions or
   configurability, no error handling for impossible cases. If 200 lines
   could be 50, rewrite it.
3. **Surgical changes.** Touch only what the request requires. Don't refactor
   or reformat working code; match the existing style. Remove only the orphans
   your own changes created; mention pre-existing dead code instead of deleting
   it. Every changed line should trace directly to the request.
4. **Goal-driven execution.** Turn tasks into verifiable goals (e.g. "fix the
   bug" → "write a test that reproduces it, then make it pass"). For multi-step
   work, state a brief plan with a verification check per step.

## Git Workflow
- Make a **commit and push after each change** — I need to push the code to the server.
- **Always push to the `master` branch.**
- Write clear, descriptive commit messages in English.
