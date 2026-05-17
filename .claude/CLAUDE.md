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
- Install dependencies: `pnpm install`
- Start development server: `pnpm start`
- Build for production: `pnpm run build`
- Run tests: `pnpm test`
- Lint code: `pnpm run lint` (if configured)

## Architecture Overview

The project is a B2B SaaS platform for Reinsurance Optimization, focusing on actuarial science and capital management.

### Core Components
- **Frontend**: Next.js 14 (App Router) with a client-side mounting pattern to avoid hydration mismatches.
- **Backend**: FastAPI (Python 3.12) providing a REST API.
- **Actuarial Engine**: Specialized Python modules (`app/modules/actuarial`) using Pandas/NumPy (with a roadmap to Polars) for:
    - Siniestrality Triangles and IBNR calculations (S-Smoothing, Chain Ladder, BF, Cape Cod).
    - Tail Factor projections and Back-testing.
    - Economic Capital (EC) models based on TCR minimization and Solvencia II (VaR 99.5%).
- **Diagnostics**: Data validation and governance (`app/modules/diagnostics`) for CSV ingestion.
- **Database**: PostgreSQL 15 with a multi-tenant architecture isolated by `company_id` (Row Level Security - RLS).
- **Asynchronous Processing**: Celery + Redis for CPU-intensive actuarial calculations.

### Data Flow
`CSV Input` $\rightarrow$ `Diagnostics/Governance` $\rightarrow$ `PostgreSQL` $\rightarrow$ `Actuarial Engine` $\rightarrow$ `TCR Optimization` $\rightarrow$ `Burn-through Analysis` $\rightarrow$ `Renewal Package` $\rightarrow$ `Executive Dashboard`

### Key Directories
- `/app`: Backend source code.
- `/app/modules/actuarial`: Core actuarial engine and projection models.
- `/app/modules/diagnostics`: Data validation and quality control.
- `/frontend`: Next.js application source.
- `/documentacion`: Technical specifications, architecture, and evolution strategies.
