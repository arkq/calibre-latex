# Copyright (c) 2024 Arkadiusz Bokowy
#
# This file is a part of calibre-latex.
#
# This project is licensed under the terms of the MIT license.

__license__ = 'MIT'
__copyright__ = '2024, Arkadiusz Bokowy <arkadiusz.bokowy@gmail.com>'
__docformat__ = 'restructuredtext en'

from calibre.gui2.convert import Widget

from PyQt5 import QtWidgets


class LatexOutputWidget(Widget):

    TITLE = _('TEX output')  # noqa
    HELP = _('Options specific to') + ' TEX ' + _('output')  # noqa
    COMMIT_NAME = 'latex_output'

    OPTIONS = ('latex_title_page', 'latex_toc', 'max_line_length')

    def __init__(self, parent, get_option, get_help, db, book_id=None):
        Widget.__init__(self, parent, self.OPTIONS)
        self.db, self.book_id = db, book_id
        self.initialize_options(get_option, get_help, db, book_id)

    def setupUi(self, widget):

        layout = QtWidgets.QVBoxLayout(widget)

        self.opt_latex_title_page = QtWidgets.QCheckBox()
        self.opt_latex_title_page.setText(_("Generate LaTeX default &Title Page"))  # noqa
        layout.addWidget(self.opt_latex_title_page)

        self.opt_latex_toc = QtWidgets.QCheckBox()
        self.opt_latex_toc.setText(_("Generate LaTeX default Table of &Contents"))  # noqa
        layout.addWidget(self.opt_latex_toc)

        layout_max_line_length = QtWidgets.QHBoxLayout()
        self.opt_max_line_length = QtWidgets.QSpinBox()
        opt_max_line_length_label = QtWidgets.QLabel()
        opt_max_line_length_label.setText(_("&Maximum line length:"))  # noqa
        opt_max_line_length_label.setBuddy(self.opt_max_line_length)
        layout_max_line_length.addWidget(opt_max_line_length_label)
        layout_max_line_length.addWidget(self.opt_max_line_length)
        layout.addLayout(layout_max_line_length)

        layout.addStretch()
