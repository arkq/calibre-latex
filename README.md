Latex Output Plugin for Calibre
===============================

This is an output plugin for [Calibre](http://calibre-ebook.com/), which
provides document conversion into the Latex format. The main goal of it, is
to generate a TeX document, which can be edited and then converted into a
PDF file using the `pdflatex` command. The conversion process it automatic,
however due to the high complexity of the Latex syntax and frequently used
tricks, the output source file will aways need some manual corrections.
Simply put, this tool is not some magic wizard which will do all the work.
It should help a lot, though.


Installation
------------

First of all make sure, that you've got Calibre installed. If not, I don't
know what are you doing here. The only reasonable answer to this question is,
that you are literature lover, and want to read everything and everywhere.
If so, you should definitely get a fresh copy of Calibre, just follow this
[link](http://calibre-ebook.com/download).

Assuming, that you are running 64 bit version of Linux system, you have to
copy this output plugin ([tex_output.py](https://raw.githubusercontent.com/Arkq/calibre-latex/master/tex_output.py))
in the following location (do not change the file name):

	/usr/lib64/calibre/calibre/ebooks/conversion/plugins/

Afterwards, get your best text editor and add the following lines into the
`/usr/lib64/calibre/calibre/customize/builtins.py` file:

	from calibre.ebooks.conversion.plugins.tex_output import LatexOutput
	plugins += [LatexOutput]

or simply run commands as follows:

	PLUGINREGISTER=/usr/lib64/calibre/calibre/customize/builtins.py
	echo "from calibre.ebooks.conversion.plugins.tex_output import LatexOutput" >>$PLUGINREGISTER
	echo "plugins += [LatexOutput]" >>$PLUGINREGISTER


Usage
-----

After successful installation, this plugin should be fully functional. You can
use it from the Calibre GUI or from the command line conversion utility, e.g.:

	ebook-convert AwesomeDocument.mobi more-awesome-latex-document.tex
