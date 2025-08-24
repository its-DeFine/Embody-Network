# Environment Templates

This folder contains all environment configuration templates for the Embody Network system.

## 📁 Template Files

### For Orchestrators (Running Full VTuber System)

#### **`FULL-AUTONOMY.env.template`** ⭐ RECOMMENDED
- **Purpose**: Complete VTuber autonomy system with BYOC orchestrator
- **Use Case**: External orchestrators wanting to run the full VTuber AI system
- **Includes**: All VTuber services + Livepeer orchestrator + Manager registration
- **Usage**: Copy to `autonomy/.env` and fill in TODO sections

### For Standalone Components

#### `orchestrator-only.env.template`
- **Purpose**: Standalone orchestrator node (no VTuber system)
- **Use Case**: Lightweight compute nodes that only process jobs
- **Note**: Most users should use FULL-AUTONOMY instead

#### `manager.env.template`
- **Purpose**: Central manager service
- **Use Case**: Running your own manager (not needed for most users)

### Examples

#### `example-frank-full.env`
- Complete example configuration for a full autonomy system
- Shows all values filled in

## 🚀 Quick Start for New Orchestrators

1. **Get the template**:
   ```bash
   cp templates/FULL-AUTONOMY.env.template autonomy/.env
   ```

2. **Edit the file** and fill in:
   - `ORCHESTRATOR_ID` - Your unique identifier
   - `ORCHESTRATOR_NAME` - Your display name
   - `ORCHESTRATOR_SECRET` - Generate a 32+ char secret
   - `ETH_ADDRESS` - Your Ethereum address
   - API keys (optional but recommended)

3. **Launch the system**:
   ```bash
   cd autonomy
   docker compose up -d
   ```

4. **Run the game** on your Windows host

## 📝 Important Notes

- The manager URL and API key are pre-configured for the Embody Network
- All pricing is set to 0 during the testing phase
- The system auto-registers with the manager on startup
- Game runs on Windows, VTuber system runs in Docker

## 🗑️ Deprecated Files

The following files have been consolidated into the templates above:
- `.env.autonomy-template` → Use `FULL-AUTONOMY.env.template`
- `.env.orchestrator-template` → Use `FULL-AUTONOMY.env.template`
- Individual `.env.*-frank` files → See examples folder

## 📞 Support

For help with configuration, contact the Embody Network team.