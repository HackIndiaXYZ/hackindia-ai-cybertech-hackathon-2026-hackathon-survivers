🏙️ FixMyCity AI

An AI-agent platform that turns civic complaints into verified, prioritized, correctly routed, and trackable resolutions.

FixMyCity AI is a multi-agent civic issue management platform for problems such as potholes, garbage, broken streetlights, water leakage, and drainage issues.

Instead of stopping at complaint registration, the system is designed to follow the complete lifecycle:

Report → Understand → Verify → Prioritize → Route → Track → Resolve → Verify → Learn

📌 Table of Contents

Problem Statement

Solution

Core Objectives

Supported Issues

End-to-End Workflow

Multi-Agent Architecture

Computer Vision Pipeline

Severity and Priority

Duplicate Detection

Before/After Verification

Voice and OCR

Department Routing

System Architecture

Data Flow

Technology Stack

ML Plan

Dataset Strategy

API Contract

Database Design

Project Structure

Team Roles

Development Roadmap

Evaluation

Hackathon Demo

Security and Reliability

Current Status

Future Scope

Setup

Hackathon

Problem Statement

Civic complaints are often misclassified, delayed, routed to the wrong department, duplicated, and difficult for citizens to track until resolution.

A normal complaint system may create a ticket, but registration alone does not guarantee correct classification, correct routing, timely prioritization, or verified repair.

Existing flow

Citizen Report
      ↓
Manual Classification
      ↓
Manual Routing
      ↓
Delayed Action
      ↓
Unclear Status
      ↓
Unverified Resolution

FixMyCity AI flow

Citizen Report
      ↓
AI Understanding
      ↓
Verification
      ↓
Duplicate Detection
      ↓
Severity + Priority
      ↓
Department Routing
      ↓
Tracking
      ↓
Repair
      ↓
AI Resolution Verification
      ↓
City-Level Intelligence

Solution

FixMyCity AI combines multi-agent AI, computer vision, geospatial information, image similarity, and structured complaint management.

A citizen can submit:

📸 Image

📝 Text description

📍 Location

🎙️ Optional voice description

The platform determines:

What is the civic issue?

Is the evidence valid?

Is it a duplicate of an existing report?

How severe is it?

How urgent is it?

Which department should handle it?

Has the issue actually been resolved?

Core Objectives

Automate civic issue classification

Reduce wrong department routing

Detect duplicate complaints

Estimate issue severity

Prioritize high-risk complaints

Track complaints from report to resolution

Verify repair completion using visual evidence

Identify recurring civic issue hotspots

Give authorities actionable city-level insights

Supported Issues

Initial unified ML classes:

pothole
garbage
streetlight
water_leakage
drainage

An other fallback can be used when the model does not confidently match a supported class. It does not need to be a trained class in the initial detector.

End-to-End Workflow

flowchart LR
    A[Citizen Report] --> B[Input Processing]
    B --> C[Classification Agent]
    C --> D[Verification Agent]
    D --> E[Duplicate Detection]
    E --> F[Severity & Priority]
    F --> G[Department Routing]
    G --> H[Complaint Tracking]
    H --> I[Field Resolution]
    I --> J[After-Repair Evidence]
    J --> K[Resolution Verification]
    K --> L[Close or Reopen]
    L --> M[Civic Intelligence]

Lifecycle

Stage

Purpose

Report

Citizen submits issue

Understand

Extract issue and context

Verify

Check evidence and consistency

Detect Duplicate

Find related reports

Prioritize

Estimate urgency and impact

Route

Select responsible department

Track

Monitor progress

Resolve

Field team performs repair

Verify

Compare repair evidence

Learn

Identify recurring city problems

Multi-Agent Architecture

flowchart TB
    U[Citizen] --> I[Input Layer]
    I --> C[Classification Agent]
    C --> V[Verification Agent]
    V --> D[Duplicate Detection]
    D --> P[Priority Agent]
    P --> R[Department Routing Agent]
    R --> DB[(Complaint Database)]
    DB --> F[Field Team]
    F --> RV[Resolution Verification Agent]
    RV --> DB
    DB --> CI[Civic Intelligence Agent]
    CI --> AD[Authority Dashboard]

1. Classification Agent

Identifies:

Issue category

Model confidence

Detected regions/bounding boxes

Supporting evidence

2. Verification Agent

Checks:

Evidence quality

Missing information

Location consistency

Suspicious reports

Duplicate likelihood

3. Duplicate Detection

Compares new complaints with previous reports using image similarity, location and category.

4. Priority Agent

Combines severity, safety risk, public impact, recurrence and related reports.

5. Department Routing Agent

