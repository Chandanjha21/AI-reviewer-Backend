update public.work_items as wi
set
    assigned_reviewer_id = coalesce(
        (
            select u.id
            from public.users as u
            where
                u.organization_id = wi.organization_id
                and u.role = 'reviewer'
                and u.is_active = true
            order by u.created_on asc
            limit 1
        ),
        c.created_by
    ),
    updated_on = now()
from public.customers as c
where
    wi.customer_id = c.id
    and wi.organization_id = c.organization_id
    and wi.assigned_reviewer_id is null;
