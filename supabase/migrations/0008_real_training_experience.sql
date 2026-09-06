-- Real leadership training experience, aligned with the requested 21-state Video/AI path.

begin;

delete from public.session_evaluations
where session_id in (
  select id from public.training_sessions
  where module_id = '00000000-0000-0000-0000-000000000501'
);

delete from public.reports
where module_id = '00000000-0000-0000-0000-000000000501';

delete from public.skill_scores
where session_id in (
  select id from public.training_sessions
  where module_id = '00000000-0000-0000-0000-000000000501'
);

delete from public.session_feedback
where session_id in (
  select id from public.training_sessions
  where module_id = '00000000-0000-0000-0000-000000000501'
);

delete from public.session_answers
where session_id in (
  select id from public.training_sessions
  where module_id = '00000000-0000-0000-0000-000000000501'
);

alter table public.training_states
add column if not exists conversation_config jsonb;

update public.training_templates
set
  title = 'Leadership Essentials: Effective Feedback Conversations',
  description = 'A practical leadership training generated from source material: video lessons, AI avatar conversations, roleplay, final feedback, and action plan.',
  category = 'Leadership',
  estimated_duration_min = 60,
  default_state_count = 21,
  skill_tags = '{}',
  updated_at = now()
where id = '00000000-0000-0000-0000-000000000404';

update public.training_modules
set
  title = 'Leadership Essentials: Effective Feedback Conversations',
  description = 'A 21-step leadership training flow that follows the requested Video/AI path. Video steps are empty placeholders until admin uploads media.',
  duration_min = 60,
  updated_at = now()
where id = '00000000-0000-0000-0000-000000000501';

update public.training_states
set
  title = updates.title,
  type = updates.type,
  estimated_min = updates.estimated_min,
  avatar_enabled = updates.avatar_enabled,
  avatar_budget_sec = updates.avatar_budget_sec,
  prompt = updates.prompt,
  rubric = '{}'::jsonb,
  skill_tags = '{}',
  completion_rule = jsonb_build_object('type', updates.completion_rule),
  conversation_config = updates.conversation_config,
  updated_at = now()
