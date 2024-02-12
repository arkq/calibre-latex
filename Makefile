# Copyright (c) 2024 Arkadiusz Bokowy
#
# This file is a part of calibre-latex.
#
# This project is licensed under the terms of the MIT license.

OUT := calibre-latex-$(shell git describe --always).zip

.PHONY: all
all: $(OUT)

.PHONY: clean
clean:
	rm $(OUT)

$(OUT): \
		src/__init__.py \
		src/plugin-import-name-texoutput.txt \
		src/tex_output_gui.py \
		src/tex_output.py \
		LICENSE.txt
	zip --verbose --junk-paths $@ $^
