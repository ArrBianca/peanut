CREATE TABLE podcast
(
    id          integer not null
        constraint podcast_pk
            primary key autoincrement,
    name        TEXT    not null,
    website     TEXT    not null,
    description TEXT    not null,
    explicit    integer not null,
    image       TEXT    not null,
    copyright   TEXT,
    language    TEXT default 'en-US',
    feed_url    TEXT,
    category    TEXT
)