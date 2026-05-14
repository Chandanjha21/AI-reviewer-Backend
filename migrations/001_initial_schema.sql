create extension if not exists "pgcrypto";

create table if not exists organizations (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    created_on timestamptz not null default now(),
    updated_on timestamptz not null default now()
);

create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id) on delete cascade,
    name text not null,
    email text not null unique,
    password_hash text not null,
    role text not null check (role in ('admin', 'reviewer')),
    is_active boolean not null default true,
    last_login timestamptz,
    created_on timestamptz not null default now(),
    updated_on timestamptz not null default now(),
    unique (id, organization_id)
);

create table if not exists customers (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id) on delete cascade,
    lead_name text not null,
    company_name text,
    email text not null,
    phone text,
    lead_context text,
    original_message text not null,
    source text,
    priority text,
    tags text[] not null default '{}',
    created_by uuid not null references users(id),
    created_on timestamptz not null default now(),
    updated_on timestamptz not null default now(),
    unique (id, organization_id)
);

create table if not exists work_items (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references organizations(id) on delete cascade,
    customer_id uuid not null,
    assigned_reviewer_id uuid references users(id) on delete set null,
    ai_output text,
    edited_output text,
    reviewer_note text,
    status text not null check (
        status in (
            'pending_review',
            'approved',
            'rejected',
            'regenerating',
            'processing',
            'sent',
            'failed'
        )
    ),
    ai_confidence_score numeric(5, 4),
    generation_version integer not null default 1,
    processing_started_at timestamptz,
    processed_at timestamptz,
    created_on timestamptz not null default now(),
    updated_on timestamptz not null default now(),
    foreign key (customer_id, organization_id)
        references customers(id, organization_id)
        on delete cascade
);

create index if not exists idx_users_organization_id on users(organization_id);
create index if not exists idx_users_org_role_active on users(organization_id, role, is_active);
create index if not exists idx_customers_organization_id on customers(organization_id);
create index if not exists idx_customers_created_by on customers(created_by);
create index if not exists idx_work_items_organization_id on work_items(organization_id);
create index if not exists idx_work_items_customer_id on work_items(customer_id);
create index if not exists idx_work_items_assigned_reviewer_id on work_items(assigned_reviewer_id);
create index if not exists idx_work_items_status on work_items(status);

create or replace function set_updated_on()
returns trigger as $$
begin
    new.updated_on = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists set_organizations_updated_on on organizations;
create trigger set_organizations_updated_on
before update on organizations
for each row execute function set_updated_on();

drop trigger if exists set_users_updated_on on users;
create trigger set_users_updated_on
before update on users
for each row execute function set_updated_on();

drop trigger if exists set_customers_updated_on on customers;
create trigger set_customers_updated_on
before update on customers
for each row execute function set_updated_on();

drop trigger if exists set_work_items_updated_on on work_items;
create trigger set_work_items_updated_on
before update on work_items
for each row execute function set_updated_on();

alter table organizations enable row level security;
alter table users enable row level security;
alter table customers enable row level security;
alter table work_items enable row level security;
