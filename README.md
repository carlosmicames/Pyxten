# Pyxten - Phase 1: Zoning Validation

AI-powered permit pre-validation platform for Puerto Rico, focusing on Tomo 6 (zoning compliance).

## Features

- ✅ Validate use/zoning compatibility
- ✅ Check compliance with Reglamento Conjunto Tomo 6
- ✅ Generate PDF validation reports
- ✅ Ministerial vs discretionary determination
- ✅ Bilingual support (Spanish/English)

## Quick Start

### 1. Clone repository
```bash
git clone https://github.com/yourusername/pyxten.git
cd pyxten
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 4. Run application
```bash
streamlit run app.py
```

### 5. Open browser
Navigate to `http://localhost:8501`

## Deployment to Streamlit Cloud

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Add `ANTHROPIC_API_KEY` to Secrets
5. Deploy!

## Project Structure
```
pyxten/
├── data/                    # Regulatory data (JSON)
├── src/                     # Source code
│   ├── validators/          # Validation logic
│   ├── ai/                  # Claude AI integration
│   ├── database/            # Data loading
│   └── utils/               # Report generation
├── app.py                   # Main Streamlit app
└── requirements.txt
```

## Roadmap

- [x] Phase 1: Tomo 6 validation
- [ ] Phase 2: Full PCOC validation
- [ ] Phase 3: Environmental compliance
- [ ] Phase 4: SBP integration
- [ ] Phase 5: Municipal expansion

## Partnership

Developed in collaboration with Hub Group and Hector Morales (former President, Junta de Planificación 2009-2012).

## License

Proprietary - All rights reserved
```

### **14. .gitignore**
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
dist/
*.egg-info/

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# Streamlit
.streamlit/secrets.toml

# OS
.DS_Store
Thumbs.db
