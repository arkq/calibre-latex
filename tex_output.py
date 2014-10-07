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


class RecodeCallbackRegistry:

    # global registry of defined recode callbacks
    __registry = {}

    @classmethod
    def register(cls, callback):
        cls.__registry[callback.tag] = callback

    def __init__(self, logger):
        # local registry of callback instances
        self.registry = {
            tag: callback(logger)
            for tag, callback in self.__registry.items()
        }

    def get(self, tag):
        return self.registry.get(tag)


class RecodeCallbackBase:

    class __metaclass__(type):
        def __init__(cls, name, bases, attrs):
            type.__init__(cls, name, bases, attrs)
            RecodeCallbackRegistry.register(cls)

    # NOTE: body is our first document structure tag, so it is safe to use
    #       it as a callback base example
    tag = XHTML('body')

    def __init__(self, logger):
        self.log = logger

        # reference counter used for tracking tags nesting
        self.refcount = 0

        # internal stack for data stashing
        self.datastack = []

    def push(self, data):
        """Push data onto the internal stack storage."""
        self.datastack.append(data)

    def pop(self):
        """Pop data from the internal stack storage."""
        return self.datastack.pop()

    def start(self, element):
        """Element recoding entry method."""
        return self.get_text(element)

    def end(self, element):
        """Element recoding exit method."""
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


class RecodeCallbackBr(RecodeCallbackBase):

    tag = XHTML('br')

    def end(self, element):
        return " \\\\*\n"


class RecodeCallbackSpan(RecodeCallbackBase):

    tag = XHTML('span')

    def start(self, element):

        functions = []

        # font format is encoded in the class attribute
        for cls in set(self.get_classes(element)):
            if cls == 'bold':
                functions.append("\\textbf{")
            elif cls == 'italic':
                functions.append("\\emph{")
            else:
                functions.append("{")
                self.log.warning("unrecognized span class:", cls)

        # save the number of used functions, so we will close them properly
        self.push(len(functions))

        return "".join(functions) + self.get_text(element)

    def end(self, element):
        return "}" * self.pop() + self.get_tail(element)


class LatexOutput(OutputFormatPlugin):

    name = 'Latex Output'
    author = 'Arkadiusz Bokowy'
    file_type = 'tex'

    options = set([
        OptionRecommendation(
            name='latex_title_page',
            recommended_value=True,
            help=_(
                "Insert Latex default Title Page which will appear as a part "
                "of the main book content."
            ),
        ),
        OptionRecommendation(
            name='latex_toc',
            recommended_value=False,
            help=_(
                "Insert Latex default Table of Contents which will appear "
                "as a part of the main book content."
            ),
        ),
    ])

    recommendations = set([
        ('pretty_print', True, OptionRecommendation.HIGH),
    ])

    def convert(self, oeb, output_path, input_plugin, opts, log):
        self.oeb, self.opts, self.log = oeb, opts, log
        self.callbacks = RecodeCallbackRegistry(log)

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

            # write custom command definitions and overrides
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
                callback = self.callbacks.get(element.tag)
                if not callback:
                    self.log.warning("unhandled tag:", element.tag)
                    continue
                if event == 'start':
                    callback.refcount += 1
                    content.append(callback.start(element))
                elif event == 'end':
                    content.append(callback.end(element))
                    callback.refcount -= 1

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
                pos = line.rfind(" ", 0, length)
                if pos == -1:
                    # look for the first space after the length
                    pos = line.find(" ", length, len(line))
                if pos == -1:
                    # we are too dumb to break this line
                    break
                pos += 1  # break after a "break" character
                lines.append(line[:pos].strip())
                line = line[pos:]
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
