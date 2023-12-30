ADD_EPISODE = """
    INSERT INTO episode (podcast_uuid, title, subtitle, uuid, media_url,
                         media_size, media_type, media_duration, pub_date, link)
    VALUES (:podcast_uuid, :title, :subtitle, :uuid, :media_url,
            :media_size, :media_type, :media_duration, :pub_date, :link)"""
INSERT_EPISODE = """
    INSERT INTO episode (podcast_uuid, uuid, title, media_url, media_size, media_type, media_duration, pub_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
DELETE_EPISODE_BY_UUID = """DELETE FROM episode WHERE podcast_uuid=? AND uuid=?"""
SELECT_EPISODE_LATEST = """SELECT * FROM episode WHERE podcast_uuid=? ORDER BY id DESC LIMIT 1"""
SELECT_EPISODE_BY_ID = """SELECT * FROM episode WHERE podcast_uuid=? AND id=?"""
SELECT_EPISODE_BY_UUID = """SELECT * FROM episode WHERE podcast_uuid=? AND uuid=?"""
SELECT_PODCAST_AUTH_KEY = """SELECT auth_token FROM podcast WHERE uuid=?"""
SELECT_PODCAST_BY_UUID = """SELECT * FROM podcast WHERE uuid=?"""
SELECT_PODCAST_EPISODES = """SELECT * FROM episode WHERE podcast_uuid=?"""  # noqa: E501
LAST_MODIFIED_PATTERN = "%a, %d %b %Y %H:%M:%S %Z"