from (values
  (1, 'Tanitim', 'video', 2, false, 0, 'Video placeholder: Egitimin amaci ve liderlik vakasi burada tanitilacak.', 'viewed', null::jsonb),
  (2, 'Interaktif tanisma', 'avatar', 2, true, 45, 'AI avatar katilimciyi karsilar, liderlik deneyimini sorar ve egitim hedefini netlestirir.', 'answered', '{"minTurns":1,"maxTurns":2,"language":"tr","persona":"Liderlik gelisim kocu","scenario":"Katilimci liderlik egitimine basliyor.","objective":"Katilimcinin hedefini netlestirmek.","conversationInstructions":"Turkce konus. Kisa, net ve profesyonel kal. Puanlama yapma.","allowedTopics":["liderlik","geri bildirim","hedef","deneyim"],"completionGuidance":"Katilimci hedefini soylediginde tamamla.","allowCoaching":true}'::jsonb),
  (3, 'Egitim', 'video', 3, false, 0, 'Video placeholder: Etkili geri bildirimin ana yapisi anlatilacak.', 'viewed', null::jsonb),
  (4, 'Interaktif iletisim', 'avatar', 3, true, 60, 'AI avatar katilimcidan yargisiz bir gozlem cumlesi kurmasini ister.', 'answered', '{"minTurns":1,"maxTurns":3,"language":"tr","persona":"Liderlik gelisim kocu","scenario":"Katilimci davranis odakli geri bildirim cumlesi calisiyor.","objective":"Somut ve yargisiz gozlem cumlesi aldirmak.","conversationInstructions":"Turkce konus. Cevap belirsizse somutlastirmasini iste. Puanlama yapma.","allowedTopics":["gozlem","davranis","geri bildirim","performans"],"completionGuidance":"Somut gozlem cumlesi geldiginde tamamla.","allowCoaching":true}'::jsonb),
  (5, 'Egitim', 'video', 3, false, 0, 'Video placeholder: Davranis, etki ve beklenti modeli anlatilacak.', 'viewed', null::jsonb),
  (6, 'Interaktif iletisim', 'avatar', 3, true, 60, 'AI avatar katilimcidan davranis-etki-beklenti modelini kullanarak kisa bir geri bildirim girisi yapmasini ister.', 'answered', '{"minTurns":1,"maxTurns":3,"language":"tr","persona":"Liderlik gelisim kocu","scenario":"Katilimci geri bildirim girisi calisiyor.","objective":"Davranis, etki ve beklenti yapisini uygulatmak.","conversationInstructions":"Turkce konus. Eksik parca varsa nazikce tamamlat. Puanlama yapma.","allowedTopics":["davranis","etki","beklenti","geri bildirim"],"completionGuidance":"Uc parca da gecince tamamla.","allowCoaching":true}'::jsonb),
  (7, 'Egitim', 'video', 3, false, 0, 'Video placeholder: Aktif dinleme ve acik soru kullanimi anlatilacak.', 'viewed', null::jsonb),
  (8, 'Interaktif iletisim', 'avatar', 3, true, 60, 'AI avatar katilimcidan ekip uyesinin bakis acisini anlamak icin iki acik soru uretmesini ister.', 'answered', '{"minTurns":1,"maxTurns":3,"language":"tr","persona":"Liderlik gelisim kocu","scenario":"Katilimci aktif dinleme asamasini calisiyor.","objective":"Iki acik soru urettirmek.","conversationInstructions":"Turkce konus. Kapali veya suclayici sorulari yeniden cercevelet. Puanlama yapma.","allowedTopics":["aktif dinleme","acik soru","ekip uyesi","baglam"],"completionGuidance":"Iki uygun acik soru geldiginde tamamla.","allowCoaching":true}'::jsonb),
  (9, 'Egitim', 'video', 3, false, 0, 'Video placeholder: Zor tepkileri sakin karsilama ve savunmaya gecmeme anlatilacak.', 'viewed', null::jsonb),
  (10, 'Interaktif iletisim', 'avatar', 3, true, 60, 'AI avatar katilimciya savunmaci bir cevap verir; katilimci sakin ve merakli kalmaya calisir.', 'answered', '{"minTurns":1,"maxTurns":3,"language":"tr","persona":"Savunmaya gecen ekip uyesi","scenario":"Ekip uyesi geri bildirime biraz direncli tepki veriyor.","objective":"Katilimcinin sakin, merakli ve net kalmasini saglamak.","conversationInstructions":"Turkce konus. Ilk cevapta hafif savunmaci ol. Katilimci sakin yaklasirsa acil.","allowedTopics":["savunma","dinleme","geri bildirim","sakinlik"],"completionGuidance":"Katilimci sakin bir yanit verdiginde tamamla.","allowCoaching":false}'::jsonb),
  (11, 'Egitim', 'video', 3, false, 0, 'Video placeholder: Net beklenti, destek ve takip tarihi belirleme anlatilacak.', 'viewed', null::jsonb),
  (12, 'Interaktif iletisim', 'avatar', 3, true, 60, 'AI avatar katilimcidan beklenti, destek ve takip tarihini iceren bir kapanis cumlesi kurmasini ister.', 'answered', '{"minTurns":1,"maxTurns":3,"language":"tr","persona":"Liderlik gelisim kocu","scenario":"Katilimci geri bildirim gorusmesini kapatma asamasini calisiyor.","objective":"Net beklenti, destek ve takip tarihi aldirmak.","conversationInstructions":"Turkce konus. Belirsiz cevaplari zaman ve olcut ekleterek netlestir. Puanlama yapma.","allowedTopics":["beklenti","destek","takip tarihi","aksiyon"],"completionGuidance":"Net kapanis cumlesi geldiginde tamamla.","allowCoaching":true}'::jsonb),
  (13, 'Vaka/Role Play Tanitim', 'video', 3, false, 0, 'Video placeholder: Deniz vakasi tanitilacak. Deniz son iki sprintte teslim tarihlerini kacirdi ve toplantilarda sessizlesti.', 'viewed', null::jsonb),
  (14, 'Vaka/Role Play Degerlendirme', 'roleplay', 5, true, 90, 'AI avatar Deniz rolune girer. Katilimci gorusmeyi baslatir, gozlem paylasir, dinler, beklentiyi netlestirir ve takip aksiyonunda anlasir.', 'answered', '{"minTurns":2,"maxTurns":4,"language":"tr","persona":"Deniz, son teslim tarihlerini kaciran ekip uyesi","scenario":"Deniz son iki sprintte teslim tarihlerini kacirdi ve toplantilarda daha sessiz.","objective":"Katilimcinin gercekci liderlik gorusmesini tamamlamasini saglamak.","conversationInstructions":"Deniz rolunde kal. Once biraz savunmaci ama is birligine acik ol. Kriterleri aciklama ve puan verme.","allowedTopics":["teslim tarihi","performans","destek","beklenti","takip"],"completionGuidance":"Gozlem, dinleme, beklenti ve takip aksiyonu tamamlaninca bitir.","allowCoaching":false}'::jsonb),
  (15, 'Interaktif iletisim', 'avatar', 3, true, 60, 'AI avatar roleplay sonrasinda katilimcidan gorusmede iyi giden bir noktayi ve degistirmek istedigi bir noktayi soylemesini ister.', 'answered', '{"minTurns":1,"maxTurns":3,"language":"tr","persona":"Liderlik gelisim kocu","scenario":"Katilimci roleplay sonrasi kisa oz degerlendirme yapiyor.","objective":"Katilimcinin oz farkindalik cikarmasini saglamak.","conversationInstructions":"Turkce konus. Kisa sorular sor. Puanlama yapma.","allowedTopics":["oz degerlendirme","geri bildirim","gorusme","gelisim"],"completionGuidance":"Bir guclu nokta ve bir gelisim noktasi geldiginde tamamla.","allowCoaching":true}'::jsonb),
  (16, 'Egitim Sonu Geri Bildirim', 'avatar', 3, true, 60, 'AI avatar katilimciya egitim boyunca fark ettigi ana davranis temasini ozetler ve son bir yansitma sorusu sorar.', 'answered', '{"minTurns":1,"maxTurns":2,"language":"tr","persona":"Liderlik gelisim kocu","scenario":"Katilimci egitim sonu geri bildirime hazirlaniyor.","objective":"Final rapor oncesi kisa yansitma almak.","conversationInstructions":"Turkce konus. Puanlama yapma; final degerlendirme ayri calisir.","allowedTopics":["geri bildirim","liderlik","yansitma","gelisim"],"completionGuidance":"Katilimci kisa yansitma yaptiginda tamamla.","allowCoaching":true}'::jsonb),
  (17, 'Egitim Sonu Geri Bildirim', 'avatar', 3, true, 60, 'AI avatar katilimcidan gercek is ortaminda hemen uygulayacagi davranisi tek cumleyle secmesini ister.', 'answered', '{"minTurns":1,"maxTurns":2,"language":"tr","persona":"Liderlik gelisim kocu","scenario":"Katilimci final davranis secimini yapiyor.","objective":"Tek uygulanabilir davranis sectirmek.","conversationInstructions":"Turkce konus. Somut davranis secmesini iste. Puanlama yapma.","allowedTopics":["uygulama","davranis","liderlik","aksiyon"],"completionGuidance":"Tek net davranis secildiginde tamamla.","allowCoaching":true}'::jsonb),
  (18, 'Egitim Sonu Geri Bildirim icin Aksiyon Listesi/Odev', 'avatar', 4, true, 60, 'AI avatar katilimcidan haftalik aksiyon listesinin ilk taslagini ister: acilis cumlesi, acik soru, beklenti, takip tarihi.', 'answered', '{"minTurns":1,"maxTurns":3,"language":"tr","persona":"Liderlik gelisim kocu","scenario":"Katilimci egitim sonu odevini hazirliyor.","objective":"Uygulanabilir aksiyon listesi taslagi almak.","conversationInstructions":"Turkce konus. Liste belirsizse tarih ve olcut eklet. Puanlama yapma.","allowedTopics":["aksiyon listesi","odev","takip tarihi","acik soru","beklenti"],"completionGuidance":"Aksiyon listesi taslagi geldiginde tamamla.","allowCoaching":true}'::jsonb),
  (19, 'Egitim Sonu Geri Bildirim icin Aksiyon Listesi/Odev', 'avatar', 4, true, 60, 'AI avatar aksiyon listesini netlestirir ve katilimcidan bir sonraki 7 gun icin taahhut cumlesi alir.', 'answered', '{"minTurns":1,"maxTurns":3,"language":"tr","persona":"Liderlik gelisim kocu","scenario":"Katilimci aksiyon listesini son haline getiriyor.","objective":"7 gunluk net taahhut almak.","conversationInstructions":"Turkce konus. Cevabi kisa ve uygulanabilir tutmaya yonlendir. Puanlama yapma.","allowedTopics":["taahhut","aksiyon","odev","takip","liderlik"],"completionGuidance":"Net taahhut cumlesi geldiginde tamamla.","allowCoaching":true}'::jsonb),
  (20, 'Kapanis', 'video', 2, false, 0, 'Video placeholder: Egitim kapanis mesaji burada oynatilacak.', 'viewed', null::jsonb),
  (21, 'Kapanis', 'final', 2, false, 0, 'Video placeholder: Final kapanis. Egitimi bitir butonu raporu tek seferlik final degerlendirme ile olusturur.', 'viewed', null::jsonb)
) as updates(order_index, title, type, estimated_min, avatar_enabled, avatar_budget_sec, prompt, completion_rule, conversation_config)
where public.training_states.module_id = '00000000-0000-0000-0000-000000000501'
  and public.training_states.order_index = updates.order_index;

