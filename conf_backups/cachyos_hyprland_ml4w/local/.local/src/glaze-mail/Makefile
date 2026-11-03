MAIL_PYTHON := $(HOME)/.config/gcal/.venv/bin/python
PREVIEW_PYTHON := $(HOME)/.local/share/glaze-mail/preview-venv/bin/python

.PHONY: test test-mail test-preview
test: test-mail test-preview

test-mail:
	PYTHONPATH=. "$(MAIL_PYTHON)" -m unittest discover -s tests -v

test-preview:
	PYTHONPATH=. "$(PREVIEW_PYTHON)" -m unittest discover -s tests_preview -v
