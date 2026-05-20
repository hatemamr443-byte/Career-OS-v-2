"""Seed mock jobs, emails, and sample CV for new users."""
from datetime import datetime, timezone, timedelta
from db import jobs, emails, profiles
from models import new_id

MOCK_JOBS = [
    {
        "title": "Senior Backend Engineer",
        "company": "Stripe",
        "location": "Remote (US)",
        "remote": True,
        "salary_range": "$180k - $260k",
        "description": "Build and scale Stripe's payment infrastructure. Work on distributed systems handling billions of dollars in transactions. We use Ruby, Go, and Python. You'll own services end-to-end and collaborate with product, design, and operations.",
        "skills_required": ["python", "go", "distributed systems", "postgres", "kafka", "api design"],
        "seniority": "senior",
    },
    {
        "title": "Staff ML Engineer — Inference",
        "company": "Anthropic",
        "location": "San Francisco, CA",
        "remote": False,
        "salary_range": "$300k - $450k",
        "description": "Optimize Claude inference for scale. Work on GPU efficiency, batching, KV cache optimization, and serving infrastructure. Strong CUDA/Triton experience required. You'll partner with research to deploy frontier models.",
        "skills_required": ["python", "cuda", "triton", "ml infrastructure", "pytorch", "distributed training"],
        "seniority": "lead",
    },
    {
        "title": "Full-Stack Engineer",
        "company": "Linear",
        "location": "Remote (Worldwide)",
        "remote": True,
        "salary_range": "$160k - $220k",
        "description": "Help build the issue tracker the world's best teams love. TypeScript, React, Node, Postgres. Strong product taste, obsession with craft and performance. Real-time sync, offline-first.",
        "skills_required": ["typescript", "react", "node.js", "postgres", "graphql", "ui engineering"],
        "seniority": "mid",
    },
    {
        "title": "AI Product Engineer",
        "company": "Vercel",
        "location": "Remote (US/EU)",
        "remote": True,
        "salary_range": "$170k - $240k",
        "description": "Build AI-native developer tools. Ship Next.js + AI SDK features. You'll prototype, ship, and iterate on LLM-powered DX. TypeScript, React, Python.",
        "skills_required": ["typescript", "react", "next.js", "llm", "python", "developer tools"],
        "seniority": "mid",
    },
    {
        "title": "Data Engineer",
        "company": "Notion",
        "location": "New York, NY",
        "remote": False,
        "salary_range": "$170k - $230k",
        "description": "Own the data platform powering Notion's analytics, growth, and ML. Build pipelines, warehouse models, and tooling. Snowflake, dbt, Airflow, Python.",
        "skills_required": ["python", "sql", "dbt", "airflow", "snowflake", "data modeling"],
        "seniority": "senior",
    },
    {
        "title": "Frontend Engineer — Design Systems",
        "company": "Figma",
        "location": "Remote (US)",
        "remote": True,
        "salary_range": "$150k - $210k",
        "description": "Build and maintain Figma's design system. React, TypeScript, accessibility, performance. Ship polished, animated UI used by millions.",
        "skills_required": ["react", "typescript", "css", "design systems", "accessibility", "animation"],
        "seniority": "mid",
    },
    {
        "title": "Engineering Manager — Platform",
        "company": "Cloudflare",
        "location": "Austin, TX",
        "remote": False,
        "salary_range": "$220k - $310k",
        "description": "Lead the platform team building Cloudflare's edge runtime. Manage 6-8 engineers. Strong technical background in distributed systems and people leadership.",
        "skills_required": ["leadership", "distributed systems", "rust", "go", "edge computing"],
        "seniority": "lead",
    },
    {
        "title": "DevOps Engineer",
        "company": "Supabase",
        "location": "Remote (Worldwide)",
        "remote": True,
        "salary_range": "$140k - $200k",
        "description": "Operate Supabase's Postgres-as-a-Service infrastructure. Kubernetes, Terraform, AWS. On-call rotation. Open source contributions encouraged.",
        "skills_required": ["kubernetes", "terraform", "aws", "postgres", "linux", "devops"],
        "seniority": "mid",
    },
    {
        "title": "Junior Software Engineer",
        "company": "Retool",
        "location": "San Francisco, CA",
        "remote": False,
        "salary_range": "$130k - $170k",
        "description": "New grad / early career role. Work across the stack on Retool's internal tools platform. TypeScript, React, Node. Mentorship and growth.",
        "skills_required": ["typescript", "react", "node.js", "sql"],
        "seniority": "junior",
    },
    {
        "title": "Security Engineer",
        "company": "1Password",
        "location": "Remote (Canada/US)",
        "remote": True,
        "salary_range": "$160k - $220k",
        "description": "Protect 100M+ users. Application security, threat modeling, incident response. Rust/Go, cryptography fundamentals.",
        "skills_required": ["security", "cryptography", "rust", "go", "threat modeling"],
        "seniority": "senior",
    },
]

