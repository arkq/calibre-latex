LaTeX Output Plugin for Calibre
===============================

This is an output plugin for [Calibre](http://calibre-ebook.com/), which
provides document conversion into the LaTeX format. The main goal of it, is
to generate a TeX document, which can be edited and then converted into a
PDF file using the `pdflatex` command. The conversion process it automatic,
however due to the high complexity of the LaTeX syntax and frequently used
tricks, the output source file will aways need some manual corrections.
Simply put, this tool is not some magic wizard which will do all the work.
It should help a lot, though.

Installation
------------

1. Download the latest version of the plugin from the [releases page](
   https://github.com/arkq/calibre-latex/releases).
2. Open the Calibre application and go to the `Preferences` dialog.
3. Go to the `Plugins` section and click the `Load plugin from file` button.
4. Select the downloaded file and click `Open`.
5. Click `Yes` to confirm installation of the plugin.
6. Restart the Calibre application.

Usage
-----

After successful installation, this plugin should be fully functional. You can
use it from the Calibre GUI or from the command line conversion utility, e.g.:

```sh
ebook-convert AwesomeDocument.mobi more-awesome-latex-document.tex
```