update public.training_sessions
set
  current_state_id = '00000000-0000-0000-0000-000000000601',
  completed_state_ids = '{}',
  status = 'in_progress',
  completed_at = null,
  updated_at = now(),
  metadata = jsonb_build_object('source', 'leadership_training_21_state_reset')
where module_id = '00000000-0000-0000-0000-000000000501';

update public.session_usage
set
  total_duration_min = 60,
  avatar_target_min = 14,
  avatar_used_min = 0,
  avatar_open_count = 0,
  buffered_avatar_min = 16.1,
  estimated_avatar_cost_usd = 0,
  estimated_total_cost_usd = 0,
  safe_budget_usd = 2.4,
  updated_at = now()
where session_id in (
  select id from public.training_sessions
  where module_id = '00000000-0000-0000-0000-000000000501'
);

update public.session_cost_logs
set provider = 'system'
where session_id in (
  select id from public.training_sessions
  where module_id = '00000000-0000-0000-0000-000000000501'
)
  and provider <> 'system';

create or replace function public.restart_my_latest_training_session()
returns uuid
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  target_session public.training_sessions%rowtype;
  first_state_id uuid;
begin
  select id
  into first_state_id
  from public.training_states
  where module_id = '00000000-0000-0000-0000-000000000501'
  order by order_index asc
  limit 1;

  if first_state_id is null then
    raise exception 'Training has no states.' using errcode = 'P0002';
  end if;

  select *
  into target_session
  from public.training_sessions
  where learner_id = auth.uid()
    and module_id = '00000000-0000-0000-0000-000000000501'
  order by started_at desc
  limit 1;

  if target_session.id is null then
    insert into public.training_sessions (
      enrollment_id,
      module_id,
      template_id,
      learner_id,
      company_id,
      current_state_id,
      completed_state_ids,
      status,
      started_at,
      updated_at,
      completed_at,
      metadata
    )
    select
      enrollment.id,
      enrollment.module_id,
      assignment.template_id,
      enrollment.learner_id,
      enrollment.company_id,
      first_state_id,
      '{}',
      'in_progress',
      now(),
      now(),
      null,
      jsonb_build_object('source', 'learner_restart_created')
    from public.learner_enrollments enrollment
    join public.company_training_assignments assignment
      on assignment.id = enrollment.assignment_id
    where enrollment.learner_id = auth.uid()
      and enrollment.module_id = '00000000-0000-0000-0000-000000000501'
    order by enrollment.assigned_at desc
    limit 1
    returning * into target_session;

    if target_session.id is null then
      raise exception 'No training enrollment found for learner.' using errcode = 'P0002';
    end if;

    insert into public.session_usage (
      session_id,
      total_duration_min,
      avatar_target_min,
      avatar_used_min,
      avatar_open_count,
      buffered_avatar_min,
      estimated_avatar_cost_usd,
      estimated_total_cost_usd,
      safe_budget_usd
    )
    values (
      target_session.id,
      60,
      14,
      0,
      0,
      16.1,
      0,
      0,
      2.4
    )
    on conflict (session_id) do update set
      total_duration_min = excluded.total_duration_min,
      avatar_target_min = excluded.avatar_target_min,
      avatar_used_min = excluded.avatar_used_min,
      avatar_open_count = excluded.avatar_open_count,
      buffered_avatar_min = excluded.buffered_avatar_min,
      estimated_avatar_cost_usd = excluded.estimated_avatar_cost_usd,
      estimated_total_cost_usd = excluded.estimated_total_cost_usd,
      safe_budget_usd = excluded.safe_budget_usd,
      updated_at = now();

    return target_session.id;
  end if;

  delete from public.session_evaluations where session_id = target_session.id;
  delete from public.reports where session_id = target_session.id;
  delete from public.skill_scores where session_id = target_session.id;
  delete from public.session_feedback where session_id = target_session.id;
  delete from public.session_answers where session_id = target_session.id;
  delete from public.session_cost_logs where session_id = target_session.id;
  delete from public.session_event_logs where session_id = target_session.id;

  update public.training_sessions
  set
    current_state_id = first_state_id,
    completed_state_ids = '{}',
    status = 'in_progress',
    completed_at = null,
    started_at = now(),
    updated_at = now(),
    metadata = jsonb_build_object('source', 'learner_restart')
  where id = target_session.id;

  update public.session_usage
  set
    total_duration_min = 60,
    avatar_target_min = 14,
    avatar_used_min = 0,
    avatar_open_count = 0,
    buffered_avatar_min = 16.1,
    stt_minutes = 0,
    tts_characters = 0,
    input_tokens = 0,
    output_tokens = 0,
    estimated_avatar_cost_usd = 0,
    estimated_llm_cost_usd = 0,
    estimated_stt_cost_usd = 0,
    estimated_tts_cost_usd = 0,
    estimated_total_cost_usd = 0,
    safe_budget_usd = 2.4,
    updated_at = now()
  where session_id = target_session.id;

  return target_session.id;
end;
$$;

grant execute on function public.restart_my_latest_training_session() to authenticated;

commit;
