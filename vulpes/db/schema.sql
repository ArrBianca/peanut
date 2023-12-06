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
    id                   integer primary key asc,
    feed_id              TEXT    not null,
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
    withhold_from_itunes integer default 0
);

create table episode
(
    id             integer primary key asc,
    podcast_id     integer,
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
    FOREIGN KEY (podcast_id) REFERENCES podcast (id),
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
