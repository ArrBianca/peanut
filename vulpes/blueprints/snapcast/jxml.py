"""A very small podcast RSS generator. Currently in beta."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from xml.etree import ElementTree as ETree


class JXElement(ETree.Element):
    """Base class for podcast types. Provides sub_element."""

    dt_fmt = "%a, %d %b %Y %H:%M:%S %z"

    def sub_elem(self, name, attrib=None, text=None):
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


# TODO(June): Give examples of what values are important.
# https://github.com/ArrBianca/peanut/issues/22
class FeedItem(JXElement):
    """An ETree Element that represents an `item` tag in a podcast feed."""

    tag = "item"

    def __init__(self,
                 title: str,
                 media_url: str,
                 media_size: int,
                 media_type: str, **kwargs) -> None:
        self.title: str = title
        """The episode's title"""
        self.subtitle: Optional[str] = None
        """A short subtitle, usually shown, smaller, directly below the title."""
        self.description: Optional[str] = None
        """A longer description.

         Accessable from an episode's info page. If a subtitle is not provided
         but a description is, it is used to fill the space. If this is not
         needed, set subtitle to empty explicitly.
         """
        self.uuid: Optional[str | UUID] = None
        """The episode's UUID.

        This is used to identify the episode and should not change. it is
        HIGHLY recommended to set this value. If not supplied, the URL of the
        item's enclosed media will be used instead.
        """

        self.media_url: Optional[str] = media_url
        """URL of the media file."""
        self.media_size: Optional[int] = media_size
        """Size in bytes of the media file."""
        self.media_type: Optional[str] = media_type
        """MIME type of the media file.

        Required, but iTunes ignores this value and uses only the media's file
        extension.
        """

        self.media_duration: Optional[int | timedelta] = None
        """Duration of the media file in seconds."""
        self.pub_date: Optional[datetime] = None
        """Publication date of the episode."""
        self.link: Optional[str] = None
        """URL of an episode-specific page, or any other URL.

        Exposed to the user as a clickable button in some clients.
        """
        self.image: Optional[str] = None
        """URL of the episode's cover art.

        This should be a square jpg or png, and is infuriatingly ignored in
        Apple Podcasts at the time of writing.
        """

        # Does nothing in my tests. Only works at podcast level.
        # self.explicit: Optional[bool] = None
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

        self.itunes_block: bool = False
        """Whether to withhold this episode from appearing in iTunes."""

        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])

        super().__init__(self.tag, {})

    def build(self):
        """Construct and return a podcast-compatible <item> tag."""
        # Check the mandatory attributes.
        for name in ["title", "media_url", "media_size", "media_type"]:
            if getattr(self, name) is None:
                raise ValueError(f"{name} element is required.")

        # TODO(June): Validate.
        # https://github.com/ArrBianca/peanut/issues/21

        # Required elements
        self.sub_elem("title", text=self.title)
        self.sub_elem("enclosure", attrib={
            'url': self.media_url,
            'length': str(self.media_size),
            'type': self.media_type,
        })

        # Simple text fields
        self.sub_elem("itunes:subtitle", text=self.subtitle)
        self.sub_elem("description", text=self.description)
        self.sub_elem("link", text=self.link)
        # TODO(June): Restrict episodeType values
        # https://github.com/ArrBianca/peanut/issues/23
        self.sub_elem("itunes:episodeType", text=self.episode_type)
        self.sub_elem("itunes:season", text=self.season)
        self.sub_elem("itunes:episode", text=self.episode)

        if self.image is not None:
            self.sub_elem("itunes:image", {'href': self.image})
        # self.sub_element("itunes:explicit", text='yes' if self.explicit else 'no')

        # Some troublemakers
        if (md := self.media_duration) is not None:
            self.sub_elem("itunes:duration", text=(int(md.total_seconds())))

        if self.uuid is None:
            self.uuid = self.media_url
        self.sub_elem("guid", {'isPermaLink': "false"}, text=str(self.uuid))

        if (pd := self.pub_date) is not None:
            pd = pd.replace(tzinfo=timezone.utc).strftime(self.dt_fmt)
            self.sub_elem("pubDate", text=pd)

        return self