MOCK_EMAILS = [
    {
        "from_name": "Sarah Chen",
        "from_addr": "sarah.chen@stripe.com",
        "subject": "Next steps — Senior Backend Engineer at Stripe",
        "body": "Hi! Thanks for applying. We loved your background. We'd like to schedule a 45-min technical screen this week. Could you share availability for Wed/Thu afternoon PT? — Sarah, Recruiting at Stripe",
        "company": "Stripe",
    },
    {
        "from_name": "Marcus Olin",
        "from_addr": "marcus@vercel.com",
        "subject": "Application update — AI Product Engineer",
        "body": "Hi — thanks for the time you put into your application. After review, we've decided to move forward with other candidates whose background is closer to the role. We'll keep your profile on file. Best, Marcus",
        "company": "Vercel",
    },
    {
        "from_name": "Linear Talent",
        "from_addr": "talent@linear.app",
        "subject": "We'd love to chat — Full-Stack Engineer",
        "body": "Hello! Your portfolio caught our eye. Are you open to a 30-min intro call with our hiring manager next week? — Linear Talent Team",
        "company": "Linear",
    },
    {
        "from_name": "Jamie Park",
        "from_addr": "jamie@notion.so",
        "subject": "Offer — Data Engineer at Notion",
        "body": "Congratulations! We're thrilled to extend an offer for the Data Engineer role. Base $195k + equity + benefits. Please review the attached letter. We'd love your decision by Friday. — Jamie",
        "company": "Notion",
    },
    {
        "from_name": "Anthropic Recruiting",
        "from_addr": "recruiting@anthropic.com",
        "subject": "Coding interview scheduled — Staff ML Engineer",
        "body": "Hi, your coding interview is confirmed for Tuesday 2pm PT. We'll send a HackerRank link 30 min before. Topics: systems design + CUDA optimization. — Anthropic Recruiting",
        "company": "Anthropic",
    },
]


async def seed_jobs_if_empty():
    count = await jobs.count_documents({})
    if count > 0:
        return
    docs = []
    base = datetime.now(timezone.utc)
    for i, j in enumerate(MOCK_JOBS):
        d = {
            **j,
            "job_id": new_id("job"),
            "source": "mock",
            "source_url": f"https://example.com/jobs/{i}",
            "posted_at": (base - timedelta(days=i)).isoformat(),
            "fetched_at": base.isoformat(),
        }
        docs.append(d)
    await jobs.insert_many(docs)


async def seed_user_emails(user_id: str) -> None:
    """DISABLED — No fake recruiter emails. Real inbox comes from Gmail OAuth only."""
    pass


SAMPLE_CV = """Alex Rivera
Senior Software Engineer • 6 years experience

EXPERIENCE
Senior Backend Engineer — Datadog (2022–Present)
- Built and scaled metrics ingestion pipeline handling 5M events/sec
- Led migration from monolith to microservices on Kubernetes
- Stack: Python, Go, Kafka, PostgreSQL, AWS

Software Engineer — Twilio (2019–2022)
- Designed REST and gRPC APIs serving 10B+ requests/month
- Mentored 3 junior engineers
- Stack: Python, Node.js, Redis, MySQL

EDUCATION
B.S. Computer Science — UC Berkeley (2019)

SKILLS
Python, Go, TypeScript, Kafka, PostgreSQL, Redis, Kubernetes, AWS, distributed systems, API design, system design
"""


async def seed_user_profile(user_id: str):
    existing = await profiles.find_one({"user_id": user_id}, {"_id": 0})
    if existing:
        return
    await profiles.insert_one({
        "user_id": user_id,
        "cv_text": SAMPLE_CV,
        "headline": "Senior Software Engineer • Backend & Distributed Systems",
        "skills": ["python", "go", "typescript", "kafka", "postgres", "redis", "kubernetes", "aws", "distributed systems", "api design"],
        "target_roles": ["Senior Backend Engineer", "Staff Engineer", "Tech Lead"],
        "target_locations": ["Remote", "San Francisco", "New York"],
        "salary_min": 180000,
        "years_experience": 6,
        "behavior": {"applications_today": 0, "avoids_lead_roles": False},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
