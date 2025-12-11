cd "/Users/avinash/Developer/Algo Trading/Fyers/fyers-algo"

# 1. Create COMPLETE .gitignore (protects credentials + secrets)
cat > .gitignore << 'EOF'
# Dependencies
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
ENV/

# Logs
logs/
*.log
log/

# Database
*.db
*.sqlite
*.sqlite3

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Build/Deploy
dist/
build/
*.egg-info/

# Fyers API Credentials (CRITICAL!)
.env
.env.local
.env.*.local

# Docker
docker-compose.override.yml

# Testing
.coverage
.pytest_cache/
htmlcov/

# Temporary files
*.tmp
*.temp
EOF

# 2. Initialize Git (first time)
git init

# 3. Add remote (your repo)
git remote add origin https://github.com/Avi5205/Fyers-Algo-Bot.git

# 4. Add all files (EXCEPT .gitignore exclusions)
git add .

# 5. First commit
git commit -m "🚀 Initial commit: Fyers Algo Trading Bot with multi-strategy consensus engine

✅ Real-time WebSocket streaming
✅ EMA Crossover + Swing + Scalping strategies  
✅ 2/3 consensus required for trades
✅ Paper & Live trading modes
✅ Session PnL summaries
✅ Production-ready structure

See README.md for full setup!"

# 6. Push to GitHub (main branch)
git branch -M master
git push -u origin master
