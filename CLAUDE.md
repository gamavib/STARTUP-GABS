# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Infrastructure
- Start all services: `docker-compose up -d`
- Stop all services: `docker-compose down`
- Restart backend: `docker-compose restart backend`
- Restart frontend: `docker-compose restart frontend`
- View backend logs: `docker logs -f insurance_saas_backend`
- View frontend logs: `docker logs -f insurance_saas_frontend`

### Backend (FastAPI)
- Install dependencies: `pip install -r requirements.txt`
- Run locally (dev): `uvicorn app.main:app --reload`

### Frontend (React)
- Install dependencies: `cd frontend && npm install`
- Start development server: `cd frontend && npm start`
- Build for production: `cd frontend && npm run build`
- Run tests: `cd frontend && npm test`

## Architecture Overview

The project is a B2B SaaS platform for Reinsurance Optimization, focusing on actuarial science and capital management.

### Core Components
- **Frontend**: React.js with Recharts for actuarial dashboards and volatility heatmaps.
- **Backend**: FastAPI (Python 3.12) providing a REST API for data ingestion and actuarial processing.
- **Actuarial Engine**: Specialized Python modules (`app/modules/actuarial`) using Pandas and NumPy for:
    - Siniestrality Triangles construction.
    - IBNR calculations (S-Smoothing, Chain Ladder, Bornhuetter-Ferguson, Cape Cod).
    - Tail Factor projections.
- **Diagnostics**: Data validation and governance (`app/modules/diagnostics`) ensuring data integrity before actuarial processing.
- **Database**: PostgreSQL 15 with a multi-tenant architecture (isolated by `company_id`).
- **Security**: JWT-based authentication and authorization.

### Data Flow
`CSV Input` $\rightarrow$ `Diagnostics/Governance` $\rightarrow$ `PostgreSQL` $\rightarrow$ `Actuarial Engine` $\rightarrow$ `TCR (Total Cost of Risk) Optimization` $\rightarrow$ `Burn-through Analysis` $\rightarrow$ `Renewal Package` $\rightarrow$ `Executive Dashboard`

### Key Directories
- `/app`: Backend source code (API endpoints, core logic).
- `/app/modules/actuarial`: The core actuarial engine and projection models.
- `/app/modules/diagnostics`: Data validation and quality control.
- `/frontend`: React application source.
- `/documentacion`: Detailed architecture, strategy, and technical specifications.
