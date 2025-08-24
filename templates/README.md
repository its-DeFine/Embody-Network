# Environment Templates

This folder contains all environment configuration templates for the Embody Network system.

## 📁 Template Files

### For Orchestrators (Running Full VTuber System)

#### **`FULL-AUTONOMY.env.template`** ⭐ THE ONLY TEMPLATE YOU NEED
- **Purpose**: Complete VTuber autonomy system with BYOC orchestrator
- **Use Case**: ALL orchestrators run the full VTuber AI system
- **Includes**: All VTuber services + Livepeer orchestrator + Manager registration + Auto-updates
- **Usage**: Copy to `autonomy/.env` and fill in TODO sections

### For System Administrators Only

#### `manager.env.template`
- **Purpose**: Central manager service (infrastructure component)
- **Use Case**: Only for running the central manager (not for orchestrators)

### Example Configuration

#### `example-frank-full.env`
- Complete example configuration showing all values filled in
- Use as reference when filling out FULL-AUTONOMY.env.template

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

## 📝 Important Notes for Orchestrators

- **ONE TEMPLATE ONLY**: Use `FULL-AUTONOMY.env.template` for everything
- **Full System**: Every orchestrator runs the complete VTuber + BYOC system
- **No Standalone Option**: There is no orchestrator-only setup
- **Auto-Updates**: Watchtower included for automatic updates

## 📞 Support

For help with configuration, contact the Embody Network team.