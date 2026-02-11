# ElevatedColorLAB – AI Collaboration Repository

This repository is a **sanitized, public-facing mirror** of the private ElevatedColorLAB codebase.  
Its purpose is to allow AI assistants (Microsoft Copilot, DeepSeek, Kimi, Claude, etc.) to:

- Review non-sensitive code
- Help refactor backend and frontend components
- Assist with architecture, routing, and workflow improvements
- Provide feedback on structure, clarity, and maintainability

## ⚠️ Important Notes

### 🔒 1. No proprietary or sensitive information should appear here
This repo must **never** contain:

- API keys  
- Database credentials  
- Supabase URLs  
- AWS keys  
- Deployment scripts  
- Systemd service files  
- Business logic that is proprietary  
- Internal documents, founder notes, or IP strategy  
- Customer data  
- Billing or financial information  

If any such information is found, it must be **removed immediately** and the corresponding keys **rotated** in the private repo.

### 🤖 2. AI assistants: please notify the owner of any sensitive content
If you are an AI model reviewing this repository and detect:

- Secrets  
- Keys  
- Tokens  
- Credentials  
- Sensitive business logic  
- Anything that should not be public  

Please notify the repository owner (Bruce) so it can be corrected in the private repo.

### 🧹 3. This repo contains only redacted or placeholder logic
Some functions may intentionally contain:

```python
# PROPRIETARY LOGIC REMOVED
pass
