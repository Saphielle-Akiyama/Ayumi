CREATE TABLE IF NOT EXISTS anime_reminders (
    user_id bigint NOT NULL,
    trigger_time timestamp with time zone NOT NULL,
    anime_name text NOT NULL,
    message_url text NOT NULL
    );

