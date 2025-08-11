# Versioning Guide

## Overview

The VTuber Autonomy Platform uses **Semantic Versioning 2.0.0** with automated CI/CD integration for version management.

## Version Format

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

Example: `0.1.0`, `1.2.3-beta.1`, `2.0.0-rc.1+build.123`

## Version Bumping Rules

The system automatically bumps versions based on **Conventional Commits**:

| Commit Type | Version Bump | Example |
|------------|--------------|---------|
| `feat:` | Minor (0.X.0) | `feat: add new agent type` |
| `fix:` | Patch (0.0.X) | `fix: resolve connection issue` |
| `BREAKING CHANGE:` | Major (X.0.0) | `feat!: new API structure` |
| `docs:`, `style:`, `refactor:` | Patch | `docs: update README` |
| `chore:`, `test:` | Patch | `chore: update dependencies` |

## Implementation Details

### Version File
- **Location**: `/VERSION`
- **Format**: Plain text containing semantic version
- **Example**: `0.1.0`

### Dynamic Version Module
- **Location**: `/app/_version.py`
- **Features**:
  - Reads from VERSION file at runtime
  - Falls back to environment variable `APP_VERSION`
  - Provides structured version information

### API Endpoints

#### Version Information
```http
GET /api/v1/version
```

Returns:
```json
{
  "version": "0.1.0",
  "major": 0,
  "minor": 1,
  "patch": 0,
  "prerelease": null,
  "build": null
}
```

#### Health Check with Version
```http
GET /health
```

Returns:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-11T10:30:00Z",
  "version": "0.1.0"
}
```

## CI/CD Workflows

### Automatic Version Bump
**File**: `.github/workflows/version-bump.yml`

**Triggers**: Push to main branches
- Reads commit messages
- Determines version bump type
- Updates VERSION file
- Creates git tag
- Commits changes with `[skip ci]`

### Release Creation
**File**: `.github/workflows/release.yml`

**Triggers**: Push of version tags (v*)
- Generates changelog from commits
- Creates GitHub release
- Builds and tags Docker images
- Publishes to container registry

## Manual Version Management

### Checking Current Version
```bash
# From file
cat VERSION

# From API
curl http://localhost:8010/api/v1/version

# From Python
python -c "from app._version import __version__; print(__version__)"
```

### Manual Version Bump
```bash
# Edit VERSION file
echo "0.2.0" > VERSION

# Commit with conventional message
git add VERSION
git commit -m "chore: bump version to 0.2.0"

# Create tag
git tag v0.2.0
git push origin v0.2.0
```

## Docker Image Versioning

Docker images are automatically tagged with:
- Semantic version: `vtuber-manager:0.1.0`
- Latest tag: `vtuber-manager:latest`
- Major.minor tag: `vtuber-manager:0.1`

## Best Practices

1. **Use Conventional Commits**
   - Start commit messages with type: `feat:`, `fix:`, `docs:`, etc.
   - Include scope when relevant: `feat(api): add new endpoint`
   - Mark breaking changes: `feat!:` or include `BREAKING CHANGE:` in body

2. **Version Bump Strategy**
   - Features → Minor version
   - Bug fixes → Patch version
   - Breaking changes → Major version
   - Documentation/style → Patch version

3. **Pre-release Versions**
   - Use for beta/RC releases: `1.0.0-beta.1`
   - Test in staging before production release

4. **Release Notes**
   - Automatically generated from commit messages
   - Group by type (Features, Fixes, etc.)
   - Include breaking changes prominently

## Troubleshooting

### Version Not Updating
- Check GitHub Actions workflow status
- Ensure commits follow conventional format
- Verify VERSION file permissions

### Docker Image Tags
- Images tagged on release creation
- Check GitHub Container Registry for available versions
- Use specific versions in production, not `latest`

### API Version Mismatch
- Restart application after VERSION file update
- Check `_version.py` can read VERSION file
- Verify environment variable `APP_VERSION` if set

## Migration from Manual Versioning

If migrating from manual version management:

1. Create VERSION file with current version
2. Update `app/config.py` to use `get_version()`
3. Add version endpoints to API
4. Configure GitHub workflows
5. Start using conventional commits

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)