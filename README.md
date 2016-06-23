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
[link](http://calibre-ebook.com/download) or use your favorite Linux package
manager, e.g. `apt-get install calibre`.

The installation process depends on how Calibre was installed. Please, follow
the instruction from the appropriate subsection.

##### 1) Calibre was installed from package manager (DEB, RPM, etc.)

Assuming, that you are running 64 bit version of Linux system, you have to
copy this output plugin ([tex\_output.py](https://github.com/Arkq/calibre-latex/raw/master/src/tex_output.py))
in the following location (do not change the file name):

	/usr/lib64/calibre/calibre/ebooks/conversion/plugins/

Afterwards, get your best text editor and add the following lines into the
`/usr/lib64/calibre/calibre/customize/builtins.py` file:

	from calibre.ebooks.conversion.plugins.tex_output import LatexOutput
	plugins += [LatexOutput]

or simply run commands as follows:

	PLUGIN=/usr/lib64/calibre/calibre/ebooks/conversion/plugins/tex_output.py
	PLUGINREGISTER=/usr/lib64/calibre/calibre/customize/builtins.py
	wget -O $PLUGIN https://github.com/Arkq/calibre-latex/raw/master/src/tex_output.py
	echo "from calibre.ebooks.conversion.plugins.tex_output import LatexOutput" >>$PLUGINREGISTER
	echo "plugins += [LatexOutput]" >>$PLUGINREGISTER

##### 2) Calibre was installed from website installer

During the automatic installation process, Calibre was most likely installed
in the location `/opt/calibre/`. The next part of this instruction relies on
this assumption. If your copy of Calibre is installed in some other location,
please modify the ROOT variable accordingly.

Run commands as follows:

	ROOT=/opt/calibre
	PLUGIN=$ROOT/lib/python2.7/site-packages/calibre/ebooks/conversion/plugins/tex_output.py
	PLUGINREGISTER=$ROOT/lib/python2.7/site-packages/calibre/customize/builtins.py
	TAG=$( $ROOT/calibre --version |python -c 'import re, sys; \
		print("v" + ".".join((re.search("[\d\.]+", sys.stdin.read()).group(0).split(".") + ["0"])[:3]))' )
	wget -O $PLUGIN https://github.com/Arkq/calibre-latex/raw/master/src/tex_output.py
	wget -O $PLUGINREGISTER https://github.com/kovidgoyal/calibre/raw/$TAG/src/calibre/customize/builtins.py
	echo "from calibre.ebooks.conversion.plugins.tex_output import LatexOutput" >>$PLUGINREGISTER
	echo "plugins += [LatexOutput]" >>$PLUGINREGISTER


Usage
-----

After successful installation, this plugin should be fully functional. You can
use it from the Calibre GUI or from the command line conversion utility, e.g.:

	ebook-convert AwesomeDocument.mobi more-awesome-latex-document.tex
