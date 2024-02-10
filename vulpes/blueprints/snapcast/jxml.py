"""A very small podcast RSS generator. Currently in beta."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from xml.etree import ElementTree as ETree

mime_lookup = {
    ".m4a": "audio/x-m4a",
    ".mp3": "audio/mpeg",
    ".mov": "video/quicktime",
    ".mp4": "video/mp4",  # mp4 files should only be used for video.
    ".m4v": "video/x-m4v",
    ".pdf": "application/pdf",  # Why does itunes support pdf podcasts?
}


class JXElement(ETree.Element):
    """Base class for podcast types. Provides sub_element."""

    dt_fmt = "%a, %d %b %Y %H:%M:%S %z"

    def sub_elem(self,
                 name: str,
                 text: Optional[str | int] = None,
                 attrib: Optional[dict] = None,
    ):
        """Add a sub-element to the current element and return it.

        :param name: The tag name of the child.
        :param attrib: A dict of attributes for the child.
        :param text: The text for the child.
        """
        if attrib is None and text is None:
            return None
        if attrib is None:
            attrib = {}
        sub = ETree.SubElement(self, name, attrib=attrib)
        if text is not None:
            sub.text = str(text)
        return sub


class FeedItem(JXElement):
    """An ETree Element that represents an `item` tag in a podcast feed.

    There are many available options, but some are more important than others.
    In approximate order of importance:

    * ``title``, ``uuid``, ``pub_date``, and all three enclosure values are
      the absolute bare minimum, and are thus required in the constructor.
    * Following those, ``media_duration`` should be populated with the
      length in seconds of the item's media.
    * If the podcast is a Serial type, ``episode_type`` and ``episode`` should
      be set for all items. If the serial is a single season, the ``season``
      element MAY be omitted. Clients often hide the season selector if this is
      the case, for a cleaner look for one-season podcasts.
    * ``subtitle`` is rendered in most clients in the episode list underneath
      the episode title, and is recommended. It should be quite short. Episode
      listings often don't look quite right unless the space is filled.
    * ``description`` appears on its own episode info screen and can be quite
      long. Fill this with show notes or any other associated text content. If
      a subtitle is not provided but a description is, it is used to fill the
      space.
    * In some but not all clients, ``link`` is shown on the episode detail page
      as a tappable button to a single URL of your choice. Intended for the
      blog page associated with a podcast episode; you can use it for whatever.
    * ``image`` points to a cover art file for the episode. Support for this
      varies **wildly** between clients. For best results, if you have episode
      art, you should both set this and embed the image in the audio file. Even
      then, it's not guaranteed that it will be shown. It sucks.
    * And finally ``itunes_block`` specifies that this episode should not be
      displayed in Apple Podcasts. They say it's for episodes against their
      guidelines, to prevent the whole feed from being removed.
    """

    tag = "item"

    def __init__(self,
                 title: str,
                 media_url: str,
                 media_size: int,
                 media_type: str,
                 pub_date: datetime,
                 uuid: UUID | str,
                 **kwargs,
    ) -> None:
        self.title: str = title
        """The episode's title"""
        self.media_url: str = media_url
        """URL of the media file."""
        self.media_size: int = media_size
        """Size in bytes of the media file."""
        self.media_type: str = media_type
        """MIME type of the media file.


        Required, but iTunes ignores this value and uses only the media's file
        extension.
        """
        self.pub_date: datetime = pub_date
        """Publication date of the episode."""
        self.uuid: UUID | str = uuid
        """The episode's UUID.

        This is used to identify the episode and should not change. it is
        HIGHLY recommended to set this value. If not supplied, the URL of the
        item's enclosed media will be used instead.
        """

        self.media_duration: Optional[timedelta] = None
        """Duration of the media file in seconds."""

        self.episode_type: Optional[str] = None
        """String identifying the type of episode.

        Either 'full', 'trailer', or 'bonus'.
        """
        self.season: Optional[str | int] = None
        """The season number of the episode.

        A serial show containing exactly one unnumbered season (season tag
        ommitted) is often shown without an otherwise redundant season
        selector in apps. Consider leaving this out if your podcast has
        numbered episodes but only one season."""
        self.episode: Optional[str | int] = None
        """The episode number.

        Used for sorting `serial` shows. The value is recorded and shown in
        certain places for episodic shows but does not influence sorting.

        Bonus episodes tied to a particular episode should be given episodeType
        of `bonus` and the same episode number. Apple Podcasts shows this
        correctly, Pocket Casts does not.

        Bonus episodes attached to the show as a whole should not be numbered.
        Ditto as above for correct portrayal.
        """

        self.subtitle: Optional[str] = None
        """A short subtitle, usually shown smaller directly below the title."""

        # Maybe should also copy this value to itunes:summary?
        self.description: Optional[str] = None
        """A longer description. """

        self.link: Optional[str] = None
        """URL of an episode-specific page, or any other URL."""

        self.image: Optional[str] = None
        """URL of the episode's cover art.

        This should be a square jpg or png, and is infuriatingly ignored in
        Apple Podcasts at the time of writing.
        """

        # Does nothing in my tests. Only works at podcast level.
        # self.explicit: Optional[bool] = None

        self.itunes_block: bool = False
        """Whether to withhold this episode from appearing in iTunes."""

        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])

        super().__init__(self.tag, {})

    def build(self):
        """Construct and return a podcast-compatible <item> tag."""
        # Required elements
        self.sub_elem("title", self.title)
        self.sub_elem("enclosure", attrib={
            "url": self.media_url,
            "length": str(self.media_size),
            "type": self.media_type,
        })
        self.sub_elem("pubDate", self.pub_date.strftime(self.dt_fmt))

        if self.uuid is None:
            self.uuid = self.media_url
        self.sub_elem("guid", str(self.uuid), {"isPermaLink": "false"})

        # Simple text fields
        self.sub_elem("itunes:episodeType", self.episode_type)
        self.sub_elem("itunes:season", self.season)
        self.sub_elem("itunes:episode", self.episode)
        self.sub_elem("itunes:subtitle", self.subtitle)
        self.sub_elem("description", self.description)
        self.sub_elem("link", self.link)

        if self.image is not None:
            self.sub_elem("itunes:image", attrib={"href": self.image})

        # IME, apple podcats does not respect this tag at an episode level.
        # self.sub_element("itunes:explicit",
        #                  text="yes" if self.explicit else "no")

        if (md := self.media_duration) is not None:
            self.sub_elem("itunes:duration", int(md.total_seconds()))

        return self


