# PGP Keys Directory

## ⚠️ SECURITY NOTICE

**NEVER COMMIT PRIVATE KEYS TO GIT!**

The `.gitignore` is configured to prevent accidental commits of private keys, but always double-check before committing.

## Files in this directory:

### Safe to commit (public):
- `master-public.asc` - Master manager's public PGP key (SAFE TO SHARE)
- `deployment-config.sh` - Helper functions for deployment
- `secure-deploy.sh` - Secure deployment script
- `README.md` - This file

### NEVER commit (private):
- `master-private.asc` - Master manager's private PGP key (KEEP SECURE!)
- Any file ending in `-private.asc`
- Any file containing `private` or `secret` in the name

## Master Key Information

The master PGP key is used to:
1. Sign one-time key (OTK) responses
2. Verify instance registration requests
3. Establish trust with new instances

## Usage

### For Master Manager Setup:
```bash
# Import the private key (only on master server)
gpg --import master-private.asc

# Set environment variable
export MASTER_PGP_PUBLIC_KEY_PATH="/app/keys/master-public.asc"
```

### For Instance Setup:
```bash
# Only need the public key
export MASTER_PGP_PUBLIC_KEY_PATH="/app/keys/master-public.asc"

# Request OTK using deployment script
./secure-deploy.sh
```

### To verify this key:
```bash
# Import and check fingerprint
gpg --import master-public.asc
gpg --fingerprint "Trading Platform Master"
```

## Security Best Practices

1. **Store private keys securely**
   - Use a hardware security module (HSM) in production
   - Or use a secure key management service (AWS KMS, Azure Key Vault, etc.)
   - Never store unencrypted private keys on disk

2. **Rotate keys regularly**
   - Generate new keys every 6-12 months
   - Keep old public keys for verification of historical data

3. **Backup keys safely**
   - Encrypt backups with a separate key
   - Store in multiple secure locations
   - Test recovery procedures

4. **Monitor key usage**
   - Log all key operations
   - Alert on suspicious activity
   - Review logs regularly