# GitHub Setup Guide for Archive-AI

## Initial Setup

Your repository is already initialized. Follow these steps to set up GitHub:

### 1. Configure Git (if not already done)

```bash
# Set your name and email (replace with your GitHub credentials)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Verify your configuration
git config --list
```

### 2. Create a GitHub Repository

1. Go to [GitHub](https://github.com) and sign in
2. Click the "+" icon in the top right → "New repository"
3. Repository name: `Archive-AI` (or your preferred name)
4. Description: "Local-first AI cognitive framework with autonomous agents"
5. Choose Public or Private
6. **DO NOT** initialize with README, .gitignore, or license (we already have files)
7. Click "Create repository"

### 3. Connect Local Repository to GitHub

After creating the repository on GitHub, you'll see setup instructions. Use these commands:

```bash
# Add the remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/Archive-AI.git

# Or if you prefer SSH (requires SSH key setup):
# git remote add origin git@github.com:YOUR_USERNAME/Archive-AI.git

# Verify remote was added
git remote -v
```

### 4. Stage and Commit Files

```bash
# Review what will be committed
git status

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Archive-AI v7.5 with MCP server and Master Agent"

# Check commit was created
git log
```

### 5. Push to GitHub

```bash
# Push to GitHub (first time)
git push -u origin main

# For subsequent pushes, you can just use:
# git push
```

### 6. Set Up Branch Protection (Optional)

On GitHub:
1. Go to Settings → Branches
2. Add rule for `main` branch
3. Enable "Require pull request reviews"
4. Enable "Require status checks"

## Daily Workflow

### Making Changes

```bash
# Check status
git status

# Add specific files
git add path/to/file.py

# Or add all changes
git add .

# Commit with descriptive message
git commit -m "Add feature: description of what changed"

# Push to GitHub
git push
```

### Creating a New Branch

```bash
# Create and switch to new branch
git checkout -b feature/new-feature-name

# Make changes, then commit
git add .
git commit -m "Add new feature"

# Push branch to GitHub
git push -u origin feature/new-feature-name
```

### Pulling Latest Changes

```bash
# Fetch and merge latest changes
git pull origin main
```

## Important Notes

### Files NOT tracked (in .gitignore):
- `venv/` - Virtual environment
- `models/` - Large model files (too big for git)
- `data/redis/` - Redis data files
- `.env` - Environment variables (sensitive data)
- `*.log` - Log files
- `__pycache__/` - Python cache files

### Files TO track:
- All source code
- Configuration files (without secrets)
- Documentation
- Docker files
- Requirements files

## SSH Key Setup (Alternative to HTTPS)

If you prefer SSH authentication:

### 1. Generate SSH Key

```bash
ssh-keygen -t ed25519 -C "your.email@example.com"
# Press Enter to accept default location
# Enter passphrase (or leave empty)
```

### 2. Add SSH Key to GitHub

```bash
# Copy public key
cat ~/.ssh/id_ed25519.pub

# Then on GitHub:
# 1. Go to Settings → SSH and GPG keys
# 2. Click "New SSH key"
# 3. Paste your public key
# 4. Click "Add SSH key"
```

### 3. Test SSH Connection

```bash
ssh -T git@github.com
# Should say: "Hi YOUR_USERNAME! You've successfully authenticated..."
```

## Troubleshooting

### If you get "remote origin already exists":

```bash
# Remove existing remote
git remote remove origin

# Add correct remote
git remote add origin https://github.com/YOUR_USERNAME/Archive-AI.git
```

### If push is rejected:

```bash
# Fetch remote changes first
git fetch origin

# Merge or rebase
git merge origin/main
# or
git rebase origin/main

# Then push again
git push
```

### If you committed sensitive data:

```bash
# Remove from git history (use git-filter-repo or BFG Repo-Cleaner)
# Then force push (only if you're the only contributor!)
git push --force
```

## Repository Structure Overview

```
Archive-AI/
├── .gitignore           # Files to ignore
├── README.md            # Project readme (you may want to create this)
├── docker-compose.yml   # Docker orchestration
├── requirements.txt     # Python dependencies
├── brain/              # Brain orchestrator
├── mcp-server/         # MCP server for agents
├── vorpal/             # Vorpal engine
├── goblin/             # Goblin engine
├── voice/              # Voice service
├── sandbox/            # Code sandbox
├── models/             # Model files (gitignored)
├── data/               # Data files (gitignored)
└── checkpoints/        # Development checkpoints
```

## Next Steps

1. ✅ Configure git user name and email
2. ✅ Create GitHub repository
3. ✅ Add remote origin
4. ✅ Create initial commit
5. ✅ Push to GitHub
6. Consider creating a README.md with project description
7. Consider adding LICENSE file
8. Set up GitHub Actions for CI/CD (optional)

