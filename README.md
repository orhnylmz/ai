# Multi-Agent AI Orchestration System

Ortak bir orkestratör tarafından koordine edilen, planning (analiz), coding ve test süreçlerini yönetecek birden fazla agent sistemi.

## 🏗️ Mimari (Architecture)

```
orchestrator/              # Merkezi orkestratör
  ├── orchestrator.py      # Ana koordinasyon motoru
  ├── state.py             # Ortak durum yönetimi
  └── config.py            # Konfigürasyon

agents/                    # Agent'lar (gelecek)
  ├── planner/             # Analiz agent'ı
  ├── developer/           # Coding agent'ı
  └── tester/              # Test agent'ı

tools/                     # Ortak araçlar (gelecek)
  ├── code_tools.py        # Kod yazma/analiz
  ├── test_tools.py        # Test çalıştırma
  └── git_tools.py         # Git operasyonları

workflows/                 # İş akışları (gelecek)
  ├── standard_flow.py     # Standart iş akışı
  └── custom_flows.py      # Özel iş akışları

tests/                     # Test'ler
  └── test_orchestration.py
```

## 📋 Core Components

### 1. **Orchestrator**
Tüm agent'ları koordine eden merkezi motor. Özellikleri:
- Sequential, Parallel, Hybrid execution modes
- Retry logic ile error handling
- State management ve checkpointing
- Callbacks ve monitoring
- Rollback desteği

### 2. **OrchestrationState**
Agent'lar arasında veri paylaşımı sağlayan ortak state. İçerir:
- `shared_context`: Tüm agent'lar tarafından erişilebilir veriler
- `agent_outputs`: Her agent'ın çıktısı
- `execution_logs`: Tüm işlemlerin logu
- `checkpoint_history`: Rollback için checkpoint'ler

### 3. **OrchestratorConfig**
Orkestratörün davranışını kontrol eden konfigürasyon:
- Execution mode (sequential/parallel/hybrid)
- Retry policy
- Logging ve metrics
- State persistence

## 🚀 Quick Start

```python
import asyncio
from orchestrator import Orchestrator, Agent
from orchestrator.config import OrchestratorConfig, ExecutionMode
from orchestrator.state import OrchestrationState

# Custom agent örneği
class PlannerAgent(Agent):
    async def execute(self, state: OrchestrationState):
        # Analiz ve planlama lojik
        return {"plan": "Feature X implementation plan"}

class DeveloperAgent(Agent):
    async def execute(self, state: OrchestrationState):
        plan = state.get_agent_output("planner")
        # Kodlama lojik
        return {"code": "Implementation code"}

class TesterAgent(Agent):
    async def execute(self, state: OrchestrationState):
        code = state.get_agent_output("developer")
        # Test lojik
        return {"tests_passed": True}

# Setup
config = OrchestratorConfig(mode=ExecutionMode.SEQUENTIAL)
orchestrator = Orchestrator(config)

# Register agents
orchestrator.register_agents([
    PlannerAgent("planner"),
    DeveloperAgent("developer"),
    TesterAgent("tester"),
])

# Set workflow
orchestrator.set_workflow(["planner", "developer", "tester"])

# Execute
state = await orchestrator.execute()
print(state.get_summary())
```

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=orchestrator
```

## 📊 Workflow Examples

### Sequential Execution (Sırayla)
```
Planner → Developer → Tester
```
Her agent'ın önceki agent'ın çıktısına bağlı olduğu durumlar.

### Parallel Execution (Paralel)
```
Planner ──┐
          ├─→ Aggregator
Developer ┤
          ├─→
Tester ───┘
```
Bağımsız agent'ların aynı anda çalışması.

## 🔄 Features

✅ **State Management**: Ortak state üzerinden veri paylaşımı
✅ **Error Handling**: Configurable retry logic
✅ **Checkpointing**: State snapshot'ları ve rollback
✅ **Callbacks**: Event-driven monitoring
✅ **Logging**: Detailed execution logs
✅ **Async/Await**: Asynchronous agent execution
✅ **Flexible Execution**: Sequential, Parallel, Hybrid modes

## 📝 Next Steps

- [ ] Agent implementations (Planner, Developer, Tester)
- [ ] Tools layer (code analysis, testing, git operations)
- [ ] Workflow templates (standard flows)
- [ ] Advanced state persistence
- [ ] Distributed execution support
- [ ] Web dashboard/monitoring

## 📚 Documentation

Değişik açıklamalar ve dokümantasyon ilerleyen geliştirmelerle eklenecektir.
