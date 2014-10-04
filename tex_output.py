# -*- coding: utf-8 -*-

__license__ = 'MIT'
__copyright__ = '2014, Arkadiusz Bokowy <arkadiusz.bokowy@gmail.com>'
__docformat__ = 'restructuredtext en'

import os

from calibre.customize.conversion import OptionRecommendation
from calibre.customize.conversion import OutputFormatPlugin


class LatexOutput(OutputFormatPlugin):

    name = 'Latex Output'
    author = 'Arkadiusz Bokowy'
    file_type = 'tex'

    options = set([
    ])

    recommendations = set([
        ('pretty_print', True, OptionRecommendation.HIGH),
    ])

    def convert(self, oeb, output_path, input_plugin, opts, log):
        self.opts, self.log = opts, log

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
                "{content}\n"
                "\\end{{document}}\n"
            ).format(
                content="",
            ))

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
