# -*- coding: utf-8 -*-

__license__ = 'MIT'
__copyright__ = '2014, Arkadiusz Bokowy <arkadiusz.bokowy@gmail.com>'
__docformat__ = 'restructuredtext en'

import os
import re
from lxml import etree

from calibre.customize.conversion import OptionRecommendation
from calibre.customize.conversion import OutputFormatPlugin
from calibre.ebooks.oeb.base import XHTML
from calibre.ebooks.oeb.base import XPath


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

    def start(self, element):
        """Element recoding entry method."""
        return self.get_begin(element) + self.get_text(element)

    def stop(self, element):
        """Element recoding exit method."""
        return self.get_end(element) + self.get_tail(element)

    def push(self, data):
        """Push data onto the internal stack storage."""
        self.datastack.append(data)

    def pop(self):
        """Pop data from the internal stack storage."""
        return self.datastack.pop()

    @staticmethod
    def get_classes(element):
        """Get classes set attached to the given element."""
        return set(element.attrib.get('class', "").split())

    @staticmethod
    def get_begin(element):
        return ""

    @staticmethod
    def get_end(element):
        return ""

    @staticmethod
    def get_text(element):
        return element.text or ""

    @staticmethod
    def get_tail(element):
        return element.tail or ""

    @staticmethod
    def get_class_style(classes):
        """
        Get style functions. In the OEB file format, style is encoded in the
        class attribute.

        That method modifies input argument - used classes are removed.
        """
        functions = []

        for cls in classes:
            if cls == 'bold':
                functions.append("\\textbf{")
            elif cls == 'italic':
                functions.append("\\emph{")
            elif cls == 'underline':
                functions.append("\\underline{")
                # NOTE: Another possibility might be the usage of the normalem
                #       package, which supports breaks in the underlined text.
                # \usepackage[normalem]{ulem}
                # functions.append("\\uline{")

        # remove used (recognized) classes
        classes.difference_update((
            'bold', 'italic', 'underline',
        ))
        return functions

    @staticmethod
    def get_class_layout(classes):
        """
        Get layout functions. In the OEB file format layout may be encoded in
        the class attribute, e.g. page-break.

        That method modifies input argument - used classes are removed.
        """
        functions = []

        for cls in classes:
            if cls == 'mbppagebreak':
                functions.append("\\chapter*{")

        # remove used (recognized) classes
        classes.difference_update((
            'mbppagebreak',
        ))
        return functions


class RecodeCallbackA(RecodeCallbackBase):

    tag = XHTML('a')

    def get_begin(self, element):
        href = element.attrib.get('href', "")
        return "\\href{" + href + "}{"

    def get_end(self, element):
        return "}"


class RecodeCallbackBlockquote(RecodeCallbackBase):

    tag = XHTML('blockquote')

    def get_begin(self, element):
        return "\n\\begin{quotation}\n"

    def get_end(self, element):
        # blockquote should act like paragraph, hence trailing newline
        return "\n\\end{quotation}\n\n"


class RecodeCallbackBr(RecodeCallbackBase):

    tag = XHTML('br')

    def get_end(self, element):
        # add extra space prefix for readability's sake
        return " \\\\*\n"


class RecodeCallbackDiv(RecodeCallbackBase):

    tag = XHTML('div')

    def get_begin(self, element):
        classes = self.get_classes(element)

        functions = []
        functions.extend(self.get_class_layout(classes))
        functions.extend(self.get_class_style(classes))

        # save the number of used functions, so we will close them properly
        self.push(len(functions))

        return "".join(functions)

    def get_end(self, element):
        # hence div is a block tag, add a new line at the end
        return "}" * self.pop() + "\n"


class RecodeCallbackP(RecodeCallbackBase):

    tag = XHTML('p')

    def get_end(self, element):
        return "\n\n"


class RecodeCallbackSpan(RecodeCallbackBase):

    tag = XHTML('span')

    def get_begin(self, element):
        classes = self.get_classes(element)

        functions = []
        functions.extend(self.get_class_layout(classes))
        functions.extend(self.get_class_style(classes))

        # save the number of used functions, so we will close them properly
        self.push(len(functions))

        return "".join(functions)

    def get_end(self, element):
        return "}" * self.pop()


class LatexOutput(OutputFormatPlugin):

    name = 'Latex Output'
    author = 'Arkadiusz Bokowy'
    file_type = 'tex'

    options = set([
        OptionRecommendation(
            name='latex_title_page',
            recommended_value=True,
            help=_(  # noqa
                "Insert Latex default Title Page which will appear as a part "
                "of the main book content."
            ),
        ),
        OptionRecommendation(
            name='latex_toc',
            recommended_value=False,
            help=_(  # noqa
                "Insert Latex default Table of Contents which will appear "
                "as a part of the main book content."
            ),
        ),
        OptionRecommendation(
            name='max_line_length',
            recommended_value=78,
            help=_(  # noqa
                "The maximum number of characters per line. Use 0 to disable "
                "line splitting."
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
                "\\usepackage{{graphicx,hyperref,lettrine}}\n"
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
                    content.append(callback.stop(element))
                    callback.refcount -= 1

        content = "".join(content)

        # fix obvious misuses of explicit newline marker
        content = re.sub(r'^( \\\\\*\n)+', r'', content)
        content = re.sub(r'\n\n( \\\\\*\n)+', r'\n\n', content)

        # normalize white characters (tabs, spaces, multiple newlines)
        content = re.sub(r'[ \t]+', r' ', content)
        content = re.sub(r'\s*\n\s*\n\s*\n', r'\n\n', content)

        if self.opts.pretty_print:
            content = self.latex_pretty_print(content, length=self.opts.max_line_length)

        return content

    @staticmethod
    def latex_pretty_print(content, length=78):
        if not length:
            return content
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
