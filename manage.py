#!/usr/bin/env python3
import os
import pathlib
from urllib.parse import urljoin
from hashlib import md5

import click
import requests
from bs4 import BeautifulSoup
from ebooklib import epub

DATA_DIR = pathlib.Path.cwd() / 'data'
BOOKS = {
    1: {
        'ordinal': 1,
        'title': 'The Eye of the World',
        'url': 'https://wot.fandom.com/wiki/The_Eye_of_the_World',
    },
    2: {
        'ordinal': 2,
        'title': 'The Great Hunt',
        'url': 'https://wot.fandom.com/wiki/The_Great_Hunt',
    },
    3: {
        'ordinal': 3,
        'title': 'The Dragon Reborn',
        'url': 'https://wot.fandom.com/wiki/The_Dragon_Reborn',
    },
    4: {
        'ordinal': 4,
        'title': 'The Shadow Rising',
        'url': 'https://wot.fandom.com/wiki/The_Shadow_Rising',
    },
    5: {
        'ordinal': 5,
        'title': 'The Fires of Heaven',
        'url': 'https://wot.fandom.com/wiki/The_Fires_of_Heaven',
    },
    6: {
        'ordinal': 6,
        'title': 'Lord of Chaos',
        'url': 'https://wot.fandom.com/wiki/Lord_of_Chaos',
    },
    7: {
        'ordinal': 7,
        'title': 'A Crown of Swords',
        'url': 'https://wot.fandom.com/wiki/A_Crown_of_Swords',
    },
    8: {
        'ordinal': 8,
        'title': 'The Path of Daggers',
        'url': 'https://wot.fandom.com/wiki/The_Path_of_Daggers',
    },
}


def _get_book_dir_name(num):
    book = BOOKS[num]
    return DATA_DIR / f"{num:02d}_{book['title'].replace(' ', '-')}"


def _save_chapter(book_dir, name, content):
    pass


def _get_chapter_urls(book_url):
    res = requests.get(book_url)
    if res.status_code != 200:
        click.echo(f'Unable to get chapter urls for book {book_url}: {res.status_code}')
    else:
        soup = BeautifulSoup(res.content, 'html.parser')
        anchors = soup.select(
            'div.WikiaSiteWrapper div.WikiaPage div.WikiaPageContentWrapper div.article-with-rail '
            'article#WikiaMainContent.WikiaMainContent div#WikiaMainContentContainer.WikiaMainContentContainer '
            'div#content.WikiaArticle div#mw-content-text.mw-content-ltr div.mw-parser-output div.noprint table tbody '
            'tr td table.collapsible'
        )[0].find_all('a')
        return [
            urljoin(book_url, a['href'])
            for a in anchors
        ]


def _parse_chapter(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    for anchor in soup.find_all('a'):
        anchor.unwrap()

    role = soup.find('h1', attrs={'id': 'firstHeading'}).text.split('/')[-1]
    title = soup.select(
        'div.WikiaSiteWrapper div.WikiaPage div.WikiaPageContentWrapper div.article-with-rail '
        'article#WikiaMainContent.WikiaMainContent div#WikiaMainContentContainer.WikiaMainContentContainer '
        'div#content.WikiaArticle div#mw-content-text.mw-content-ltr div.mw-parser-output table tbody tr td strong big '
        'em'
    )[0].text
    setting = soup.select(
        'div.WikiaSiteWrapper div.WikiaPage div.WikiaPageContentWrapper div.article-with-rail '
        'article#WikiaMainContent.WikiaMainContent div#WikiaMainContentContainer.WikiaMainContentContainer '
        'div#content.WikiaArticle div#mw-content-text.mw-content-ltr div.mw-parser-output table tbody tr td small'
    )[0]
    summary_elements = soup.select(
        'div.WikiaSiteWrapper div.WikiaPage div.WikiaPageContentWrapper div.article-with-rail '
        'article#WikiaMainContent.WikiaMainContent div#WikiaMainContentContainer.WikiaMainContentContainer '
        'div#content.WikiaArticle div#mw-content-text.mw-content-ltr div.mw-parser-output'
    )[0].find_all(['p', 'dl'], recursive=False)
    foot_notes = soup.find('span', attrs={'class': 'references-small'})
    summary_elements = [
        f"<h1>{role}: {title}</h1>",
        f"<p>{setting}</p>",
    ] + [
        element
        for element in summary_elements
        if 'External summary' not in str(element)
    ]
    if foot_notes:
        summary_elements.append('<h2>Notes</h2>')
        summary_elements.append(foot_notes)
    summary = '\n'.join(map(str, summary_elements))
    return role, title, summary


def _grab_book(book, dst_dir):
    chapter_urls = _get_chapter_urls(book['url'])
    for i, url in enumerate(chapter_urls):
        res = requests.get(url)
        if res.status_code != 200:
            click.echo(f'Unable to get chapter for {book["title"]} from {url}: {res.status_code}')
        else:
            role, title, summary = _parse_chapter(res.content)
            chapter_name = f"{i:02d}_{role.replace(' ', '-')}_{title.replace(' ', '-')}.html"
            with open(str(dst_dir / chapter_name), 'w') as f:
                f.write(summary)


def _create_epub(book, src_dir):
    lang = 'en'
    ebook = epub.EpubBook()
    ebook.set_identifier(md5(book['title'].encode()).hexdigest())
    ebook.set_title(book['title'])
    ebook.set_language(lang)
    ebook.add_author('Wheel of Time WIKI')
    ebook.add_metadata('DC', 'description', f"Summary of Book {book['ordinal']} of the Wheel of Time Series")

    chapters = []
    for chap_file in sorted(src_dir.glob('*.html')):
        tokens = [t.replace('-', ' ') for t in chap_file.stem.split('_')]
        chap_args = {
            'title': f"{tokens[1]}: {tokens[2]}",
            'file_name': f"{chap_file.stem}.xhtml",
            'lang': lang,
        }
        chapter = epub.EpubHtml(**chap_args)
        chapter.content = chap_file.read_text()
        ebook.add_item(chapter)
        chapters.append(chapter)

    ebook.toc = ((chapters))
    ebook.spine = chapters

    ncx = epub.EpubNcx()
    ebook.add_item(ncx)
    nav = epub.EpubNav()
    ebook.add_item(nav)
    ebook.spine.insert(0, 'nav')

    dst_file = DATA_DIR / f"{book['title'].replace(' ', '-')}.epub"
    epub.write_epub(str(dst_file), ebook)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('number', type=int, nargs=-1)
def grab_book(number):
    for num in number:
        book = BOOKS[num]
        click.echo(f"Grabbing {book['title']}...")
        book_dir = _get_book_dir_name(num)
        os.makedirs(book_dir, exist_ok=True)
        _grab_book(book, book_dir)


@cli.command()
@click.argument('number', type=int, nargs=-1)
def create_epub(number):
    for num in number:
        book = BOOKS[num]
        book_dir = _get_book_dir_name(num)
        if not book_dir.exists():
            click.echo(f"No data present for {book['title']}")
        else:
            click.echo(f"Generating {book['title']}...")
            _create_epub(book, book_dir)


if __name__ == '__main__':
    cli()
