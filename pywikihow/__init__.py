import bs4
from pywikihow.exceptions import ParseError, UnsupportedLanguage
from datetime import timedelta
from requests_cache import CachedSession

expire_after = timedelta(hours=1)
session = CachedSession(backend='memory', expire_after=expire_after)


def get_html(url):
    headers = {
        'User-Agent': "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:41.0) Gecko/20100101 Firefox/41.0"}
    r = session.get(url, headers=headers)
    html = r.text.encode("utf8")
    return html


class HowToStep:
    def __init__(self, number, summary=None, description=None, picture=None, html=""):
        self._number = number
        self._summary = summary
        self._description = description
        self._picture = picture
        self.html = html

    @property
    def number(self):
        return self._number

    @property
    def summary(self):
        return self._summary

    @property
    def description(self):
        return self._description

    @property
    def picture(self):
        return self._picture

    def as_dict(self):
        return {"number": self.number,
                "summary": self.summary,
                "description": self.description,
                "picture": self.picture}

    def print(self, extended=False):
        print(self.number, "-", self.summary)
        if extended:
            print(self.description)


class HowTo:
    def __init__(self, url="http://www.wikihow.com/Special:Randomizer",
                 lazy=True, html=""):
        self._url = url
        self._title = None
        self._html = html
        self._intro = None
        self._steps = []
        self._parsed = False
        if not lazy:
            self._parse()

    def __repr__(self):
        return "HowTo:" + self.title

    @property
    def url(self):
        if not self._parsed:
            self._parse()
        return self._url

    @property
    def title(self):
        if not self._parsed:
            self._parse()
        return self._title

    @property
    def intro(self):
        if not self._parsed:
            self._parse()
        return self._intro

    @property
    def steps(self):
        if not self._parsed:
            self._parse()
        return self._steps

    @property
    def summary(self):
        summary = self.title + "\n"
        for step in self.steps:
            summary += "{n} - ".format(n=step.number) + step.summary + "\n"
        return summary

    @property
    def n_steps(self):
        return len(self._steps)

    def print(self, extended=False):
        if not extended:
            print(self.summary)
        else:
            print(self.title)
            print(self.intro)
            for s in self.steps:
                s.print(extended)

    def _parse_title(self, soup):
        # get title
        html = soup.findAll("h1",
                            {"class": ["title_lg", "title_md", "title_sm"]})[0]
        if not html.find("a"):
            raise ParseError
        else:
            self._url = html.find("a").get("href")
            if not self._url.startswith("http"):
                self._url = "http://" + self._url
            self._title = self._url.split("/")[-1].replace("-", " ")

    def _parse_intro(self, soup):
        # get article intro/summary
        intro_html = soup.find("div", {"class": "mf-section-0"})
        if not intro_html:
            raise ParseError
        else:
            super = intro_html.find("sup")
            if super != None:
                for sup in intro_html.findAll("sup"):
                    sup.decompose()
                    intro = intro_html.text
                    self._intro = intro.strip()
            else:
                intro = intro_html.text
                self._intro = intro.strip()

    def _parse_steps(self, soup):
        self._steps = []
        step_html = soup.findAll("div", {"class": "step"})
        count = 0
        for html in step_html:
            # This finds and cleans weird tags from the step data
            super = html.find("sup")
            script = html.find("script")
            if script != None:
                for script in html.findAll("script"):
                    script.decompose()
            if super != None:
                for sup in html.findAll("sup"):
                    sup.decompose()
            count += 1
            summary = html.find("b").text

            for _extra_div in html.find("b").find_all("div"):
                summary = summary.replace(_extra_div.text, "")

            step = HowToStep(count, summary)
            ex_step = html
            for b in ex_step.findAll("b"):
                b.decompose()
            step._description = ex_step.text.strip()
            self._steps.append(step)

    def _parse_pictures(self, soup):
        # get step pic
        count = 0
        for html in soup.findAll("a", {"class": "image"}):
            # one more ugly blob, nice :D
            html = html.find("img")
            i = str(html).find("data-src=")
            pic = str(html)[i:].replace('data-src="', "")
            pic = pic[:pic.find('"')]

            # save in step
            self._steps[count]._picture = pic
            count += 1

    def _parse(self):
        try:
            html = self.html
            soup = bs4.BeautifulSoup(html, 'html.parser')
            self._parse_title(soup)
            self._parse_intro(soup)
            self._parse_steps(soup)
            self._parse_pictures(soup)
            self._parsed = True
        except Exception as e:
            raise ParseError

    def as_dict(self):
        return {
            "title": self.title,
            "url": self._url,
            "intro": self._intro,
            "n_steps": len(self.steps),
            "steps": [s.as_dict() for s in self.steps]
        }


def RandomHowTo(lang="en"):
    lang = lang.split("-")[0].lower()
    if lang not in WikiHow.lang2url:
        raise UnsupportedLanguage
    url = WikiHow.lang2url[lang] + "Special:Randomizer"
    return HowTo(url)


class WikiHow:
    lang2url = {
        "en": "http://www.wikihow.com/",
        "es": "http://es.wikihow.com/",
        "pt": "http://pt.wikihow.com/",
        "it": "http://www.wikihow.it/",
        "fr": "http://fr.wikihow.com/",
        "ru": "http://ru.wikihow.com/",
        "de": "http://de.wikihow.com/",
        "zh": "http://zh.wikihow.com/",
        "nl": "http://nl.wikihow.com/",
        "cz": "http://www.wikihow.cz/",
        "id": "http://id.wikihow.com/",
        "jp": "http://www.wikihow.jp/",
        "hi": "http://hi.wikihow.com/",
        "th": "http://th.wikihow.com/",
        "ar": "http://ar.wikihow.com/",
        "ko": "http://ko.wikihow.com/",
        "tr": "http://www.wikihow.com.tr/",
        "vn": "http://www.wikihow.vn/",
    }

    @staticmethod
    def search(search_term, max_results=-1, lang="en"):
        lang = lang.split("-")[0].lower()
        if lang not in WikiHow.lang2url:
            raise UnsupportedLanguage
        search_url = WikiHow.lang2url[lang] + \
                     "wikiHowTo?search=" + search_term.replace(" ", "+")
        html = get_html(search_url)
        soup = bs4.BeautifulSoup(html, 'html.parser').findAll('a', attrs={
            'class': "result_link"})
        count = 1
        for link in soup:
            url = link.get('href')
            if not url.startswith("http"):
                url = "http://" + url
            how_to = HowTo(url)
            try:
                how_to._parse()
            except ParseError:
                continue
            yield how_to
            count += 1
            if 0 < max_results < count:
                return


def search_wikihow(query, max_results=10, lang="en"):
    return list(WikiHow.search(query, max_results, lang))


if __name__ == "__main__":
    how = RandomHowTo("it")
    how.print()

    for how_to in WikiHow.search("comprar bitcoin", lang="pt"):
        how_to.print()
        break

    for how_to in WikiHow.search("buy bitcoin"):
        how_to.print()
        break
