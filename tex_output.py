# -*- coding: utf-8 -*-

__license__ = 'MIT'
__copyright__ = '2014, Arkadiusz Bokowy <arkadiusz.bokowy@gmail.com>'
__docformat__ = 'restructuredtext en'

import os
import re
from lxml import etree
from urllib import unquote

from calibre import CurrentDir
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

    def __init__(self, converter):
        # local registry of callback instances
        self.registry = {
            tag: callback(converter, converter.log)
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

    def __init__(self, converter, logger):
        self.converter = converter
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

    @classmethod
    def get_begin(cls, element):
        return ""

    @classmethod
    def get_end(cls, element):
        return ""

    @classmethod
    def get_text(cls, element):
        return cls.sanitize(element.text or "")

    @classmethod
    def get_tail(cls, element):
        return cls.sanitize(element.tail or "")

    @staticmethod
    def sanitize(text):
        """
        Return the given text with sanitized TeX special characters.

        There is ten characters which have special meaning in the TeX
        document, plus a newline which controls document structure.
        The list of all of them:
        &, %, $, #, _, {, }, ~, ^, backslash and newline
        """
        text = re.sub(r'\\', r'\\textbackslash{}', text)
        text = re.sub(r'\^', r'\\textasciicircum{}', text)
        text = re.sub(r'~', r'\\textasciitilde{}', text)
        text = re.sub(r'[&%$#_{}]', r'\\\g<0>', text)
        return re.sub(r'[\r\n]+', r' ', text)

    @staticmethod
    def get_classes(element):
        """Get classes set attached to the given element."""
        return set(element.attrib.get('class', "").split())

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
                functions.append("\\uline{")

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


class RecodeCallbackB(RecodeCallbackBase):

    tag = XHTML('b')

    def get_begin(self, element):
        return self.get_class_style({"bold"})[0]

    def get_end(self, element):
        return "}"


class RecodeCallbackBlockquote(RecodeCallbackBase):

    tag = XHTML('blockquote')

    def get_begin(self, element):
        return "\n\\begin{quotation}\n"

    def get_end(self, element):
        return "\n\\end{quotation}\n"


class RecodeCallbackBr(RecodeCallbackBase):

    tag = XHTML('br')

    def get_begin(self, element):
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


class RecodeCallbackEm(RecodeCallbackBase):

    tag = XHTML('em')

    def get_begin(self, element):
        return self.get_class_style({"italic"})[0]

    def get_end(self, element):
        return "}"


class RecodeCallbackFigcaption(RecodeCallbackBase):

    tag = XHTML('figcaption')

    def get_begin(self, element):
        return "\n\\caption{"

    def get_end(self, element):
        return "}\n"


class RecodeCallbackFigure(RecodeCallbackBase):

    tag = XHTML('figure')

    def get_begin(self, element):
        return "\n\\begin{figure}[h]\n\\centering\n"

    def get_end(self, element):
        return "\n\\end{figure}\n"


class RecodeCallbackH1(RecodeCallbackBase):

    tag = XHTML('h1')

    def get_begin(self, element):
        # NOTE: To be honest, we do not know if given book/article has any
        #       "parts" in it. None the less, the lowest section of a TeX
        #       document structure is a part.
        return "\n\\part{"

    def get_end(self, element):
        return "}\n"


class RecodeCallbackH2(RecodeCallbackBase):

    tag = XHTML('h2')

    def get_begin(self, element):
        return "\n\\chapter{"

    def get_end(self, element):
        return "}\n"


class RecodeCallbackH3(RecodeCallbackBase):

    tag = XHTML('h3')

    def get_begin(self, element):
        return "\n\\section{"

    def get_end(self, element):
        return "}\n"


class RecodeCallbackH4(RecodeCallbackBase):

    tag = XHTML('h4')

    def get_begin(self, element):
        return "\n\\subsection{"

    def get_end(self, element):
        return "}\n"


class RecodeCallbackHr(RecodeCallbackBase):

    tag = XHTML('hr')

    def get_begin(self, element):
        # in the HTML the HR tag is defined as a thematic break
        return "\n\n\\bigskip\n\\hrule\n\\bigskip\n\n"


class RecodeCallbackI(RecodeCallbackBase):

    tag = XHTML('i')

    def get_begin(self, element):
        return self.get_class_style({"italic"})[0]

    def get_end(self, element):
        return "}"


class RecodeCallbackImg(RecodeCallbackBase):

    tag = XHTML('img')

    def get_begin(self, element):
        # try to get image source from the converter images mapping, otherwise
        # use `src` attribute itself (e.g. external resource)
        src = element.attrib.get('src', "")
        src = self.converter.images.get(src) or unquote(src)
        return "\n\\includegraphics[width=0.8\\textwidth]{" + src + "}\n"


class RecodeCallbackLi(RecodeCallbackBase):

    tag = XHTML('li')

    def get_begin(self, element):
        return "\n\\item "

    def get_end(self, element):
        return "\n"


class RecodeCallbackOl(RecodeCallbackBase):

    tag = XHTML('ol')

    def get_begin(self, element):
        return "\n\\begin{enumerate}\n"

    def get_end(self, element):
        return "\n\\end{enumerate}\n"


class RecodeCallbackP(RecodeCallbackBase):

    tag = XHTML('p')

    def get_begin(self, element):
        return "\n\n"

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


class RecodeCallbackSub(RecodeCallbackBase):

    tag = XHTML('sub')

    def get_begin(self, element):
        # NOTE: TeX does not provide subscript command for text environment.
        #       This "lack" of functionality is reasonable, because usage of
        #       a subscript outside the math scope seems to be wrong anyway.
        self.log.info("using math-mode subscript")
        return "$_{"

    def get_end(self, element):
        return "}$"


class RecodeCallbackSup(RecodeCallbackBase):

    tag = XHTML('sup')

    def get_begin(self, element):
        return "\\textsuperscript{"

    def get_end(self, element):
        return "}"


class RecodeCallbackStrong(RecodeCallbackBase):

    tag = XHTML('strong')

    def get_begin(self, element):
        return self.get_class_style({"bold"})[0]

    def get_end(self, element):
        return "}"


class RecodeCallbackU(RecodeCallbackBase):

    tag = XHTML('u')

    def get_begin(self, element):
        return self.get_class_style({"underline"})[0]

    def get_end(self, element):
        return "}"


class RecodeCallbackUl(RecodeCallbackBase):

    tag = XHTML('ul')

    def get_begin(self, element):
        return "\n\\begin{itemize}\n"

    def get_end(self, element):
        return "\n\\end{itemize}\n"


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
        self.callbacks = RecodeCallbackRegistry(self)

        # set the base-name for this conversion (e.g. directory prefix)
        self.basename = os.path.splitext(os.path.basename(output_path))[0]

        # create output directory if needed
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir) and output_dir:
            os.makedirs(output_dir)

        # try to get basic metadata of this document
        authors = map(lambda x: x.value, oeb.metadata.author)
        creators = map(lambda x: x.value, oeb.metadata.creator)
        titles = map(lambda x: x.value, oeb.metadata.title)
        languages = map(lambda x: x.value, oeb.metadata.language)

        # get language abbreviations and full names needed by latex
        languages = self.latex_convert_languages(languages)

        # extract embedded images to the images directory
        self.images = self.latex_extract_images(output_dir)

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
                "\\usepackage[normalem]{{ulem}}\n"
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
                    content.append(callback.stop(element))
                    callback.refcount -= 1

        content = "".join(content)

        # fix obvious misuses of explicit newline marker
        content = re.sub(r'^( \\\\\*\n)+', r'', content)
        content = re.sub(r'\n\n( \\\\\*\n)+', r'\n\n', content)

        # normalize white characters (tabs, spaces, multiple newlines)
        content = re.sub(r'^ ', r'', re.sub(r'[ \t]+', r' ', content), flags=re.M)
        content = re.sub(r'\s*\n\s*\n\s*\n', r'\n\n', content.strip()) + "\n"

        if self.opts.pretty_print:
            content = self.latex_pretty_print(content, length=self.opts.max_line_length)

        return content

    def latex_extract_images(self, directory):

        images = filter(lambda x: x.media_type.startswith('image'), self.oeb.manifest)
        if not images:
            return {}

        # gather image ID mappings for further references
        reference = self.oeb.spine.items[0]
        references = {}

        with CurrentDir(directory):

            # create output directory if needed
            images_dir = self.latex_images_directory()
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)

            for image in images:
                image_name = re.sub(r'[\\/]', r'_', image.id)
                image_path = os.path.join(images_dir, image_name)
                references[reference.relhref(image.href)] = image_path
                with open(image_path, 'wb') as f:
                    f.write(image.data)

        return references

    def latex_images_directory(self):
        return self.basename + "-images"

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
        return "\n".join(lines) + "\n"

    @staticmethod
    def latex_convert_languages(languages):
        mapping = {
            'eng': ('en', 'eng', 'english'),
            'pol': ('pl', 'pol', 'polish'),
        }
        languages = map(lambda x: mapping.get(x), languages)
        languages = tuple(filter(None, languages))
        if languages:
            return languages
        return (mapping['eng'],)