class PodcastFeed(JXElement):
    """An ETree Element that represents the `channel` tag in a podcast feed."""

    tag = "channel"
    _categories = []

    generator: str = "JXML - The J stands for June!"
    """Indentifier for the feed-generating library."""

    def __init__(self, title: str, description: str,
                 image: str, explicit: bool, **kwargs) -> None:
        self.episodes: list[FeedItem] = []

        # "Required" elements
        self.title = title
        self.description = description
        self.image = image
        """URL pointing to a png or jpg cover image for the podcast feed."""
        self.explicit = explicit

        # Optional
        self.categories = []
        """Category list for the podcast.

        Should be of the form of either:
            - A list of objects with <cat> and [sub] attrs.
            - A list of dicts with <cat> and [sub] keys.
        (`cat` is mandatory if given, `sub` is optional)

        The values of `cat` and `sub` should correspond to the categories and
        subcategories laid out in the Apple Podcasts documentation at
        podcasters.apple.com/support/1691-apple-podcasts-categories`   .
        Pay attention to the rules specified there for string escaping.
        """

        self.author: Optional[str] = None
        """The person or group responsible for creating the show."""
        self.feed_url: Optional[str] = None
        """Self-referencing URL of the feed itself, if known."""
        self.link: Optional[str] = None
        """URL pointing to the website for the podcast."""
        self.copyright: Optional[str] = None
        """A human-readable copyright string."""
        self.language: Optional[str] = None
        """ISO639 two-letter language code."""

        self.last_build_date: Optional[datetime] = None
        """The last time that feed content changed.

        Set this value to current when adding or updating an item or any field
        of the podcast.
        """
        self.itunes_block: Optional[bool] = False
        """Prevent this podcast from appearing in the iTunes directory."""

        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])

        super().__init__("channel", {})

    def build(self, pretty=False) -> str:
        """Construct a podcast RSS feed."""
        root = ETree.Element("rss", {
            'version': "2.0",
            'xmlns:itunes': "http://www.itunes.com/dtds/podcast-1.0.dtd",
            'xmlns:atom': "http://www.w3.org/2005/Atom",
        })
        root.append(self)

        for name in ["title", "description", "image", "explicit"]:
            if getattr(self, name) is None:
                raise ValueError(f"{name} element is required.")

        self.sub_elem("title", text=self.title)
        # Maybe this could stand to be duplicated to itunes:summary?
        self.sub_elem("description", text=self.description)
        if self.image:
            self.sub_elem("itunes:image", {'href': self.image})
        # Okay so the itunes podcast docs straight up lie. It says explicit
        # should be true or false, but it only accepts yes and no. How dare.
        self.sub_elem("itunes:explicit", text='yes' if self.explicit else 'no')

        # Then the simple text-only elems:
        self.sub_elem("itunes:author", text=self.author)
        self.sub_elem("copyright", text=self.copyright)
        self.sub_elem("link", text=self.link)
        self.sub_elem("language", text=self.language)
        self.sub_elem("itunes:block", text="yes" if self.itunes_block else None)

        # Category processing.
        # TODO(June): clean this up lol.
        for category in self.categories:
            try:
                cat = self.sub_elem("itunes:category", {'text': category.cat})
                if cat is not None and hasattr(category, 'sub') and category.sub is not None:
                    ETree.SubElement(cat, "itunes:category", {'text': category.sub})
            except AttributeError:
                cat = self.sub_elem("itunes:category", {'text': category['cat']})
                if cat is not None and 'sub' in category and category['sub'] is not None:
                    ETree.SubElement(cat, "itunes:category", {'text': category.sub})

        # Now relevant RSS elements brought forward:
        if (lbd := self.last_build_date) is None:
            lbd = datetime.now(timezone.utc)
        else:
            lbd = lbd.replace(tzinfo=timezone.utc).strftime(self.dt_fmt)
        self.sub_elem("lastBuildDate", text=lbd)
        self.sub_elem("generator", text=self.generator)

        # Atom self-link
        if self.feed_url is not None:
            self.sub_elem("atom:link", {
                'href': self.feed_url,
                'rel': 'self',
                'type': 'text/xml',
            })

        # Episode time!
        for episode in self.episodes:
            self.append(episode.build())

        if pretty:
            ETree.indent(root)
        return ETree.tostring(root, encoding='unicode', xml_declaration=True) + '\n'