Maps the verified issue to the responsible department.

6. Resolution Verification Agent

Compares the original problem with field repair evidence.

7. Civic Intelligence Agent

Finds hotspots, recurring issues, workload patterns and infrastructure trends.

Computer Vision Pipeline

flowchart LR
    A[Input Image] --> B[Preprocessing]
    B --> C[YOLO Detector]
    C --> D[Class + Confidence + Boxes]
    D --> E[Severity]
    D --> F[Image Embedding]
    F --> G[Similarity Search]
    G --> H[Duplicate / Related Report]

Initial model classes

0: pothole
1: garbage
2: streetlight
3: water_leakage
4: drainage

The initial ML plan uses a lightweight YOLO detector. Final model choice, weights and performance numbers will be reported only after training and validation.

Severity and Priority

Severity can initially be estimated using a rules/context layer instead of training a separate severity model.

Potential signals:

Detected object size

Number of affected regions

Safety risk

Road/location importance

Number of related complaints

Recurrence

Public impact

Conceptual scoring:

Visual Severity
      +
Safety Risk
      +
Public Impact
      +
Recurrence
      +
Related Reports
      ↓
Priority Score
      ↓
LOW / MEDIUM / HIGH

No fixed threshold is treated as final until it is validated with project data.

Duplicate Detection

Multiple citizens can report the same physical issue.

Report A ─┐
Report B ─┼──> Same location / similar image
Report C ─┘
              ↓
        Related Civic Issue

Proposed approach

Image Embedding
      +
Cosine Similarity
      +
GPS Distance
      +
Issue Category
      ↓
Duplicate / Related Probability

Candidate embedding approaches include CLIP or DINOv2. Final thresholds should be selected from validation data.

Before/After Verification

A major differentiator is verifying whether a reported repair actually appears complete.

flowchart LR
    A[Before Image] --> C[Visual Comparison]
    B[After Image] --> C
    C --> D{Issue Still Detected?}
    D -->|Yes| E[Recheck / Reopen]
    D -->|No| F[Likely Resolved]
    F --> G[Update Complaint]

The system can compare:

Original detection

After-image detection

Image similarity

Location consistency

Resolution confidence

Voice and OCR

Voice

Citizen speaks
      ↓
Speech-to-Text
      ↓
Complaint Text
      ↓
Agent Workflow

Potential technology: Whisper.

OCR

Image
 ↓
OCR
 ↓
Extracted Text
 ↓
Agent Reasoning

Potential technology: PaddleOCR / Tesseract.

These are secondary features after the core CV pipeline is stable.

Department Routing

flowchart TD
    A[Verified Complaint] --> B{Issue Type}
    B -->|Pothole| C[Roads / Public Works]
    B -->|Garbage| D[Sanitation]
    B -->|Streetlight| E[Electrical]
    B -->|Water Leakage| F[Water Supply]
    B -->|Drainage| G[Drainage / Public Works]
    B -->|Unknown| H[Manual Review]

Final department names can be configured for the target city.

System Architecture

flowchart TB
    subgraph Frontend
        CU[Citizen UI]
        AU[Authority Dashboard]
        FU[Field Worker UI]
    end

    subgraph Backend
        API[FastAPI]
        CS[Complaint Service]
        GS[Geospatial Service]
    end

    subgraph AI
        LG[LangGraph]
        LLM[LLM]
        CV[YOLO / CV]
        EMB[Image Embeddings]
        OCR[OCR / Speech]
    end

    subgraph Storage
        PG[(PostgreSQL + PostGIS)]
        CH[(ChromaDB)]
        FS[(Image Storage)]
        RD[(Redis)]
    end

    CU --> API
    AU --> API
    FU --> API
    API --> CS
    API --> GS
    API --> LG
    LG --> LLM
    LG --> CV
    LG --> EMB
    LG --> OCR
    CS --> PG
    GS --> PG
    EMB --> CH
    API --> FS
    API --> RD

Data Flow

sequenceDiagram
    participant C as Citizen
    participant API as FastAPI
    participant CV as CV Model
    participant AG as AI Agents
    participant DB as Database
    participant F as Field Team

    C->>API: Submit image + text + location
    API->>CV: Analyze image
    CV-->>API: Class + confidence + boxes
    API->>AG: Start complaint workflow
    AG->>DB: Search related complaints
    DB-->>AG: Similar reports
    AG->>DB: Save priority + department
    DB-->>C: Complaint status
    F->>API: Upload repair evidence
    API->>AG: Verify resolution
    AG->>DB: Close or reopen complaint

Technology Stack

Layer

Technology

Frontend