class PodcastFeed(JXElement):
    """An ETree Element that represents the `channel` tag in a podcast.

    There are many available options, but some are more important than
    others. In approximate order of importance:

    * ``title``, ``description``, and ``link`` are vital. ``link`` is a URL to
      the website hosting the podcast or the feed's homepage.
    * ``image`` is the URL to the podcasts's cover art. Apple Podcasts says it
      should be a png or jpg between 1400 and 3000 px square. Transparency is
      very likely not handled well or at all. Probably keep it smaller for
      convenience. The feed validators always yell at me for my 2MB cover art.
    * If applicable, ``is_serial`` should be set. Clients change episode
      handling behavior, generally splitting shows into seasons (based on
      fields set at the episode level) and defaulting to presenting the
      episodes in an oldest-to-newest ordering. If ``is_serial`` is set to
      True, all episodes must be numbered.
    * ``author`` is the group or person responsible for creating the show. In
      podcast clients, this is shown near the title and can name a person or
      group or company etc.
    * iTunes lists ``explicit`` as required, but treats a missing tag as a `no`
      so it's all good. Set this if the podcast contains adult language. As
      an aside, the documentation straight up lies about the values accepted.
      The spec's `true` and `false` don't do `anything`!! You have to fill the
      tag with `yes` or `no`! Why!
    * ``categories`` is a list of up to three sets of Category and Subcategory
      as laid out on the `Apple podcasts article here.
      <https://podcasters.apple.com/support/1691-apple-podcasts-categories>`_
      Check the code below for how to pass these values into the generator.
    * ``last_build_date`` represents the last time that feed content changed.
      Set this value in your database to the current time when adding or
      updating an item or any field of the podcast.
    * To allegedly improve caching, ``feed_url`` should be set to the same URL
      the feed is being accessed at.
    * ``copyright`` is a human-readable string with copyright info for the
      podcast. As usual, you don't need to specifically claim copyright to have
      your work protected. Still useful for completeness or to release the
      show under a more permissive license.
    * ``language``, (default ``en``) is the ISO639 two-letter language code of
      the primary spoken language used in the podcast.
    * ``itunes_block`` prevents toe feed from being added to the Apple Podcasts
      directory.
    * If you're moving your feed to a new location, set ``new_feed_url`` on
      your previous location, and leave it up for some time. Apple Podcasts
      will migrate subscribers automatically. Unknown if any other clients
      honor this option, or if it still functions for podcasts that are
      withheld from the directory.
    * And finally, if you're `absolutely` certain that the feed will never
      again be updated, set ``complete`` to True. Specifying this indicates,
      at least to Apple Podcasts (maybe others. unknown.) that they should stop
      checking the feed for updates. Setting this is PROBABLY NOT WORTH IT.
    """

    tag = "channel"
    _categories = []

    generator: str = "JXML - The J stands for June!"
    """Indentifier for the feed-generating library."""

    def __init__(self,
                 title: str,
                 description: str,
                 link: str,
                 **kwargs,
    ) -> None:
        self.episodes: list[FeedItem] = []

        # "Required" elements
        self.title: str = title
        self.description: str = description
        self.link: str = link
        """URL pointing to the website for the podcast."""

        self.image: Optional[str] = None
        """URL pointing to a png or jpg cover image for the podcast feed."""
        self.is_serial: bool = False
        """Whether the podcast is a serial type."""
        self.author: Optional[str] = None
        """The person or group responsible for creating the show."""
        self.explicit: Optional[bool] = None
        """Whether the podcast contains adult content."""

        self.categories: list = []
        """Category list for the podcast.

        Should be of the form of either:
            - A list of objects with <cat> and [sub] attrs.
            - A list of dicts with <cat> and [sub] keys.
        (`cat` is mandatory, `sub` may be None)

        The values of `cat` and `sub` should correspond to the categories and
        subcategories laid out in the Apple Podcasts documentation `Here
        <https://podcasters.apple.com/support/1691-apple-podcasts-categories>`_.
        Pay attention to the rules specified there for string escaping.
        """

        self.last_build_date: Optional[datetime] = None
        """The last time that feed content changed.

        Set this value to current when adding or updating an item or any field
        of the podcast.
        """

        self.feed_url: Optional[str] = None
        """Self-referencing URL of the feed itself, if known."""
        self.copyright: Optional[str] = None
        """A human-readable copyright string."""
        self.language: Optional[str] = "en"
        """ISO639 two-letter language code."""

        self.itunes_block: Optional[bool] = False
        """Prevent this podcast from appearing in the iTunes directory."""
        self.new_feed_url: Optional[str] = None
        """URL of a replacement RSS feed for this podcast. Careful."""
        self.complete: Optional[bool] = False
        """Flag marking the feed as complete. VERY CAREFUL."""

        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])

        super().__init__("channel", {})

    def build(self, pretty=False) -> str:
        """Construct a podcast RSS feed."""
        root = ETree.Element("rss", {
            "version": "2.0",
            "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
            "xmlns:atom": "http://www.w3.org/2005/Atom",
            "xmlns:podcast": "https://podcastindex.org/namespace/1.0",
        })
        root.append(self)

        # Required fields.
        self.sub_elem("title", self.title)
        # Maybe this could stand to be duplicated to itunes:summary?
        self.sub_elem("description", self.description)
        if self.image:
            self.sub_elem("itunes:image", attrib={"href": self.image})

        # Then the simple text-only elems:
        self.sub_elem("itunes:author", self.author)
        self.sub_elem("copyright", self.copyright)
        self.sub_elem("link", self.link)
        self.sub_elem("language", self.language)
        self.sub_elem("itunes:new-feed-url", self.new_feed_url)
        self.sub_elem("itunes:block", "Yes" if self.itunes_block else None)
        self.sub_elem("itunes:complete", "Yes" if self.complete else None)
        self.sub_elem("itunes:type",
                      "serial" if self.is_serial else "episodic")
        # Okay so the itunes podcast docs straight up lie. It says explicit
        # should be true or false, but it only accepts yes and no. How dare.
        self.sub_elem("itunes:explicit", "yes" if self.explicit else "no")

        # Category processing. Accept dicty object for convenience :)
        for category in self.categories:
            cat = sub = None

            if hasattr(category, "cat") and hasattr(category, "sub"):
                cat = category.cat
                sub = category.sub
            elif "cat" in category and "sub" in category:
                cat = category["cat"]
                sub = category["sub"]

            cat_tag = self.sub_elem("itunes:category", attrib={"text": cat})
            if cat_tag is not None and sub is not None:
                ETree.SubElement(cat_tag, "itunes:category", {"text": sub})

        # Now relevant RSS elements brought forward:
        if (lbd := self.last_build_date) is None:
            lbd = datetime.now(timezone.utc)
        self.sub_elem("lastBuildDate", lbd.strftime(self.dt_fmt))
        self.sub_elem("generator", self.generator)

        # Atom self-link
        if self.feed_url is not None:
            self.sub_elem("atom:link", attrib={
                "href": self.feed_url,
                "rel": "self",
                "type": "application/rss+xml",
            })

        # Episode time!
        for episode in self.episodes:
            self.append(episode.build())

        if pretty:
            ETree.indent(root)
        return ETree.tostring(root, encoding="unicode", xml_declaration=True)
