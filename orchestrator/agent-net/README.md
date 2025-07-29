# Agent-Net: GPU Check Pipeline (BYOC-Ready)

Agent-Net is a Bring-Your-Own-Container (BYOC) pipeline that exposes a **GPU health & model-listing capability** to upstream orchestrators. It deploys an Ollama LLM container (with GPU support) and a lightweight Python worker that answers GPU-state queries.

---

## 1. What You Get

* 🔍 **Real-time GPU health** – vRAM usage, temperature, and power draw reported straight from the Ollama server.
* 📜 **Model catalogue** – list all models currently pulled into Ollama.
* ⚡ **Self-contained BYOC image** – easy to run anywhere Docker & NVIDIA GPUs are available.
* 🪙 **Ticket-based payments** – conforms to Livepeer probabilistic micropayment (PM) flow (details below).

---

## 2. Prerequisites

* Docker _(tested with ≥ 24.x)_
* NVIDIA driver + `nvidia-container-runtime`
* A GPU supported by Ollama (Ampere or newer recommended)

---

## 3. Deploy in 3 Commands

```bash
# 1) Go to project root
cd agent-net

# 2) Build without cache to make sure the latest base images are used
DOCKER_BUILDKIT=1 docker compose build --no-cache

# 3) Start the stack
docker compose up -d
```

The first start pulls the **CodeLlama-34B-Instruct Q4_K_M** model (~14GB). Subsequent starts are instant because the model is cached in the `ollama_data` volume.

---

## 4. Capability Endpoints

The worker exposes **one primary route** (and an alias):

```
POST /gpu-check   → returns GPU / model information
POST /agent-net   → alias that internally calls /gpu-check
```

Send a JSON body – the only required key is `agent_id` (string). Example request:
Note: agent_id can be arbitrary at this point

```bash
curl -X POST http://localhost:9876/gpu-check \
     -H "Content-Type: application/json" \
     -d '{"agent_id": "demo-agent"}'
```

Example response:
```jsonc
{
  "status": "success",
  "agent_id": "demo-agent",
  "model_name": "codellama:34b-instruct-q4_k_m",
  "vram_usage_mb": 6321,
  "total_models": 1,
  "timestamp": 1719345600.123,
  "gpu_count": 1
}
```

---

## 5. Registering with an Orchestrator

At container start-up the worker calls `/capability/register` on the orchestrator with JSON similar to:

```jsonc
{
  "url": "http://worker:9876",          // where jobs are sent
  "name": "<Orchid>",   // unique per orchestrator (see Section 7)
  "description": "GPU uptime monitoring (BYOC)",
  "capacity": 10                         // parallel jobs supported
}
```

> **No `price_per_unit` field** – payment is fully determined by the ticket parameters selected by the orchestrator (see next section).

---

## 6. Payment Mechanics (Probabilistic Tickets)

Agent-Net follows the Livepeer PM spec: every request includes a *probabilistic ticket* with two on-chain fields:

* **`faceValue`** – the ETH amount cashed-out when the ticket wins.
* **`winProb`**   – 256-bit fixed-point probability that the ticket wins.

The orchestrator chooses these numbers when it starts; the worker is passive and simply submits winning tickets for redemption.

### 6.1  Relationship between Variables

Let:
* **`ticketEV`**  – desired expected value per job (*set by orchestrator and capped from Gateway*)
* **`faceValue`** – total ticket value(0.001 ETH recommended)

Then:

```
winProb = ticketEV / faceValue   (0 < winProb ≤ 1)
```

### 6.2  Worked Example

Suppose the orchestrator is willing to pay **18 gwei** per job and selects **faceValue = 180 gwei** so that on average only 1 in 10 tickets is a winner.

| Parameter   | Value  |
|-------------|--------|
| `faceValue` | 180 gwei |
| `ticketEV`  | 18 gwei  |
| `winProb`   | 0.1      |

The expected cost per call is exactly `ticketEV` (18 gwei). Increasing `faceValue` while keeping `ticketEV` constant reduces on-chain fees (fewer winning tickets) at the expense of higher variance.

### 6.3  Orchestrator Flag Cheat-Sheet

Set these flags (or env vars) on the **orchestrator** container:

| Flag / Env Var | Example Value | Purpose |
|---------------|--------------|---------|
| `CAPABILITY_PRICE_PER_UNIT` | `29000000000000` | Advertised price per unit (Wei) when registering capability |
| `-pricePerUnit` | `100000000000000` | Legacy per-unit price broadcast to gateways (still required) |
| `-ticketEV` | `29000000000000` | Expected value of each probabilistic ticket (Wei) |
| `-maxFaceValue` | `1000000000000000` | Upper bound for `faceValue` sent to workers |
| `-autoAdjustPrice` | `false` | Disable automatic price tuning (we want deterministic pricing) |
| `-maxGasPrice` | `1000000000` | Gas-price ceiling (Wei) used when redeeming winning tickets |

> Hint  Ensure the numeric literals have **no quotes** inside command-line flags. All numbers are interpreted in decimal Wei.

### 6.4  Gateway Limit Flags (from `docker-compose-gateway.yml`)

| Flag | Value | Meaning |
|------|-------|---------|
| `-maxTicketEV` | `300000000000000` | Reject tickets with EV above this amount |
| `-maxTotalEV` | `300000000000000` | Aggregate EV ceiling over multiple tickets received together |
| `-maxFaceValue` | `1000000000000000` | Same cap as orchestrator – must be **≥** orchestrator value |
| `-maxPricePerUnit` | `130000000000000` | Reject workers priced above this amount (set comfortably above orchestrator price) |

### 6.5  Orchestrator vs Gateway – Quick Consistency Check

| Parameter | Orchestrator | Gateway | ✅ OK / ❌ Mismatch |
|-----------|--------------|---------|-------------------|
| `pricePerUnit` / `maxPricePerUnit` | `100 000 000 000 000` | `130 000 000 000 000` | ✅ within limit |
| `ticketEV` / `maxTicketEV` | `29 000 000 000 000` | `300 000 000 000 000` | ✅ within limit |
| `faceValue` / `maxFaceValue` | `1 000 000 000 000 000` | `1 000 000 000 000 000` | ✅ equal |
When all orchestrator settings sit comfortably below the gateway ceilings – jobs will be accepted without further tuning. 


---

## 7. Direct Job Allocation (BYOC Bypass)

While BYOC load-balancing is under active development, each orchestrator currently registers **its own capability name** – e.g. `agent-net-nyc` or `agent-net-tokyo`. Gateways target the desired orchestrator directly by capability name, cleanly bypassing any limitations in the generic BYOC matcher.

---

## 8. Roadmap

* Launch of initial agent logic (v0.2.0 of Unreal Vtuber https://github.com/its-DeFine/Unreal_Vtuber)
* Multiple agents per Orchestrator
* Embodied agents
* TBA


---

*Last updated: 2025-06-26*  
Maintainer: DeFine