React / Next.js

UI

Tailwind CSS

Backend

FastAPI

Agent orchestration

LangGraph

LLM

Gemini / OpenAI-compatible LLM

Computer Vision

YOLO / Ultralytics

Image processing

OpenCV, Pillow

Embeddings

CLIP / DINOv2 or compatible model

OCR

PaddleOCR / Tesseract

Speech

Whisper

Database

PostgreSQL

Geospatial

PostGIS

Vector DB

ChromaDB / FAISS

Cache

Redis

Maps

Leaflet / OpenStreetMap / Mapbox

ML development

Google Colab

Containerization

Docker

Version control

Git + GitHub

ML Plan

Issue detector

Input: civic issue image

Output:

{
  "category": "pothole",
  "confidence": 0.94,
  "boxes": []
}

Severity module

def estimate_severity(detections, image_size):
    return {
        "level": "high",
        "score": 0.87
    }

Image embedding

def embed_image(image):
    return [0.12, 0.03, 0.91]

Repair verification

def verify_repair(before, after):
    return {
        "resolved": True,
        "confidence": 0.91
    }

These examples describe the intended interface; actual model outputs will be produced by the implementation.

Dataset Strategy

Potential sources:

Roboflow Universe

Kaggle

Public civic datasets

Custom images where permitted

Dataset pipeline

flowchart LR
    A[Dataset 1] --> D[Merge]
    B[Dataset 2] --> D
    C[Dataset 3] --> D
    D --> E[Class Remapping]
    E --> F[Quality Checks]
    F --> G[Train / Val / Test]
    G --> H[YOLO Training]

Quality checks

Class balance

Duplicate images

Missing labels

Invalid bounding boxes

Wrong class mappings

Data leakage

Annotation quality

Image resolution

Large datasets, model weights, runs and generated artifacts should remain outside Git tracking.

Database Design

Conceptual complaint entity:

Complaint
├── complaint_id
├── citizen_id
├── issue_category
├── description
├── latitude
├── longitude
├── image_url
├── confidence
├── severity
├── priority
├── department
├── status
├── created_at
├── updated_at
└── resolution_evidence

Complaint state machine

stateDiagram-v2
    [*] --> Reported
    Reported --> Verifying
    Verifying --> Verified
    Verifying --> Rejected
    Verified --> Prioritized
    Prioritized --> Routed
    Routed --> InProgress
    InProgress --> Resolved
    Resolved --> ResolutionVerification
    ResolutionVerification --> Closed
    ResolutionVerification --> Reopened
    Reopened --> InProgress
    Closed --> [*]

API Contract

The ML layer should expose predictable outputs for backend/agent integration.

Classification

def classify_issue(image):
    return {"category": str, "confidence": float, "boxes": list}

Severity

def estimate_severity(detections, image_size):
    return {"level": str, "score": float}

Embedding

def embed_image(image):
    return list[float]

Repair verification

def verify_repair(before, after):
    return {"resolved": bool, "confidence": float}

Project Structure

Current

FixMyCity/
├── ml/
│   ├── README.md
│   ├── configs/
│   │   └── classes.yaml
│   ├── notebooks/
│   └── src/
│       └── merge_datasets.py
├── .gitignore
├── requirements.txt
├── LICENSE
└── README.md

Planned expansion

FixMyCity/
├── frontend/
├── backend/
│   ├── api/
│   ├── services/
│   ├── models/
│   └── schemas/
├── agents/
│   ├── classification/
│   ├── verification/
│   ├── priority/
│   ├── routing/
│   ├── resolution/
│   └── intelligence/
├── ml/
│   ├── configs/
│   ├── notebooks/
│   ├── src/
│   ├── data/       # ignored
│   ├── models/     # ignored
│   └── runs/       # ignored
├── tests/
├── docker/
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md

Team Roles

Member 1 — AI/ML & Computer Vision

Dataset preparation

YOLO training

Issue detection

Model evaluation

Severity estimation

Duplicate image detection

Before/after verification

ML inference integration

Member 2 — AI Agents / LLM / RAG

LangGraph workflow

Agent design

LLM reasoning

Verification logic

Department routing

RAG knowledge base

Agent communication

Member 3 — Backend / Database / Geospatial

FastAPI

PostgreSQL / PostGIS

Complaint APIs

Authentication

Ticket management

Geospatial queries

Backend integration

Member 4 — Frontend / Product / Dashboard

Citizen reporting UI

Authority dashboard

Complaint tracking

Map visualization

Priority visualization

Field worker interface

Before/after evidence UI

Development Roadmap

Phase 1 — Foundation

Git repository

ML directory structure

