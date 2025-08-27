# CLAUDE.md - Critical Architecture & Engineering Guidelines

*Created: 2025-08-27*
*Last Updated: 2025-08-27*

## 🚨 CRITICAL: Repository Architecture

### Repository Separation (MUST READ)

This project consists of **TWO SEPARATE REPOSITORIES** with different purposes:

1. **Embody-Network** (this repository)
   - Main orchestration and management system
   - The `autonomy/` folder here is **FOR LOCAL TESTING ONLY**
   - The `autonomy/` folder is **GITIGNORED** - never commit it
   - Changes to autonomy functionality should **NOT** be made here

2. **Unreal_Vtuber** (separate repository)
   - Contains the **ACTUAL PRODUCTION** VTuber code
   - This is where **ALL VTuber/autonomy changes** should be made
   - Has its own CI/CD pipeline and deployment system
   - Located at: `https://github.com/its-DeFine/Unreal_Vtuber`

### ⚠️ Common Mistakes to Avoid

1. **NEVER** commit autonomy changes to Embody-Network
2. **NEVER** create VTuber-related PRs in Embody-Network
3. **ALWAYS** make VTuber changes in the Unreal_Vtuber repository
4. **ALWAYS** verify which repository you're working in before making changes

### Correct Workflow for VTuber Changes

```bash
# WRONG - Don't do this:
cd /home/geo/operation/autonomy
# Make changes
git commit  # This would fail - autonomy is gitignored

# CORRECT - Do this instead:
cd /home/geo/test/Unreal_Vtuber  # Or wherever the Unreal_Vtuber repo is cloned
# Make changes
git commit
gh pr create --repo its-DeFine/Unreal_Vtuber
```

## 📁 Repository Structure

### Embody-Network Repository
```
/home/geo/operation/
├── scripts/               # Orchestration scripts
├── docs/                 # Documentation
├── docker/               # Docker configurations
├── manager/              # Central manager code
├── autonomy/             # GITIGNORED - Local testing only
└── .gitignore           # Contains: autonomy/
```

### Unreal_Vtuber Repository
```
/home/geo/test/Unreal_Vtuber/  # Or other clone location
├── NeuroBridge/          # Core VTuber module
├── docker-compose.*.yml  # Docker configurations
├── neurosync-worker/     # Worker implementations
├── webapp/               # Web interface
├── scripts/              # VTuber-specific scripts
└── .github/workflows/    # CI/CD pipelines
```

## 🔄 Update Systems

### Force Rebuild Feature

The force rebuild system is implemented **DIFFERENTLY** in each repository:

1. **Embody-Network**: Uses `scripts/dual_update_manager.py` for orchestrator updates
2. **Unreal_Vtuber**: Uses GitHub Actions workflow for container rebuilds

**Important**: These are **independent systems** - changes to one don't affect the other.

### Where to Implement Updates

- **Orchestrator updates** → Embody-Network repository
- **VTuber container rebuilds** → Unreal_Vtuber repository
- **Central manager updates** → Embody-Network repository
- **NeuroBridge changes** → Unreal_Vtuber repository

## 🏗️ Development Guidelines

### Local Testing

The `autonomy/` folder in Embody-Network is for:
- Testing integration with central manager
- Local development experiments
- Temporary debugging

**Remember**: Changes here are **NEVER committed** to git.

### Production Changes

All production VTuber changes must:
1. Be made in the Unreal_Vtuber repository
2. Go through PR review process
3. Trigger automated rebuilds via GitHub Actions
4. Be deployed through the proper CI/CD pipeline

## 🚀 Deployment Architecture

### Central Manager (Embody-Network)
- Manages multiple orchestrators
- Handles agent registration
- Coordinates distributed systems
- **Does NOT contain VTuber code**

### VTuber System (Unreal_Vtuber)
- Self-contained VTuber implementation
- Connects to central manager via API
- Has its own update/rebuild system
- Deployed independently

## 📋 Quick Reference Checklist

Before making changes, ask yourself:

- [ ] Am I changing VTuber/autonomy code? → Use **Unreal_Vtuber** repo
- [ ] Am I changing orchestrator/manager code? → Use **Embody-Network** repo
- [ ] Am I in the correct repository?
- [ ] Is this a local test or production change?
- [ ] Have I checked the `.gitignore` to ensure I'm not committing test files?

## 🔍 Finding the Right Repository

```bash
# Check current repository
git remote -v

# If you see:
# https://github.com/its-DeFine/Embody-Network → Orchestrator/Manager work
# https://github.com/its-DeFine/Unreal_Vtuber → VTuber/Autonomy work

# Common locations:
# Embody-Network: /home/geo/operation/
# Unreal_Vtuber: /home/geo/test/Unreal_Vtuber/
```

## ⚡ Emergency Commands

If you accidentally made changes in the wrong place:

```bash
# If you modified autonomy/ in Embody-Network by mistake:
cd /home/geo/operation
git status  # Should show nothing (autonomy is gitignored)

# Move changes to correct repository:
cp -r autonomy/* /home/geo/test/Unreal_Vtuber/
cd /home/geo/test/Unreal_Vtuber/
git add .
git commit -m "feat: [your change description]"
```

## 📝 Historical Context

- **August 2025**: Repositories were separated to improve modularity
- The `autonomy/` folder remains in Embody-Network for backward compatibility
- It's gitignored to prevent accidental commits
- All new development should follow the separated architecture

---

**Remember**: When in doubt, check which repository you're in and whether your changes belong there. The separation exists for good architectural reasons - respect it!