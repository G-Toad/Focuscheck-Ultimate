# Complete AI Productivity System Implementation Guide
## Integration with FocusCheck Windows Application

### Table of Contents
1. [System Overview](#1-system-overview)
2. [Architecture Components](#2-architecture-components)
3. [Phase-by-Phase Implementation](#3-phase-by-phase-implementation)
4. [Integration Points](#4-integration-points)
5. [Data Flow Specifications](#5-data-flow-specifications)
6. [API Specifications](#6-api-specifications)
7. [Database Schemas](#7-database-schemas)
8. [AI Learning Pipeline](#8-ai-learning-pipeline)
9. [Testing & Validation](#9-testing-validation)
10. [Deployment Guide](#10-deployment-guide)

---

## 1. System Overview

### 1.1 Project Goal
Transform the existing FocusCheck Windows application into an intelligent AI-powered productivity system that learns user behavior, provides adaptive interventions, and ensures long-term productivity through psychological insights and continuous learning.

### 1.2 Core Components Integration Map

```
┌─────────────────────────────────────────────────────────────┐
│                     EXISTING FOCUSCHECK                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Tkinter UI │  │  SQLite DB   │  │ System Tray │       │
│  │   Prompts   │  │   (tasks.db) │  │  Integration │       │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                  │               │
│         └─────────────────┼──────────────────┘               │
│                           │                                  │
│                    ┌──────▼───────┐                          │
│                    │  WebSocket   │                          │
│                    │   Client     │◄── ADD THIS              │
│                    └──────┬───────┘                          │
└───────────────────────────┼─────────────────────────────────┘
                            │
                 ┌──────────▼───────────┐
                 │   AI BACKEND SYSTEM  │◄── BUILD THIS
                 │  ┌────────────────┐  │
                 │  │  FastAPI Core  │  │
                 │  └────────┬───────┘  │
                 │           │          │
     ┌───────────┼───────────┼──────────┼───────────┐
     │           │           │          │           │
┌────▼────┐ ┌────▼────┐ ┌────▼────┐ ┌──▼───┐ ┌────▼────┐
│ AI Brain│ │Calendar │ │Database │ │Redis │ │Workers  │
│ (GPT-4) │ │Monitor  │ │(Postgres)│ │Cache │ │(Celery) │
└─────────┘ └─────────┘ └──────────┘ └──────┘ └─────────┘
```

### 1.3 Technology Stack

**Existing (FocusCheck)**:
- Python 3.x with Tkinter
- SQLite3 database
- Windows APIs via ctypes
- pystray for system tray

**New Components**:
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15 + existing SQLite
- **Cache/Queue**: Redis 7
- **AI**: OpenAI GPT-4 API
- **Task Queue**: Celery 5.3
- **Containerization**: Docker & Docker Compose
- **Calendar**: Google Calendar API
- **WebSocket**: websockets library

---

## 2. Architecture Components

### 2.1 Component Responsibilities

#### A. FocusCheck Modifications
**Purpose**: Add AI communication capability to existing app

**Required Changes**:
1. Add WebSocket client module
2. Modify prompt_dialog.py to send responses to AI
3. Add intervention receiver for AI messages
4. Extend task_db.py to sync with central database

**New Files to Add**:
```python
# focuscheck/ai_integration/websocket_client.py
import asyncio
import websockets
import json
import threading
from datetime import datetime

class AIWebSocketClient:
    def __init__(self, backend_url="ws://localhost:8000/ws/desktop"):
        self.backend_url = backend_url
        self.websocket = None
        self.connected = False
        self.message_queue = []
        
    async def connect(self):
        """Establish WebSocket connection to AI backend"""
        try:
            self.websocket = await websockets.connect(self.backend_url)
            self.connected = True
            await self.send_queued_messages()
        except Exception as e:
            print(f"Connection failed: {e}")
            
    async def send_prompt_response(self, response_type, response_time, task_info=None):
        """Send user's prompt response to AI"""
        message = {
            "type": "prompt_response",
            "timestamp": datetime.now().isoformat(),
            "response": response_type,  # "working", "wasting_time", "break"
            "response_time": response_time,
            "active_task": task_info,
            "intensity_level": self.get_current_intensity()
        }
        await self.send_message(message)
        
    async def send_message(self, message):
        """Send message to backend"""
        if self.connected:
            await self.websocket.send(json.dumps(message))
        else:
            self.message_queue.append(message)
            
    async def receive_interventions(self):
        """Listen for AI interventions"""
        async for message in self.websocket:
            data = json.loads(message)
            if data["type"] == "intervention":
                self.trigger_intervention(data)
                
    def trigger_intervention(self, intervention):
        """Display AI intervention in FocusCheck UI"""
        # Call existing FocusCheck dialog system with AI message
        pass
```

**Integration Points in Existing Code**:
```python
# Modify app.py - Add to FocusCheckApp.__init__()
self.ai_client = AIWebSocketClient()
self.ai_thread = threading.Thread(target=self.run_ai_client)
self.ai_thread.start()

# Modify prompt_dialog.py - In handle_response()
def handle_response(self, response_type):
    # Existing code...
    
    # ADD: Send to AI
    if hasattr(self.app, 'ai_client'):
        asyncio.run(self.app.ai_client.send_prompt_response(
            response_type=response_type,
            response_time=self.response_time,
            task_info=self.current_task
        ))
```

#### B. AI Backend System
**Purpose**: Central intelligence and coordination

**Core Modules**:

```python
# backend/main.py - FastAPI Application
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize all services on startup
    await init_database()
    app.state.ai_brain = AIBrain()
    app.state.calendar_monitor = CalendarMonitor()
    app.state.pattern_analyzer = PatternAnalyzer()
    
    # Start background tasks
    asyncio.create_task(app.state.calendar_monitor.start())
    asyncio.create_task(app.state.pattern_analyzer.analyze_loop())
    
    yield
    # Cleanup on shutdown

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws/desktop")
async def desktop_websocket(websocket: WebSocket):
    await websocket.accept()
    desktop_handler = DesktopConnectionHandler(websocket, app.state)
    await desktop_handler.handle()
```

#### C. AI Brain Architecture
**Purpose**: Process events and generate intelligent responses

```python
# backend/ai/brain.py
class AIBrain:
    def __init__(self):
        self.memory = UserMemory()
        self.profile = UserProfile()
        self.intervention_engine = InterventionEngine()
        
    async def process_event(self, event):
        # 1. Update memory with new event
        self.memory.add_event(event)
        
        # 2. Analyze pattern
        pattern = self.analyze_pattern(event)
        
        # 3. Update user profile
        self.profile.update(pattern)
        
        # 4. Decide on intervention
        intervention = self.intervention_engine.decide(
            event=event,
            profile=self.profile,
            recent_memory=self.memory.get_recent()
        )
        
        # 5. Learn from result
        if intervention:
            asyncio.create_task(self.track_intervention_effectiveness(intervention))
            
        return intervention
```

#### D. Calendar Monitor
**Purpose**: Track calendar events and trigger on completions

```python
# backend/core/calendar_monitor.py
class CalendarMonitor:
    def __init__(self, ai_brain):
        self.ai_brain = ai_brain
        self.check_interval = 30  # seconds
        self.completed_events = set()
        
    async def monitor_loop(self):
        while True:
            events = await self.fetch_current_events()
            
            for event in events:
                if self.event_just_ended(event):
                    await self.trigger_completion_flow(event)
                    
            await asyncio.sleep(self.check_interval)
            
    async def trigger_completion_flow(self, event):
        # Immediate intervention on event completion
        intervention = await self.ai_brain.process_calendar_completion(event)
        await self.send_to_desktop(intervention)
```

---

## 3. Phase-by-Phase Implementation

### Phase 1: Backend Foundation (Days 1-3)

#### Step 1.1: Project Setup
```bash
# Create directory structure
mkdir productivity-ai-backend
cd productivity-ai-backend
mkdir -p backend/{api,core,ai,integrations}
mkdir -p config
mkdir -p docker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

#### Step 1.2: Install Dependencies
```bash
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
sqlalchemy==2.0.23
asyncpg==0.29.0
psycopg2-binary==2.9.9
redis==5.0.1
celery==5.3.4
openai==1.3.7
google-api-python-client==2.108.0
pydantic==2.5.2
python-dotenv==1.0.0
httpx==0.25.2
```

#### Step 1.3: Database Setup
```python
# backend/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base

DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/productivity_ai"
engine = create_async_engine(DATABASE_URL)
Base = declarative_base()

# backend/core/models.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float
from datetime import datetime

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50))  # 'focuscheck', 'calendar', 'manual'
    event_type = Column(String(100))
    data = Column(JSON)
    user_response = Column(String(50))
    response_time = Column(Float)
    
class Intervention(Base):
    __tablename__ = "interventions"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    trigger_event_id = Column(Integer)
    level = Column(String(20))  # 'gentle', 'firm', 'aggressive', 'nuclear'
    message = Column(String(1000))
    delivered = Column(Boolean, default=False)
    user_responded = Column(Boolean)
    effectiveness = Column(Float)  # 0-1 score
```

#### Step 1.4: Basic WebSocket Handler
```python
# backend/core/desktop_handler.py
class DesktopConnectionHandler:
    def __init__(self, websocket, app_state):
        self.websocket = websocket
        self.ai_brain = app_state.ai_brain
        self.connected = True
        
    async def handle(self):
        try:
            while self.connected:
                message = await self.websocket.receive_json()
                await self.process_message(message)
        except WebSocketDisconnect:
            self.connected = False
            
    async def process_message(self, message):
        event_type = message.get("type")
        
        if event_type == "prompt_response":
            # Process FocusCheck response
            intervention = await self.ai_brain.process_prompt(message)
            if intervention:
                await self.send_intervention(intervention)
                
    async def send_intervention(self, intervention):
        await self.websocket.send_json({
            "type": "intervention",
            "level": intervention.level,
            "message": intervention.message,
            "require_response": intervention.require_response
        })
```

### Phase 2: FocusCheck Integration (Days 4-5)

#### Step 2.1: Modify FocusCheck
**File: focuscheck/ai_integration/__init__.py**
```python
from .websocket_client import AIWebSocketClient
from .intervention_handler import InterventionHandler

__all__ = ['AIWebSocketClient', 'InterventionHandler']
```

**File: focuscheck/ai_integration/intervention_handler.py**
```python
import tkinter as tk
from tkinter import messagebox
import threading

class InterventionHandler:
    def __init__(self, app):
        self.app = app
        
    def handle_intervention(self, intervention_data):
        """Display AI intervention based on level"""
        level = intervention_data.get("level", "gentle")
        message = intervention_data.get("message")
        
        if level == "gentle":
            self.show_gentle_reminder(message)
        elif level == "firm":
            self.show_firm_dialog(message)
        elif level == "aggressive":
            self.show_aggressive_popup(message)
        elif level == "nuclear":
            self.trigger_nuclear_response(message)
            
    def show_gentle_reminder(self, message):
        """Subtle notification in system tray"""
        self.app.system_tray.notify("AI Assistant", message)
        
    def show_firm_dialog(self, message):
        """Modal dialog requiring acknowledgment"""
        dialog = tk.Toplevel()
        dialog.title("Important Message")
        dialog.attributes('-topmost', True)
        # ... dialog implementation
```

#### Step 2.2: Modify app.py
```python
# Add to FocusCheckApp.__init__()
def __init__(self):
    # Existing initialization...
    
    # Add AI integration
    self.ai_client = None
    self.intervention_handler = None
    if self.settings.get('ai_enabled', True):
        self.init_ai_integration()
        
def init_ai_integration(self):
    """Initialize AI backend connection"""
    from ai_integration import AIWebSocketClient, InterventionHandler
    
    backend_url = self.settings.get('ai_backend_url', 'ws://localhost:8000/ws/desktop')
    self.ai_client = AIWebSocketClient(backend_url)
    self.intervention_handler = InterventionHandler(self)
    
    # Start WebSocket connection in background
    self.ai_thread = threading.Thread(target=self.run_ai_client, daemon=True)
    self.ai_thread.start()
```

### Phase 3: AI Intelligence Layer (Days 6-10)

#### Step 3.1: Learning System Implementation
```python
# backend/ai/learning_engine.py
class LearningEngine:
    def __init__(self):
        self.patterns = {}
        self.effectiveness_scores = {}
        
    async def learn_from_interaction(self, event, intervention, outcome):
        """Update learning based on intervention effectiveness"""
        
        # 1. Calculate effectiveness
        effectiveness = self.calculate_effectiveness(outcome)
        
        # 2. Update pattern recognition
        pattern_key = self.extract_pattern_key(event)
        if pattern_key not in self.patterns:
            self.patterns[pattern_key] = []
        self.patterns[pattern_key].append(effectiveness)
        
        # 3. Update intervention effectiveness
        intervention_key = f"{intervention.level}_{event.context}"
        if intervention_key not in self.effectiveness_scores:
            self.effectiveness_scores[intervention_key] = []
        self.effectiveness_scores[intervention_key].append(effectiveness)
        
        # 4. Store in database for persistence
        await self.persist_learning(pattern_key, effectiveness)
```

#### Step 3.2: Pattern Recognition
```python
# backend/ai/pattern_analyzer.py
class PatternAnalyzer:
    def __init__(self, ai_brain):
        self.ai_brain = ai_brain
        
    async def analyze_loop(self):
        """Continuous background pattern analysis"""
        while True:
            # Analyze every 30 minutes
            await asyncio.sleep(1800)
            
            # Get recent events
            events = await self.get_recent_events(hours=24)
            
            # Identify patterns
            patterns = {
                'procrastination_windows': self.find_weak_times(events),
                'trigger_phrases': self.extract_excuses(events),
                'effectiveness_map': self.map_intervention_success(events),
                'prediction_model': self.update_prediction_model(events)
            }
            
            # Update AI brain with patterns
            await self.ai_brain.update_patterns(patterns)
```

### Phase 4: Calendar Integration (Days 11-13)

#### Step 4.1: Google Calendar Setup
```python
# backend/integrations/google_calendar.py
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta

class GoogleCalendarIntegration:
    def __init__(self, user_id):
        self.user_id = user_id
        self.service = None
        
    async def authenticate(self):
        """OAuth2 flow for Google Calendar"""
        creds = await self.load_credentials()
        self.service = build('calendar', 'v3', credentials=creds)
        
    async def get_events(self, time_min=None, time_max=None):
        """Fetch calendar events"""
        if not time_min:
            time_min = datetime.utcnow().isoformat() + 'Z'
        if not time_max:
            time_max = (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'
            
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
```

#### Step 4.2: Event Completion Detection
```python
# backend/core/calendar_monitor.py
class CalendarMonitor:
    def __init__(self, ai_brain):
        self.ai_brain = ai_brain
        self.calendar = GoogleCalendarIntegration()
        self.active_events = {}
        self.check_interval = 30  # seconds
        
    async def monitor_loop(self):
        """Main monitoring loop"""
        await self.calendar.authenticate()
        
        while True:
            current_time = datetime.now()
            events = await self.calendar.get_events()
            
            for event in events:
                event_id = event['id']
                end_time = self.parse_event_time(event.get('end'))
                
                # Check if event just ended
                if end_time and current_time > end_time:
                    if event_id not in self.completed_events:
                        await self.handle_event_completion(event)
                        self.completed_events.add(event_id)
                        
            await asyncio.sleep(self.check_interval)
            
    async def handle_event_completion(self, event):
        """Immediate trigger on event completion"""
        # Create intervention based on event type
        if 'meeting' in event.get('summary', '').lower():
            intervention = {
                'level': 'gentle',
                'message': f"How did {event['summary']} go? Any action items to capture?",
                'require_response': True,
                'context': 'post_meeting'
            }
        else:
            intervention = {
                'level': 'gentle', 
                'message': f"{event['summary']} just ended. Ready for the next task?",
                'require_response': False,
                'context': 'event_transition'
            }
            
        await self.ai_brain.send_intervention(intervention)
```

---

## 4. Integration Points

### 4.1 FocusCheck → AI Backend

**Data Flow**:
1. User responds to FocusCheck prompt
2. Response captured with timing and context
3. WebSocket client sends to backend
4. AI processes and decides on intervention
5. Intervention sent back via WebSocket
6. FocusCheck displays appropriate UI

**Message Format**:
```json
// FocusCheck → Backend
{
    "type": "prompt_response",
    "timestamp": "2024-01-15T14:30:00Z",
    "response": "wasting_time",
    "response_time": 45.2,
    "intensity_level": 2,
    "active_task": {
        "id": 1,
        "title": "Complete project proposal",
        "due_date": "2024-01-16T17:00:00Z"
    },
    "context": {
        "idle_time": 0,
        "active_window": "YouTube - Chrome",
        "previous_response": "working",
        "time_since_last": 3600
    }
}

// Backend → FocusCheck
{
    "type": "intervention",
    "id": "int_12345",
    "level": "firm",
    "message": "You've been on YouTube for 45 minutes. Your project is due tomorrow.",
    "require_response": true,
    "require_evidence": false,
    "options": ["Get back to work", "5 more minutes", "I need help"],
    "timeout": 60,
    "escalation_warning": true
}
```

### 4.2 Calendar → AI Backend

**Trigger Events**:
- Event starts: Pre-event preparation check
- Event ends: Immediate follow-up (T+0 seconds)
- Event cancelled: Check if avoiding commitment
- Event modified: Recalculate intervention strategy

### 4.3 AI Backend → Database

**Storage Strategy**:
- **PostgreSQL**: Long-term patterns, interventions, learning data
- **SQLite (existing)**: Keep for FocusCheck tasks, sync critical data
- **Redis**: Real-time state, temporary patterns, cache

---

## 5. Data Flow Specifications

### 5.1 Real-time Event Processing Pipeline

```
[FocusCheck Prompt] → [User Response] → [WebSocket] → [Event Processor]
                                                             ↓
[Pattern Matcher] ← [Context Builder] ← [Memory Retrieval] ←
        ↓
[AI Decision Engine] → [Intervention Generator] → [Delivery System]
        ↓
[Effectiveness Tracker] → [Learning System] → [Pattern Database]
```

### 5.2 Background Processing Pipeline

```
[Calendar Monitor] ──┐
[Task Monitor] ──────┼→ [Event Queue] → [Pattern Analyzer]
[Time Triggers] ─────┘                          ↓
                                        [Prediction Model]
                                                ↓
                                        [Proactive Interventions]
```

---

## 6. API Specifications

### 6.1 REST Endpoints

```python
# Health & Status
GET  /health                    # System health check
GET  /status                    # Current system status

# Events
POST /api/v1/events             # Log new event
GET  /api/v1/events             # Get event history
GET  /api/v1/events/patterns    # Get detected patterns

# Interventions
POST /api/v1/interventions      # Create intervention
GET  /api/v1/interventions/{id} # Get intervention
PUT  /api/v1/interventions/{id} # Update with response

# Learning
GET  /api/v1/analytics/effectiveness  # Intervention effectiveness
GET  /api/v1/analytics/patterns       # Behavior patterns
GET  /api/v1/analytics/predictions    # Future predictions

# Calendar
GET  /api/v1/calendar/events    # Get calendar events
POST /api/v1/calendar/sync      # Force sync
GET  /api/v1/calendar/auth      # Start OAuth flow

# Configuration
GET  /api/v1/config             # Get current config
PUT  /api/v1/config             # Update configuration
```

### 6.2 WebSocket Protocol

```python
# Connection establishment
ws://localhost:8000/ws/desktop

# Message types
class WebSocketMessage:
    type: str  # 'prompt_response', 'activity_update', 'heartbeat'
    timestamp: datetime
    data: dict

# Bidirectional communication
Desktop → Backend:
    - prompt_response
    - activity_update
    - task_update
    - manual_checkin
    
Backend → Desktop:
    - intervention
    - status_request
    - configuration_update
    - emergency_alert
```

---

## 7. Database Schemas

### 7.1 PostgreSQL Schema (AI Backend)

```sql
-- Core event storage
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    data JSONB,
    processed BOOLEAN DEFAULT FALSE,
    INDEX idx_timestamp (timestamp),
    INDEX idx_event_type (event_type)
);

-- Intervention tracking
CREATE TABLE interventions (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id),
    timestamp TIMESTAMPTZ NOT NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT,
    delivered BOOLEAN DEFAULT FALSE,
    response TEXT,
    response_time FLOAT,
    effectiveness FLOAT,
    INDEX idx_effectiveness (effectiveness)
);

-- Pattern storage
CREATE TABLE patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_data JSONB NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User profile
CREATE TABLE user_profile (
    id SERIAL PRIMARY KEY,
    attribute VARCHAR(100) NOT NULL UNIQUE,
    value JSONB,
    confidence FLOAT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Learning memory
CREATE TABLE memory (
    id SERIAL PRIMARY KEY,
    memory_type VARCHAR(50),
    key VARCHAR(255),
    value JSONB,
    importance FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    accessed_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_key (key),
    INDEX idx_importance (importance DESC)
);
```

### 7.2 Sync with Existing SQLite

```python
# backend/core/sqlite_sync.py
class SQLiteSync:
    def __init__(self, sqlite_path, postgres_engine):
        self.sqlite_conn = sqlite3.connect(sqlite_path)
        self.pg_engine = postgres_engine
        
    async def sync_tasks(self):
        """Sync tasks from FocusCheck SQLite to PostgreSQL"""
        # Pull tasks from SQLite
        tasks = self.sqlite_conn.execute(
            "SELECT * FROM tasks WHERE synced = 0"
        ).fetchall()
        
        # Push to PostgreSQL
        async with self.pg_engine.begin() as conn:
            for task in tasks:
                await conn.execute(
                    "INSERT INTO tasks (...) VALUES (...)"
                )
                
        # Mark as synced in SQLite
        self.sqlite_conn.execute(
            "UPDATE tasks SET synced = 1 WHERE synced = 0"
        )
```

---

## 8. AI Learning Pipeline

### 8.1 Three-Stage Learning Architecture

#### Stage 1: Immediate Learning (Real-time)
```python
class ImmediateLearning:
    """Process each interaction immediately"""
    
    async def process(self, event, intervention, outcome):
        # Update effectiveness score
        effectiveness = self.calculate_effectiveness(outcome)
        
        # Store in fast cache
        await redis.hset(
            f"effectiveness:{intervention.level}",
            f"{event.context}",
            effectiveness
        )
        
        # Update moving average
        await self.update_moving_average(intervention.level, effectiveness)
```

#### Stage 2: Pattern Recognition (Every 30 minutes)
```python
class PatternRecognition:
    """Identify patterns in user behavior"""
    
    async def analyze(self):
        recent_events = await self.get_events(hours=24)
        
        patterns = {
            'temporal': self.find_time_patterns(recent_events),
            'sequential': self.find_sequence_patterns(recent_events),
            'contextual': self.find_context_patterns(recent_events),
            'emotional': self.infer_emotional_patterns(recent_events)
        }
        
        await self.store_patterns(patterns)
        await self.update_prediction_model(patterns)
```

#### Stage 3: Deep Learning (Nightly)
```python
class DeepLearning:
    """Deep analysis and model updates"""
    
    async def nightly_analysis(self):
        # Get all historical data
        all_events = await self.get_all_events()
        
        # Train prediction model
        model = self.train_lstm_model(all_events)
        
        # Update user profile
        profile = self.build_psychological_profile(all_events)
        
        # Generate insights
        insights = self.generate_insights(model, profile)
        
        # Plan next day's strategy
        strategy = self.plan_intervention_strategy(insights)
        
        await self.save_results(model, profile, insights, strategy)
```

### 8.2 Psychological Profiling

```python
class PsychologicalProfile:
    """Build and maintain user psychological profile"""
    
    def __init__(self):
        self.traits = {
            'procrastination_type': None,  # 'avoider', 'thrill_seeker', 'indecisive'
            'motivation_drivers': [],      # 'fear', 'reward', 'competition', 'growth'
            'resistance_patterns': [],     # How they fight the system
            'effective_triggers': [],      # What actually works
            'energy_patterns': {},         # Time of day energy levels
            'stress_indicators': []        # Signs of stress/overwhelm
        }
        
    async def update(self, events):
        # Analyze response patterns
        self.analyze_procrastination_type(events)
        
        # Test motivation theories
        self.test_motivation_drivers(events)
        
        # Map resistance strategies
        self.identify_resistance_patterns(events)
        
        # Track what works
        self.update_effective_triggers(events)
```

### 8.3 Intervention Strategy Evolution

```python
class InterventionStrategy:
    """Evolving intervention strategies based on learning"""
    
    def __init__(self):
        self.strategies = {
            'gentle': GentleStrategy(),
            'firm': FirmStrategy(),
            'aggressive': AggressiveStrategy(),
            'nuclear': NuclearStrategy()
        }
        
    async def select_intervention(self, context, profile):
        # Calculate strategy scores
        scores = {}
        for name, strategy in self.strategies.items():
            scores[name] = strategy.calculate_score(context, profile)
            
        # Select best strategy
        best_strategy = max(scores, key=scores.get)
        
        # Generate intervention
        intervention = self.strategies[best_strategy].generate(context)
        
        # Add personalization
        intervention = self.personalize(intervention, profile)
        
        return intervention
```

---

## 9. Testing & Validation

### 9.1 Integration Testing

```python
# tests/test_integration.py
class TestFocusCheckIntegration:
    async def test_prompt_response_flow(self):
        """Test complete flow from FocusCheck to AI and back"""
        
        # 1. Simulate FocusCheck prompt response
        response = {
            "type": "prompt_response",
            "response": "wasting_time",
            "response_time": 30.5
        }
        
        # 2. Send via WebSocket
        async with websockets.connect('ws://localhost:8000/ws/desktop') as ws:
            await ws.send(json.dumps(response))
            
            # 3. Receive intervention
            intervention = await ws.recv()
            data = json.loads(intervention)
            
            # 4. Validate intervention
            assert data['type'] == 'intervention'
            assert data['level'] in ['gentle', 'firm', 'aggressive']
            assert 'message' in data
```

### 9.2 Learning Validation

```python
class TestLearningSystem:
    async def test_effectiveness_tracking(self):
        """Verify learning system improves over time"""
        
        # Generate test events
        events = self.generate_test_events(days=7)
        
        # Process through learning system
        for event in events:
            intervention = await ai_brain.process_event(event)
            outcome = self.simulate_user_response(intervention)
            await ai_brain.learn(event, intervention, outcome)
            
        # Check improvement
        effectiveness_day1 = await self.get_effectiveness(day=1)
        effectiveness_day7 = await self.get_effectiveness(day=7)
        
        assert effectiveness_day7 > effectiveness_day1
```

### 9.3 Calendar Integration Testing

```python
class TestCalendarIntegration:
    async def test_event_completion_trigger(self):
        """Test immediate trigger on calendar event completion"""
        
        # Create test event ending now
        test_event = {
            'id': 'test_123',
            'summary': 'Test Meeting',
            'end': {'dateTime': datetime.now().isoformat()}
        }
        
        # Process through calendar monitor
        await calendar_monitor.handle_event_completion(test_event)
        
        # Verify intervention was triggered
        interventions = await get_recent_interventions(seconds=5)
        assert len(interventions) > 0
        assert 'Test Meeting' in interventions[0].message
```

---

## 10. Deployment Guide

### 10.1 Development Environment Setup

```bash
# 1. Clone repository
git clone https://github.com/yourusername/productivity-ai
cd productivity-ai

# 2. Set up Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Set up Docker services
docker-compose up -d postgres redis

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Initialize database
python -m alembic upgrade head

# 6. Run backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 7. Run FocusCheck with AI integration
cd ../focuscheck
python main.py --ai-enabled
```

### 10.2 Production Deployment (Local NUC)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    restart: always
    
  redis:
    image: redis:7-alpine
    volumes:
      - ./data/redis:/data
    restart: always
    
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis
    restart: always
    
  worker:
    build: ./backend
    command: celery -A core.celery worker -l info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
    restart: always
    
  scheduler:
    build: ./backend
    command: celery -A core.celery beat -l info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
    restart: always
```

### 10.3 System Service Setup (Windows)

```python
# focuscheck/install_service.py
import win32serviceutil
import win32service
import win32event
import servicemanager

class FocusCheckAIService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'FocusCheckAI'
    _svc_display_name_ = 'FocusCheck AI Productivity System'
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        
    def SvcDoRun(self):
        # Start FocusCheck with AI
        from app import FocusCheckApp
        app = FocusCheckApp(ai_enabled=True)
        app.run()

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(FocusCheckAIService)
```

### 10.4 Monitoring & Maintenance

```python
# backend/monitoring/health.py
class SystemMonitor:
    async def check_health(self):
        health = {
            'database': await self.check_database(),
            'redis': await self.check_redis(),
            'ai_api': await self.check_openai(),
            'calendar': await self.check_google_calendar(),
            'websocket_connections': await self.count_connections(),
            'memory_usage': self.get_memory_usage(),
            'intervention_queue': await self.check_queue_size()
        }
        
        return health
        
    async def alert_if_unhealthy(self, health):
        if not all(health.values()):
            await self.send_alert(health)
```

---

## Configuration Files Reference

### config/settings.yaml
```yaml
# System Configuration
system:
  debug: false
  timezone: "America/Los_Angeles"
  
# AI Configuration
ai:
  model: "gpt-4"
  temperature: 0.7
  max_tokens: 500
  
  intervention_levels:
    gentle:
      enabled: true
      base_delay: 0
      
    firm:
      enabled: true
      base_delay: 5
      
    aggressive:
      enabled: true
      base_delay: 10
      
    nuclear:
      enabled: true
      base_delay: 15
      require_payment: true
      
# Calendar Integration
calendar:
  enabled: true
  check_interval: 30  # seconds
  
  event_triggers:
    meeting_end:
      enabled: true
      immediate: true
      
    deadline_approach:
      enabled: true
      warnings: [1440, 360, 60]  # minutes before
      
# Learning Configuration
learning:
  immediate:
    enabled: true
    
  pattern_analysis:
    enabled: true
    interval: 1800  # 30 minutes
    
  deep_learning:
    enabled: true
    schedule: "02:00"  # 2 AM daily
    
# FocusCheck Integration
focuscheck:
  websocket_reconnect: true
  reconnect_interval: 5  # seconds
  heartbeat_interval: 30  # seconds
```

---

## Complete Development Checklist

### Foundation Phase
- [ ] Set up project structure
- [ ] Install dependencies
- [ ] Configure Docker services
- [ ] Create database schemas
- [ ] Set up environment variables

### Backend Development
- [ ] Create FastAPI application
- [ ] Implement WebSocket handler
- [ ] Build AI Brain class
- [ ] Create intervention system
- [ ] Implement learning pipeline
- [ ] Set up pattern recognition
- [ ] Create calendar monitor

### FocusCheck Integration
- [ ] Add WebSocket client
- [ ] Modify prompt dialog
- [ ] Create intervention handler
- [ ] Update app.py
- [ ] Add settings for AI
- [ ] Test connection

### Calendar Integration
- [ ] Set up Google OAuth
- [ ] Implement calendar client
- [ ] Create event monitor
- [ ] Test completion triggers
- [ ] Handle different event types

### Learning System
- [ ] Implement immediate learning
- [ ] Create pattern analyzer
- [ ] Build psychological profiler
- [ ] Set up effectiveness tracking
- [ ] Create prediction model

### Testing
- [ ] Unit tests for AI Brain
- [ ] Integration tests for WebSocket
- [ ] Calendar trigger tests
- [ ] Learning improvement tests
- [ ] End-to-end flow tests

### Deployment
- [ ] Docker compose setup
- [ ] Production configuration
- [ ] Service installation
- [ ] Monitoring setup
- [ ] Documentation

### Optimization
- [ ] Performance profiling
- [ ] Database indexing
- [ ] Caching strategy
- [ ] Error handling
- [ ] Logging system

---

## Critical Success Factors

1. **Immediate Calendar Triggers**: Events must trigger within seconds of completion
2. **Reliable WebSocket**: Connection must auto-reconnect on failure
3. **Learning Persistence**: All learning must survive restarts
4. **Flexible Configuration**: All timings/behaviors adjustable without code changes
5. **Graceful Degradation**: System continues working if AI API fails
6. **Privacy First**: All data stored locally, only AI API calls go external

---

## Troubleshooting Guide

### Common Issues and Solutions

**FocusCheck won't connect to backend**:
- Check firewall settings
- Verify backend is running: `curl http://localhost:8000/health`
- Check WebSocket URL in settings.json

**Calendar events not triggering**:
- Verify Google OAuth credentials
- Check calendar permissions
- Review calendar_monitor logs

**AI not learning/improving**:
- Check PostgreSQL is persisting data
- Verify learning pipeline is running
- Review effectiveness scores in database

**Interventions not showing**:
- Check FocusCheck intervention handler
- Verify WebSocket message format
- Check intervention level settings

---

## Next Steps After Implementation

1. **Week 1-2**: Get basic loop working (FocusCheck ↔ AI)
2. **Week 3-4**: Add calendar integration and triggers
3. **Month 2**: Refine learning based on real data
4. **Month 3**: Add advanced features (opportunity hunting, progress tracking)
5. **Ongoing**: Continuously tune based on effectiveness metrics

This guide provides everything needed to build the complete system. Each component is specified with enough detail for implementation while maintaining flexibility for adjustments based on real-world testing.