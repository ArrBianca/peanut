create table episode
(
    id             integer
        constraint episode_pk
            primary key autoincrement,
    podcast_id     integer
        constraint episode_podcast_id_fk
            references podcast,
    episode_uuid   TEXT,
    title          TEXT,
    summary        TEXT,
    subtitle       TEXT,
    long_summary   TEXT,
    media_url      TEXT,
    media_size     INTEGER,
    media_type     TEXT,
    media_duration INTEGER,
    pub_date       TEXT,
    link           TEXT,
    constraint title_summary_check
        check ((title NOTNULL) OR (summary NOTNULL))
);

