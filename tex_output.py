# -*- coding: utf-8 -*-

__license__ = 'MIT'
__copyright__ = '2014, Arkadiusz Bokowy <arkadiusz.bokowy@gmail.com>'
__docformat__ = 'restructuredtext en'

from lxml import etree
import os

from calibre.customize.conversion import OptionRecommendation
from calibre.customize.conversion import OutputFormatPlugin
from calibre.ebooks.oeb.base import XPath
from calibre.ebooks.oeb.base import XHTML


class RecodeCallbackRegistry(type):

    # registry of defined recode callbacks
    registry = {}

    def __init__(cls, name, bases, attrs):
        RecodeCallbackRegistry.registry[cls.tag] = cls()
        return type.__init__(cls, name, bases, attrs)

    @classmethod
    def get(cls, tag):
        return cls.registry.get(tag)

    @classmethod
    def set_logger(cls, logger):
        for callback in cls.registry.values():
            callback.log = logger


class RecodeCallbackBase:
    __metaclass__ = RecodeCallbackRegistry

    # NOTE: body is our first document structure tag, so it is safe to use
    #       it as a callback base example
    tag = XHTML('body')

    # XXX: when callback entry point is called, it is guarantied that this
    #      attribute is set to the current application logger
    log = None

    def start(self, element):
        return self.get_text(element)

    def end(self, element):
        return self.get_tail(element)

    @staticmethod
    def get_text(element):
        return element.text or ""

    @staticmethod
    def get_tail(element):
        return element.tail or ""

    @staticmethod
    def get_classes(element):
        return element.attrib.get('class', "").split()


class RecodeCallbackP(RecodeCallbackBase):

    tag = XHTML('p')

    def end(self, element):
        return "\n\n"


class RecodeCallbackSpan(RecodeCallbackBase):

    tag = XHTML('span')

    def start(self, element):

        # font format is encoded in the class attribute
        classes = self.get_classes(element)

        if 'bold' in classes:
            return "\\textbf{" + self.get_text(element)
        elif 'italic' in classes:
            return "\\emph{" + self.get_text(element)

        self.log.warning("unrecognized span class:", classes)
        return "{" + self.get_text(element)

    def end(self, element):
        return "}" + self.get_tail(element)


class LatexOutput(OutputFormatPlugin):

    name = 'Latex Output'
    author = 'Arkadiusz Bokowy'
    file_type = 'tex'

    options = set([
        OptionRecommendation(
            name='latex_title_page',
            recommended_value=True,
            help=_('Insert Latex default Title Page which will appear as part of main book content.'),
        ),
        OptionRecommendation(
            name='latex_toc',
            recommended_value=False,
            help=_('Insert Latex default Table of Contents which will appear as part of the main book content.'),
        ),
    ])

    recommendations = set([
        ('pretty_print', True, OptionRecommendation.HIGH),
    ])

    def convert(self, oeb, output_path, input_plugin, opts, log):
        self.oeb, self.opts, self.log = oeb, opts, log
        RecodeCallbackRegistry.set_logger(log)

        # try to get basic metadata of this document
        authors = map(lambda x: x.value, oeb.metadata.author)
        creators = map(lambda x: x.value, oeb.metadata.creator)
        titles = map(lambda x: x.value, oeb.metadata.title)
        languages = map(lambda x: x.value, oeb.metadata.language)

        # get language abbreviations and full names needed by latex
        languages = self.latex_convert_languages(languages)

        # create output directories if needed
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir) and output_dir:
            os.makedirs(output_dir)

        #import pdb; pdb.set_trace()

        # open output file for content writing
        with open(output_path, 'w') as f:

            # write standard latex header
            f.write((
                "% vim: spl={vimlanguage}\n"
                "\\documentclass[12pt,oneside]{{book}}\n"
                "\\usepackage[utf8]{{inputenc}}\n"
                "\\usepackage[OT4]{{fontenc}}\n"
                "\\usepackage[{languages}]{{babel}}\n"
                "\\usepackage[pdfauthor={{{authors}}},pdftitle={{{title}}}]{{hyperref}}\n"
                "\\usepackage{{graphicx,lettrine}}\n"
                "\n"
            ).format(
                vimlanguage=languages[0][0],
                languages=",".join(map(lambda x: x[2], languages)),
                authors=" & ".join(authors or creators),
                title=" | ".join(titles),
            ))

            # write custom command definitions and overwrites
            f.write((
                "\\newcommand{\\cover}[1]{\\def\\cover{#1}} % custom variable for cover image\n"
                "\\newcommand{\\degree}{\\textsuperscript{o}}\n"
                "\n"
            ))

            # write document header constants
            f.write((
                "\\cover{{{cover}}}\n"
                "\\author{{{authors}}}\n"
                "\\title{{{title}}}\n"
                "\\date{{{date}}}\n"
                "\n"
            ).format(
                cover="",
                authors=" & ".join(authors or creators),
                title=" | ".join(titles),
                date="",
            ))

            # write document content
            f.write((
                "\\begin{{document}}\n"
                "{titlepage}"  # this section has a new line on its own
                "{tocpage}"    # this section has a new line on its own
                "\n"
                "{content}"    # this section has a new line on its own
                "\n"
                "\\end{{document}}\n"
            ).format(
                titlepage=self.latex_format_titlepage(),
                tocpage=self.latex_format_tocpage(),
                content=self.latex_format_content(),
            ))

    def latex_format_titlepage(self):
        if not self.opts.latex_title_page:
            return "% \\maketitle\n"
        return "\\maketitle\n"

    def latex_format_tocpage(self):
        if not self.opts.latex_toc:
            return "% \\tableofcontents\n"
        return "\\tableofcontents\n"

    def latex_format_content(self):

        # collection of TeX document chunks
        content = []

        for x in self.oeb.spine:
            try:
                body = XPath('//h:body')(x.data)[0]
            except IndexError:
                continue
            # recode the OEB document nodes into the TeX syntax
            for event, element in etree.iterwalk(body, ('start', 'end')):
                callback = RecodeCallbackRegistry.get(element.tag)
                if not callback:
                    self.log.warning("unhandled tag:", element.tag)
                    continue
                if event == 'start':
                    content.append(callback.start(element))
                elif event == 'end':
                    content.append(callback.end(element))

        content = "".join(content)

        # content post-processing

        if self.opts.pretty_print:
            content = self.latex_pretty_print(content)

        return content

    @staticmethod
    def latex_pretty_print(content, length=78):
        lines = []
        for line in content.splitlines():
            while len(line) > length:
                space = line.rfind(" ", 0, length)
                if space == -1:
                    # look for the first space after the length
                    space = line.find(" ", length, len(line))
                if space == -1:
                    # we are too dumb to break this line
                    break
                lines.append(line[:space])
                line = line[space + 1:]
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def latex_convert_languages(languages):
        mapping = {
            'eng': ('en', 'eng', 'english'),
            'pol': ('pl', 'pol', 'polish'),
        }
        languages = list(map(lambda x: mapping[x], languages))
        if languages:
            return languages
        return mapping['eng']
