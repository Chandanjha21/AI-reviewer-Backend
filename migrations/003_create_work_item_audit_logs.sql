create table if not exists work_item_audit_logs (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id) on delete cascade,
    work_item_id uuid not null references work_items(id) on delete cascade,
    actor_id uuid references users(id) on delete set null,
    actor_type text not null default 'system' check (actor_type in ('admin', 'reviewer', 'system')),
    action text not null check (
        action in (
            'item_created',
            'ai_draft_generated',
            'draft_regenerated',
            'draft_edited',
            'item_approved',
            'item_rejected',
            'background_job_started',
            'background_job_completed',
            'background_job_failed',
            'status_updated'
        )
    ),
    from_status text,
    to_status text,
    metadata jsonb not null default '{}'::jsonb,
    created_on timestamptz not null default now()
);

create index if not exists idx_work_item_audit_logs_organization_id
on work_item_audit_logs(organization_id);

create index if not exists idx_work_item_audit_logs_work_item_id_created_on
on work_item_audit_logs(work_item_id, created_on);

alter table work_item_audit_logs enable row level security;