Class configuration

.gitignore

Requirements

Project README

Phase 2 — Dataset

Dataset collection

Dataset inspection

Class mapping

Dataset merge

Duplicate check

Class balance analysis

Train/validation/test split

Phase 3 — Computer Vision

YOLO baseline

Model training

Validation

Error analysis

Model optimization

Inference pipeline

Phase 4 — Intelligent Processing

Severity estimation

Image embeddings

Duplicate detection

Before/after verification

Phase 5 — Agents

Classification Agent

Verification Agent

Priority Agent

Routing Agent

Resolution Agent

Civic Intelligence Agent

Phase 6 — Backend

FastAPI

PostgreSQL / PostGIS

Complaint APIs

Agent integration

Image storage

Phase 7 — Frontend

Citizen interface

Authority dashboard

Field worker interface

Map

Complaint timeline

Phase 8 — Demo

End-to-end testing

Demo dataset

Performance evaluation

Docker setup

Deployment

Evaluation

Object detection

Measure:

Precision

Recall

mAP@50

mAP@50–95

F1-score

Inference latency

Duplicate detection

Measure:

Similarity accuracy

Precision

Recall

False duplicate rate

Missed duplicate rate

Resolution verification

Measure:

Correctly resolved cases

False resolution cases

Reopened cases

Verification confidence

Performance numbers will be added only after actual validation. No fabricated metrics are used in this README.

Hackathon Demo

Example: Pothole

Citizen uploads pothole image + location
              ↓
Classification Agent
              ↓
Pothole detected with confidence
              ↓
Verification Agent
              ↓
Duplicate search
              ↓
Multiple nearby reports found
              ↓
Priority Agent
              ↓
HIGH PRIORITY
              ↓
Roads / Public Works Department
              ↓
Field team repairs pothole
              ↓
After-repair image uploaded
              ↓
Resolution Verification Agent
              ↓
Issue no longer detected
              ↓
Complaint closed
              ↓
Hotspot added to city intelligence

Why this is a strong demo

It demonstrates the complete AI-agent loop rather than only showing a classifier:

Detection → Reasoning → Decision → Routing → Action → Verification → Learning

Security and Reliability

Production deployment should include:

File type and size validation

Authentication and role-based access

Secure image storage

Input sanitization

Audit logs

Agent output validation

Confidence thresholds

Human review for uncertain/high-impact decisions

Protection of citizen information

Rate limiting and abuse prevention

AI outputs should be treated as decision-support signals rather than unquestionable ground truth.

Current Status

Component

Status

Repository

✅ Complete

GitHub integration

✅ Complete

ML structure

✅ Complete

Class configuration

✅ Complete

.gitignore

✅ Complete

Requirements

✅ Complete

Dataset collection

🔄 Next

Dataset merging

⏳

Dataset analysis

⏳

YOLO training

⏳

Model evaluation

⏳

Severity estimation

⏳

Duplicate detection

⏳

Repair verification

⏳

AI agents

⏳

Backend

⏳

Frontend

⏳

End-to-end demo

⏳

Future Scope

Multilingual complaint reporting

Regional-language voice input

Emergency escalation

Official municipal system integration

Predictive infrastructure maintenance

Road condition mapping

Recurring issue prediction

City-wide infrastructure health scoring

Resource allocation optimization

Mobile application

Offline-first reporting

Setup

Clone

git clone https://github.com/HackIndiaXYZ/hackindia-ai-cybertech-hackathon-2026-hackathon-survivers.git
cd hackindia-ai-cybertech-hackathon-2026-hackathon-survivers

Windows

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

Linux / macOS

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

ML experimentation is being developed using Google Colab. Large datasets, trained weights and generated runs remain outside Git tracking.

Hackathon

HackIndia AI & CyberTech Hackathon 2026
Track: AI & AI Agents
Project: FixMyCity AI

One-line pitch

FixMyCity AI turns civic complaints into verified, prioritized, correctly routed, and trackable resolutions.

Core differentiator

Traditional systems often stop at:

Complaint → Ticket

FixMyCity AI aims to provide:

Complaint
   ↓
Understand
   ↓
Verify
   ↓
Prioritize
   ↓
Route
   ↓
Track
   ↓
Resolve
   ↓
Verify
   ↓
Learn

The system does not just register a civic complaint — it follows the complaint through the resolution lifecycle and uses AI to verify whether the reported problem was actually fixed.

Vision

From reporting city problems to helping cities resolve them intelligently.

Disclaimer

This repository is a hackathon project. Production deployment would require validation with real municipal workflows, representative datasets, security controls, privacy protections, and appropriate human oversight.