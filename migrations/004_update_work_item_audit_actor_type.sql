alter table work_item_audit_logs
drop constraint if exists work_item_audit_logs_actor_type_check;

alter table work_item_audit_logs
add constraint work_item_audit_logs_actor_type_check
check (actor_type in ('admin', 'reviewer', 'system'));

update work_item_audit_logs
set actor_type = coalesce(
    (
        select users.role
        from users
        where users.id = work_item_audit_logs.actor_id
    ),
    'system'
)
where actor_type = 'user';
