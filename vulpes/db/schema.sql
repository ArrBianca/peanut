drop table if exists peanut_files;
drop table if exists podcast;
drop table if exists episode;
drop table if exists person;

create table peanut_files
(
    filename    TEXT,
    size        INT,
    origin_name TEXT,
    tstamp      INT
);

create table podcast
(
    uuid                 TEXT    not null,
    name                 TEXT    not null,
    website              TEXT    not null,
    description          TEXT    not null,
    explicit             integer not null,
    image                TEXT    not null,
    author_name          TEXT    not null,
    copyright            TEXT,
    language             TEXT default 'en-US',
    feed_url             TEXT,
    category             TEXT,
    withhold_from_itunes integer default 0,
    auth_token           TEXT    not null,
    last_modified        TEXT
);

create table episode
(
    id             integer primary key asc,
    uuid           TEXT,
    podcast_uuid   TEXT,
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
    episode_art    TEXT,
    FOREIGN KEY (podcast_uuid) REFERENCES podcast (uuid),
    constraint title_summary_check
        check ((title NOTNULL) OR (summary NOTNULL))
);

create table person
(
    id      integer primary key asc,
    name    text,
    email   text,
    constraint person_name_email_check
        check ((name NOTNULL) OR (email NOTNULL))
)
