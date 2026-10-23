"""Pre-launch smoke checks for a static, third-party hosted checkout site."""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://fahremback.github.io/clockwork-museum-escape-kit/"
EXPECTED = {
    "starter": ("https://payhip.com/buy?link=WZegu", "6.99"),
    "complete": ("https://payhip.com/buy?link=BNgAl", "14.99"),
}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors = []
        self.images = []
        self.ids = set()
        self.headings = []
        self.metas = {}
        self.links = []
        self.inline_json = []
        self.in_json = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "a":
            self.anchors.append(attrs)
        elif tag == "img":
            self.images.append(attrs)
        elif tag == "meta":
            self.metas[attrs.get("name") or attrs.get("property")] = attrs.get("content")
        elif tag == "link":
            self.links.append(attrs)
        elif re.fullmatch(r"h[1-6]", tag):
            self.headings.append(tag)
        elif tag == "script" and attrs.get("type") == "application/ld+json":
            self.in_json = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_json = False

    def handle_data(self, data):
        if self.in_json:
            self.inline_json.append(data)


class LaunchChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.page = Page()
        cls.page.feed(cls.raw)

    def test_checkout_links_require_no_javascript(self):
        found = {a.get("data-edition"): a for a in self.page.anchors
                 if a.get("data-edition")}
        self.assertEqual(set(found), set(EXPECTED))
        for edition, (expected, _) in EXPECTED.items():
            self.assertEqual(found[edition]["href"], expected)
            self.assertEqual(urlsplit(expected).hostname, "payhip.com")
            self.assertIn("Buy", found[edition].get("aria-label", ""))
        self.assertNotIn("CHECKOUT_LINKS", self.raw)

    def test_accessibility_basics(self):
        self.assertEqual(self.page.headings.count("h1"), 1)
        self.assertIn("top", self.page.ids)
        self.assertIn("skip-link", self.raw)
        self.assertIn(":focus-visible", self.raw)
        for a in self.page.anchors:
            if a.get("href", "").startswith("#"):
                self.assertIn(a["href"][1:], self.page.ids)
        for img in self.page.images:
            self.assertTrue(img.get("alt"), img)
            self.assertGreater(int(img.get("width", 0)), 0, img)
            self.assertGreater(int(img.get("height", 0)), 0, img)
            self.assertTrue((ROOT / img["src"]).is_file())

    def test_product_structured_data_matches_visible_offers(self):
        graph = json.loads("".join(self.page.inline_json))["@graph"]
        products = [item for item in graph if item["@type"] == "Product"]
        self.assertEqual(len(products), 2)
        expected_offers = {p: price for p, (_, price) in EXPECTED.items()}
        for p in products:
            sku = p["@id"].split("#")[-1]
            self.assertIn(sku, EXPECTED)
            self.assertEqual(p["offers"]["priceCurrency"], "USD")
            self.assertEqual(p["offers"]["price"], expected_offers[sku])
            self.assertIn(expected_offers[sku], self.raw)
            self.assertNotIn("aggregateRating", p)
            self.assertNotIn("availability", p["offers"])

    def test_search_and_social_metadata(self):
        self.assertGreater(len(self.page.metas["description"]), 95)
        self.assertLessEqual(len(self.page.metas["description"]), 165)
        self.assertIn("https://" ,self.page.metas["og:image"])
        self.assertIn("https://" ,self.page.metas["twitter:image"])
        self.assertTrue((ROOT / "assets/share.jpg").is_file())
        self.assertTrue(any(x.get("rel") == "canonical" and x.get("href") == SITE_URL
                            for x in self.page.links))
        xml = ElementTree.parse(ROOT / "sitemap.xml")
        self.assertEqual(
            xml.find("{http://www.sitemaps.org/schemas/sitemap/0.9}url/"
                     "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text, SITE_URL)
        self.assertIn("Sitemap: " + SITE_URL + "sitemap.xml",
                      (ROOT / "robots.txt").read_text())

    def test_no_credentials_or_private_deliverables_in_public_site(self):
        self.assertNotRegex(self.raw, r"(?:sk|rk)_(?:test|live)_[A-Za-z0-9]{12,}")
        self.assertFalse(list(ROOT.rglob("*.pdf")))
        self.assertFalse(list(ROOT.rglob("*.zip")))

    def test_optimized_images(self):
        self.assertIn('src="assets/cover.webp"', self.raw)
        self.assertLess((ROOT / "assets/cover.webp").stat().st_size, 450_000)
        self.assertLess((ROOT / "assets/share.jpg").stat().st_size, 650_000)
        self.assertLess((ROOT / "assets/favicon.png").stat().st_size, 30_000)


if __name__ == "__main__":
    unittest.main()
