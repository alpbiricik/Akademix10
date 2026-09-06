-- AkademX10 XAI reference seed data.
-- Idempotent and non-destructive. Does not create auth.users rows.

begin;

insert into public.companies (id, name, industry, status, created_at, updated_at) values
('00000000-0000-0000-0000-000000000101', 'Northwind Sales Academy', 'B2B SaaS Sales', 'active', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000102', 'Contoso Enablement Lab', 'Customer Success', 'active', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z')
on conflict (id) do update set
  name = excluded.name,
  industry = excluded.industry,
  status = excluded.status,
  updated_at = excluded.updated_at;

insert into public.users (id, email, full_name, role, title, status, created_at, updated_at)
select v.id, v.email, v.full_name, v.role, v.title, v.status, v.created_at::timestamptz, v.updated_at::timestamptz
from (values
  ('00000000-0000-0000-0000-000000000201'::uuid, 'platform@akademx10.local', 'Deniz', 'platform', 'Platform Operator', 'active', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z'),
  ('00000000-0000-0000-0000-000000000202'::uuid, 'hr@northwind.local', 'Ece', 'company', 'HR Manager', 'active', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z'),
  ('00000000-0000-0000-0000-000000000203'::uuid, 'learner@northwind.local', 'Alp', 'learner', 'Employee', 'active', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z'),
  ('00000000-0000-0000-0000-000000000204'::uuid, 'learner@contoso.local', 'Mina', 'learner', 'Employee', 'active', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z'),
  ('00000000-0000-0000-0000-000000000205'::uuid, 'hr@contoso.local', 'Can', 'company', 'HR Manager', 'active', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z')
) as v(id, email, full_name, role, title, status, created_at, updated_at)
where exists (select 1 from auth.users au where au.id = v.id)
on conflict (id) do update set
  email = excluded.email,
  full_name = excluded.full_name,
  role = excluded.role,
  title = excluded.title,
  status = excluded.status,
  updated_at = excluded.updated_at;

insert into public.company_members (id, company_id, user_id, role_in_company, status, created_at)
select v.id, v.company_id, v.user_id, v.role_in_company, v.status, v.created_at::timestamptz
from (values
  ('00000000-0000-0000-0000-000000000301'::uuid, '00000000-0000-0000-0000-000000000101'::uuid, '00000000-0000-0000-0000-000000000202'::uuid, 'hr_manager', 'active', '2026-07-29T09:00:00Z'),
  ('00000000-0000-0000-0000-000000000302'::uuid, '00000000-0000-0000-0000-000000000101'::uuid, '00000000-0000-0000-0000-000000000203'::uuid, 'learner', 'active', '2026-07-29T09:00:00Z'),
  ('00000000-0000-0000-0000-000000000303'::uuid, '00000000-0000-0000-0000-000000000102'::uuid, '00000000-0000-0000-0000-000000000204'::uuid, 'learner', 'active', '2026-07-29T09:00:00Z'),
  ('00000000-0000-0000-0000-000000000304'::uuid, '00000000-0000-0000-0000-000000000102'::uuid, '00000000-0000-0000-0000-000000000205'::uuid, 'hr_manager', 'active', '2026-07-29T09:00:00Z')
) as v(id, company_id, user_id, role_in_company, status, created_at)
where exists (select 1 from public.users u where u.id = v.user_id)
on conflict (company_id, user_id) do update set
  role_in_company = excluded.role_in_company,
  status = excluded.status;

insert into public.training_templates (id, title, description, category, estimated_duration_min, default_state_count, skill_tags, status, version, created_by, avatar_policy, created_at, updated_at) values
('00000000-0000-0000-0000-000000000401', 'Leadership', 'Coaching, feedback, accountability, and team alignment.', 'Leadership', 35, 18, array['Coaching','Feedback','Accountability'], 'active', '1.0', null, '{"mode":"lite","activeTargetMin":7,"openCloseTarget":10,"bufferedBillableMin":8.05,"safeBudgetUsd":1.25}', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000402', 'Project Management', 'Scope alignment, stakeholder updates, and risk escalation.', 'Project Management', 45, 20, array['Planning','Risk Framing','Stakeholder Alignment'], 'active', '1.0', null, '{"mode":"lite","activeTargetMin":7,"openCloseTarget":10,"bufferedBillableMin":8.05,"safeBudgetUsd":1.25}', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000403', 'Workplace Ethics', 'Ethical risk recognition, speak-up practice, and escalation paths.', 'Workplace Ethics', 30, 16, array['Judgment','Courage','Policy Awareness'], 'active', '1.0', null, '{"mode":"lite","activeTargetMin":7,"openCloseTarget":10,"bufferedBillableMin":8.05,"safeBudgetUsd":1.25}', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000404', 'Sales / Customer Communication', 'Consultative communication, objection handling, empathy, and closing.', 'Sales / Customer Communication', 40, 21, array['Communication','Empathy','Objection Handling','Closing','Confidence'], 'active', '1.0', (select id from public.users where id = '00000000-0000-0000-0000-000000000201'), '{"mode":"lite","activeTargetMin":7,"openCloseTarget":10,"bufferedBillableMin":8.05,"safeBudgetUsd":1.25}', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000405', 'Stress Management', 'Pressure awareness, self-regulation, and action planning.', 'Wellbeing', 40, 18, array['Self-awareness','Composure','Boundary Setting'], 'active', '1.0', null, '{"mode":"lite","activeTargetMin":7,"openCloseTarget":10,"bufferedBillableMin":8.05,"safeBudgetUsd":1.25}', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000406', 'Onboarding', 'Role ramp, culture, process fluency, and first-week confidence.', 'Onboarding', 30, 14, array['Role Clarity','Process Fluency','Confidence'], 'active', '1.0', null, '{"mode":"lite","activeTargetMin":7,"openCloseTarget":10,"bufferedBillableMin":8.05,"safeBudgetUsd":1.25}', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z')
on conflict (id) do update set
  title = excluded.title,
  description = excluded.description,
  category = excluded.category,
  estimated_duration_min = excluded.estimated_duration_min,
  default_state_count = excluded.default_state_count,
  skill_tags = excluded.skill_tags,
  status = excluded.status,
  version = excluded.version,
  created_by = excluded.created_by,
  avatar_policy = excluded.avatar_policy,
  updated_at = excluded.updated_at;

insert into public.training_modules (id, template_id, title, description, duration_min, status, created_at, updated_at) values
('00000000-0000-0000-0000-000000000501', '00000000-0000-0000-0000-000000000404', 'AI Roleplay: Customer Communication', 'A 40-minute AI-powered roleplay session for customer empathy, objection handling, and next-step closing.', 40, 'active', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z')
on conflict (id) do update set
  title = excluded.title,
  description = excluded.description,
  duration_min = excluded.duration_min,
  status = excluded.status,
  updated_at = excluded.updated_at;

insert into public.training_states (id, module_id, order_index, title, type, estimated_min, avatar_enabled, avatar_budget_sec, prompt, rubric, skill_tags, completion_rule, created_at, updated_at) values
('00000000-0000-0000-0000-000000000601','00000000-0000-0000-0000-000000000501',1,'Welcome and session goals','intro',2,false,0,'Welcome to your AI customer communication roleplay.','{"text":"Understands the journey and scoring model."}',array['Communication','Confidence'],'{"type":"viewed"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000602','00000000-0000-0000-0000-000000000501',2,'Customer context brief','video',2,false,0,'Short video: a renewal customer is unsure whether the platform is worth the cost.','{"text":"Identifies context and conversation objective."}',array['Product Knowledge','Communication'],'{"type":"viewed"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000603','00000000-0000-0000-0000-000000000501',3,'Avatar coach welcome','avatar',3,true,45,'LiveAvatar Lite frames the practice standard.','{"text":"Receives concise coaching."}',array['Confidence'],'{"type":"viewed"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000604','00000000-0000-0000-0000-000000000501',4,'First response','question',1,false,0,'Customer says: We are not sure the platform is worth renewing. What is your first response?','{"text":"Acknowledges concern and asks discovery."}',array['Empathy','Communication'],'{"type":"answered"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000605','00000000-0000-0000-0000-000000000501',5,'Value framing lesson','video',2,false,0,'Connect product value to customer outcomes instead of feature lists.','{"text":"Uses outcome language."}',array['Product Knowledge','Closing'],'{"type":"viewed"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000606','00000000-0000-0000-0000-000000000501',6,'Competitor objection','roleplay',3,true,60,'Customer: Your competitor is cheaper and promises faster onboarding.','{"text":"Handles price and value calmly."}',array['Objection Handling','Confidence'],'{"type":"answered"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000607','00000000-0000-0000-0000-000000000501',7,'Roleplay checkpoint','feedback',1,false,0,'Summarize where the response created trust.','{"text":"Feedback is behavior-specific."}',array['Communication'],'{"type":"manual"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000608','00000000-0000-0000-0000-000000000501',8,'Discovery reflection','reflection',2,false,0,'Write two discovery questions for the renewal concern.','{"text":"Questions are open-ended."}',array['Communication','Empathy'],'{"type":"answered"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000609','00000000-0000-0000-0000-000000000501',9,'Proof point lesson','video',3,false,0,'Use adoption, retention, and time-to-value as proof points.','{"text":"Connects proof to outcomes."}',array['Product Knowledge'],'{"type":"viewed"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000610','00000000-0000-0000-0000-000000000501',10,'ROI objection drill','question',1,false,0,'How would you respond to: I do not see measurable ROI?','{"text":"Proposes evidence review."}',array['Objection Handling'],'{"type":"answered"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000611','00000000-0000-0000-0000-000000000501',11,'Coach micro-model','avatar',2,true,45,'Avatar demonstrates an empathy-to-value response pattern.','{"text":"Notices reusable structure."}',array['Empathy'],'{"type":"viewed"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000612','00000000-0000-0000-0000-000000000501',12,'Executive stakeholder','roleplay',3,true,60,'Customer: My CFO only cares about cost.','{"text":"Maps value to business evidence."}',array['Closing','Product Knowledge'],'{"type":"answered"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000613','00000000-0000-0000-0000-000000000501',13,'Stakeholder feedback','feedback',1,false,0,'Compare answer against clarity, evidence, and next action.','{"text":"Scores are transparent."}',array['Communication','Closing'],'{"type":"manual"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000614','00000000-0000-0000-0000-000000000501',14,'Closing lesson','video',2,false,0,'Closing means securing a useful next commitment.','{"text":"Understands next-step closing."}',array['Closing'],'{"type":"viewed"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000615','00000000-0000-0000-0000-000000000501',15,'Closing question','question',3,false,0,'What question would you ask before proposing the next meeting?','{"text":"Clarifies decision process."}',array['Closing','Communication'],'{"type":"answered"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000616','00000000-0000-0000-0000-000000000501',16,'Pricing follow-up','roleplay',1,true,60,'Customer: Send pricing and I will think about it.','{"text":"Guides toward dated follow-up."}',array['Closing','Confidence'],'{"type":"answered"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000617','00000000-0000-0000-0000-000000000501',17,'Personal phrase','reflection',2,false,0,'Write one sentence for your next objection conversation.','{"text":"Action is specific."}',array['Communication'],'{"type":"answered"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000618','00000000-0000-0000-0000-000000000501',18,'Final coaching cue','avatar',3,true,45,'Avatar gives one final cue before the action plan.','{"text":"Practical coaching."}',array['Confidence'],'{"type":"viewed"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000619','00000000-0000-0000-0000-000000000501',19,'Final scoring checkpoint','feedback',1,false,0,'Summarize progress and one focus area.','{"text":"Connects strengths and growth."}',array['Communication'],'{"type":"manual"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000620','00000000-0000-0000-0000-000000000501',20,'Final action plan','reflection',2,false,0,'Write your final action plan.','{"text":"Action plan is concrete."}',array['Action Planning'],'{"type":"answered"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z'),
('00000000-0000-0000-0000-000000000621','00000000-0000-0000-0000-000000000501',21,'Final summary','final',2,true,105,'Session complete. Open your report for next actions.','{"text":"Completion and report handoff."}',array['Communication'],'{"type":"viewed"}','2026-07-29T09:00:00Z','2026-07-29T09:00:00Z')
on conflict (module_id, order_index) do update set
  title = excluded.title,
  type = excluded.type,
  estimated_min = excluded.estimated_min,
  avatar_enabled = excluded.avatar_enabled,
  avatar_budget_sec = excluded.avatar_budget_sec,
  prompt = excluded.prompt,
  rubric = excluded.rubric,
  skill_tags = excluded.skill_tags,
  completion_rule = excluded.completion_rule,
  updated_at = excluded.updated_at;

insert into public.company_training_assignments (id, company_id, template_id, module_id, assigned_by, status, starts_at, due_at, created_at)
values ('00000000-0000-0000-0000-000000000701', '00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000404', '00000000-0000-0000-0000-000000000501', (select id from public.users where id = '00000000-0000-0000-0000-000000000201'), 'active', '2026-07-29T09:00:00Z', null, '2026-07-29T09:00:00Z')
on conflict (company_id, module_id) do update set
  template_id = excluded.template_id,
  assigned_by = excluded.assigned_by,
  status = excluded.status,
  starts_at = excluded.starts_at,
  due_at = excluded.due_at;

insert into public.company_training_assignments (id, company_id, template_id, module_id, assigned_by, status, starts_at, due_at, created_at)
select '00000000-0000-0000-0000-000000000702', '00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000404', '00000000-0000-0000-0000-000000000501', (select id from public.users where id = '00000000-0000-0000-0000-000000000201'), 'active', '2026-07-29T09:00:00Z', null, '2026-07-29T09:00:00Z'
where exists (select 1 from public.users where id = '00000000-0000-0000-0000-000000000205')
on conflict (company_id, module_id) do update set
  template_id = excluded.template_id,
  assigned_by = excluded.assigned_by,
  status = excluded.status,
  starts_at = excluded.starts_at,
  due_at = excluded.due_at;

insert into public.learner_enrollments (id, assignment_id, company_id, learner_id, module_id, status, assigned_at, started_at, completed_at)
select '00000000-0000-0000-0000-000000000801', '00000000-0000-0000-0000-000000000701', '00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000203', '00000000-0000-0000-0000-000000000501', 'in_progress', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z', null
where exists (select 1 from public.users where id = '00000000-0000-0000-0000-000000000203')
on conflict (assignment_id, learner_id) do update set
  status = excluded.status,
  started_at = excluded.started_at,
  completed_at = excluded.completed_at;

insert into public.learner_enrollments (id, assignment_id, company_id, learner_id, module_id, status, assigned_at, started_at, completed_at)
select '00000000-0000-0000-0000-000000000802', '00000000-0000-0000-0000-000000000702', '00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000204', '00000000-0000-0000-0000-000000000501', 'in_progress', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z', null
where exists (select 1 from public.users where id = '00000000-0000-0000-0000-000000000204')
on conflict (assignment_id, learner_id) do update set
  status = excluded.status,
  started_at = excluded.started_at,
  completed_at = excluded.completed_at;

insert into public.training_sessions (id, enrollment_id, module_id, template_id, learner_id, company_id, current_state_id, completed_state_ids, status, started_at, updated_at, completed_at, metadata)
select '00000000-0000-0000-0000-000000000901', '00000000-0000-0000-0000-000000000801', '00000000-0000-0000-0000-000000000501', '00000000-0000-0000-0000-000000000404', '00000000-0000-0000-0000-000000000203', '00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000601', '{}', 'in_progress', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z', null, '{"source":"reference_seed"}'
where exists (select 1 from public.learner_enrollments where id = '00000000-0000-0000-0000-000000000801')
on conflict (id) do update set
  current_state_id = excluded.current_state_id,
  completed_state_ids = excluded.completed_state_ids,
  status = excluded.status,
  updated_at = excluded.updated_at,
  metadata = excluded.metadata;

insert into public.training_sessions (id, enrollment_id, module_id, template_id, learner_id, company_id, current_state_id, completed_state_ids, status, started_at, updated_at, completed_at, metadata)
select '00000000-0000-0000-0000-000000000902', '00000000-0000-0000-0000-000000000802', '00000000-0000-0000-0000-000000000501', '00000000-0000-0000-0000-000000000404', '00000000-0000-0000-0000-000000000204', '00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000601', '{}', 'in_progress', '2026-07-29T09:00:00Z', '2026-07-29T09:00:00Z', null, '{"source":"reference_seed"}'
where exists (select 1 from public.learner_enrollments where id = '00000000-0000-0000-0000-000000000802')
on conflict (id) do update set
  current_state_id = excluded.current_state_id,
  completed_state_ids = excluded.completed_state_ids,
  status = excluded.status,
  updated_at = excluded.updated_at,
  metadata = excluded.metadata;

insert into public.session_usage (id, session_id, total_duration_min, avatar_target_min, avatar_used_min, avatar_open_count, buffered_avatar_min, estimated_avatar_cost_usd, estimated_total_cost_usd, safe_budget_usd, updated_at)
select '00000000-0000-0000-0000-000000001001', '00000000-0000-0000-0000-000000000901', 40, 7, 0, 0, 8.05, 0, 0.8, 1.25, '2026-07-29T09:00:00Z'
where exists (select 1 from public.training_sessions where id = '00000000-0000-0000-0000-000000000901')
on conflict (session_id) do update set
  total_duration_min = excluded.total_duration_min,
  avatar_target_min = excluded.avatar_target_min,
  buffered_avatar_min = excluded.buffered_avatar_min,
  safe_budget_usd = excluded.safe_budget_usd,
  updated_at = excluded.updated_at;

insert into public.session_usage (id, session_id, total_duration_min, avatar_target_min, avatar_used_min, avatar_open_count, buffered_avatar_min, estimated_avatar_cost_usd, estimated_total_cost_usd, safe_budget_usd, updated_at)
select '00000000-0000-0000-0000-000000001002', '00000000-0000-0000-0000-000000000902', 40, 7, 0, 0, 8.05, 0, 0.8, 1.25, '2026-07-29T09:00:00Z'
where exists (select 1 from public.training_sessions where id = '00000000-0000-0000-0000-000000000902')
on conflict (session_id) do update set
  total_duration_min = excluded.total_duration_min,
  avatar_target_min = excluded.avatar_target_min,
  buffered_avatar_min = excluded.buffered_avatar_min,
  safe_budget_usd = excluded.safe_budget_usd,
  updated_at = excluded.updated_at;

insert into public.reports (id, session_id, learner_id, company_id, module_id, overall_score, skill_summary, strengths, improvement_areas, action_plan, generated_by, generated_at, metadata)
select '00000000-0000-0000-0000-000000001101', '00000000-0000-0000-0000-000000000901', '00000000-0000-0000-0000-000000000203', '00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000501', 80, '[{"skill":"Communication","score":80,"delta":8},{"skill":"Empathy","score":76,"delta":8}]', '["Acknowledges customer concerns.","Links value to outcomes."]', '["Ask one more discovery question.","Use proof points earlier."]', '["Open with empathy and discovery.","Close with a dated next step."]', 'ai', '2026-07-29T09:00:00Z', '{"source":"reference_report"}'
where exists (select 1 from public.training_sessions where id = '00000000-0000-0000-0000-000000000901')
on conflict (session_id) do update set
  overall_score = excluded.overall_score,
  skill_summary = excluded.skill_summary,
  strengths = excluded.strengths,
  improvement_areas = excluded.improvement_areas,
  action_plan = excluded.action_plan,
  generated_by = excluded.generated_by,
  generated_at = excluded.generated_at,
  metadata = excluded.metadata;

insert into public.reports (id, session_id, learner_id, company_id, module_id, overall_score, skill_summary, strengths, improvement_areas, action_plan, generated_by, generated_at, metadata)
select '00000000-0000-0000-0000-000000001102', '00000000-0000-0000-0000-000000000902', '00000000-0000-0000-0000-000000000204', '00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000501', 78, '[{"skill":"Communication","score":78,"delta":6},{"skill":"Empathy","score":74,"delta":6}]', '["Keeps the conversation calm.","Names a concrete customer outcome."]', '["Ask a follow-up question before pitching.","Confirm next steps explicitly."]', '["Use one discovery question.","Close with a dated action."]', 'ai', '2026-07-29T09:00:00Z', '{"source":"reference_report"}'
where exists (select 1 from public.training_sessions where id = '00000000-0000-0000-0000-000000000902')
on conflict (session_id) do update set
  overall_score = excluded.overall_score,
  skill_summary = excluded.skill_summary,
  strengths = excluded.strengths,
  improvement_areas = excluded.improvement_areas,
  action_plan = excluded.action_plan,
  generated_by = excluded.generated_by,
  generated_at = excluded.generated_at,
  metadata = excluded.metadata;

commit;
