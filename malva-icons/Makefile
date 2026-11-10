# Malva Icons — Build, Install, Export & Verification Makefile

PYTHON ?= python3
PREFIX ?= $(HOME)/.local/share/icons
SYSTEM_PREFIX ?= /usr/share/icons
THEME_DIR := assets/icons/Malva

.PHONY: all build build-small install install-copy install-system uninstall check check-fast test export-png clean

all: build

build:
	$(PYTHON) tools/icons/build_theme.py

build-small:
	$(PYTHON) tools/icons/build_theme.py --small-cuts

install:
	$(PYTHON) tools/icons/install_theme.py --dest "$(PREFIX)"

install-copy:
	$(PYTHON) tools/icons/install_theme.py --dest "$(PREFIX)" --copy

install-system:
	$(PYTHON) tools/icons/install_theme.py --dest "$(SYSTEM_PREFIX)"

uninstall:
	$(PYTHON) tools/icons/install_theme.py --dest "$(PREFIX)" --uninstall

test:
	$(PYTHON) tools/icons/selftest.py
	$(PYTHON) -m unittest discover -s tests -v

check-fast:
	$(PYTHON) tools/icons/selftest.py
	$(PYTHON) tools/icons/check_theme.py --no-negative

check:
	$(PYTHON) tools/icons/selftest.py
	$(PYTHON) tools/icons/check_glyphs.py
	$(PYTHON) tools/icons/check_apps.py
	$(PYTHON) tools/icons/check_objects.py
	$(PYTHON) tools/icons/check_tiles.py
	$(PYTHON) tools/icons/check_theme.py

export-png:
	$(PYTHON) tools/icons/export_png.py --theme $(THEME_DIR) --size 16 24 32 48 64 128 256 --color "#2E2230" -o out/Malva-png --aliases

clean:
	rm -rf out/ png-export/ build/ dist/
	find . -type d -name "__pycache__" -exec rm -rf {} +
