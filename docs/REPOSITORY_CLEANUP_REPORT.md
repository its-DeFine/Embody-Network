# Repository Cleanup & Organization Report

## Files/Directories to Remove for Production

### 1. Development & Testing Artifacts
- **`__pycache__/`** - Python bytecode cache (should be gitignored)
- **`backup/` and `backups/`** - Old backup directories (should use version control instead)
- **`vtuber-dashboard-v2.html/`** - Empty directory owned by root (cleanup artifact)
- **`.pytest_cache/`** - Test cache directory (should be gitignored)

### 2. Test Files in Wrong Location
The following test files are in `/scripts/` instead of `/tests/`:
- `scripts/test_distributed_integration.py`
- `scripts/test_orchestrator_deployment.py`
- `scripts/test_livepeer_connectivity.py`
- `scripts/test_livepeer_auth.py`
- `scripts/test_cross_network.py`
- `scripts/live_distributed_test.py`
- `scripts/monitor_distributed_test.py`
- `scripts/manual_integration_test.py`

**Action**: Move to `/tests/integration/` directory

### 3. Development Files
- **`implement/`** - Development session directory (not needed in production)
- **`autonomy_local_customizations.md`** - Development notes (move to docs/)
- **`check_system_status.sh`** - Development utility (move to scripts/dev/)

## Current Repository Structure

```
/home/geo/operation/
├── app/                    ✅ Application code
├── autonomy/              ✅ Submodule (Unreal_Vtuber)
├── data/                  ✅ Data directory
├── docker/                ✅ Docker configurations
├── docs/                  ✅ Documentation
├── scripts/               ⚠️  Mixed (utilities + tests)
│   ├── services/          ✅ Service scripts
│   ├── utilities/         ✅ Utility scripts
│   └── [test files]       ❌ Should be in /tests/
├── server/                ✅ BYOC worker implementation
├── tests/                 ✅ Test directory (underutilized)
├── .env files             ✅ Environment configs
├── docker-compose.*.yml   ✅ Docker compositions
└── requirements.*.txt     ✅ Dependencies

```

## Recommended Actions

### 1. Immediate Cleanup (Safe to Remove)
```bash
# Remove Python cache
rm -rf __pycache__/ .pytest_cache/

# Remove backup directories (ensure everything is in git first)
rm -rf backup/ backups/

# Remove empty root-owned directory
sudo rm -rf vtuber-dashboard-v2.html/

# Remove development artifacts
rm -rf implement/
```

### 2. Reorganize Test Files
```bash
# Create proper test structure
mkdir -p tests/integration tests/unit

# Move test files from scripts to tests
mv scripts/test_*.py tests/integration/
mv scripts/*_test.py tests/integration/
mv scripts/continuous_byoc_test.py tests/integration/
```

### 3. Reorganize Scripts
```bash
# Create development utilities folder
mkdir -p scripts/dev

# Move development-only scripts
mv check_system_status.sh scripts/dev/
mv scripts/manual_integration_test.py scripts/dev/
```

### 4. Update .gitignore
Add the following to `.gitignore`:
```
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
*.egg-info/

# Backups
backup/
backups/
*.bak
*.tmp

# Development
implement/
.vscode/
.idea/

# Environment files with secrets
.env.local
.env.production
```

## Security Considerations

### ✅ Good Security Practices Found:
- No exposed private keys or certificates
- Environment files properly use variables
- Secrets are in .env files (should be gitignored)

### ⚠️ Security Recommendations:
1. Ensure `.env` files are in `.gitignore`
2. Use `.env.example` templates without real values
3. Remove any hardcoded credentials from scripts
4. Use secrets management for production

## Production Readiness Checklist

- [ ] Remove all `__pycache__` directories
- [ ] Remove backup directories
- [ ] Move test files to proper location
- [ ] Remove development artifacts
- [ ] Update .gitignore
- [ ] Remove `.env` from git tracking
- [ ] Create `.env.production.example`
- [ ] Document all required environment variables
- [ ] Remove root-owned directories
- [ ] Ensure no test data in production

## Final Repository Structure (After Cleanup)

```
/home/geo/operation/
├── app/                   # Core application
├── autonomy/              # VTuber submodule
├── data/                  # Runtime data
├── docker/                # Docker configs
├── docs/                  # Documentation
├── scripts/
│   ├── services/          # Service scripts
│   ├── utilities/         # Utility scripts
│   └── dev/              # Development tools
├── server/                # BYOC worker
├── tests/
│   ├── unit/             # Unit tests
│   └── integration/       # Integration tests
├── .env.example           # Environment template
├── .gitignore            # Updated ignore file
├── docker-compose.*.yml   # Docker compositions
├── README.md             # Project documentation
└── requirements.*.txt     # Dependencies
```

## Summary

The repository has good overall structure but needs cleanup for production:

**Critical Issues:**
- Test files mixed with production scripts
- Python cache directories not ignored
- Backup directories should be removed
- Root-owned empty directory

**Good Practices:**
- Clear separation of app, scripts, and services
- Proper documentation structure
- Environment configuration templates
- No exposed secrets or credentials

**Estimated Cleanup Time:** 10-15 minutes

After cleanup, the repository will be production-ready with clear separation between development and production assets.